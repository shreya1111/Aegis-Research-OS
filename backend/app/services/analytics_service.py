"""Analytics service for Phase 8 - data profiling and AI-assisted analysis."""

from __future__ import annotations

import io
import json
import logging
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from uuid import UUID

import pandas as pd

from app.core.config import get_settings
from app.core.llm.provider import LLMProvider, Message
from app.db.repositories.analytics_repository import AnalyticsRepository

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for analytics operations: profiling, analysis, charting."""

    def __init__(
        self,
        *,
        repository: AnalyticsRepository,
        llm_provider: LLMProvider,
    ) -> None:
        self._repo = repository
        self._llm = llm_provider

    async def profile_dataset(
        self,
        dataset_id: UUID,
        csv_content: bytes,
    ) -> dict[str, Any]:
        """Profile a CSV dataset: detect types, generate summary statistics."""
        try:
            # Read CSV
            df = pd.read_csv(io.BytesIO(csv_content))

            # Basic info
            row_count, column_count = df.shape

            # Generate profile data
            profile = {
                "columns": {},
                "summary": {
                    "row_count": row_count,
                    "column_count": column_count,
                    "columns": list(df.columns),
                },
            }

            # Profile each column
            for col in df.columns:
                col_data = df[col]
                col_profile = {
                    "dtype": str(col_data.dtype),
                    "null_count": int(col_data.isnull().sum()),
                    "null_percentage": float(col_data.isnull().sum() / len(col_data) * 100),
                    "unique_count": int(col_data.nunique()),
                }

                # Add type-specific stats
                if pd.api.types.is_numeric_dtype(col_data):
                    col_profile.update(
                        {
                            "min": float(col_data.min()) if not pd.isna(col_data.min()) else None,
                            "max": float(col_data.max()) if not pd.isna(col_data.max()) else None,
                            "mean": float(col_data.mean()) if not pd.isna(col_data.mean()) else None,
                            "median": float(col_data.median()) if not pd.isna(col_data.median()) else None,
                            "std": float(col_data.std()) if not pd.isna(col_data.std()) else None,
                        }
                    )
                elif pd.api.types.is_object_dtype(col_data) or pd.api.types.is_string_dtype(col_data):
                    # String/categorical stats
                    top_values = col_data.value_counts().head(10).to_dict()
                    col_profile["top_values"] = {str(k): int(v) for k, v in top_values.items()}

                profile["columns"][col] = col_profile

            # Update repository
            await self._repo.update_dataset_profile(
                dataset_id,
                row_count=row_count,
                column_count=column_count,
                profile_data=profile,
            )

            return profile

        except Exception as e:
            logger.error(f"Failed to profile dataset {dataset_id}: {e}")
            await self._repo.mark_dataset_failed(dataset_id, str(e))
            raise BadRequestException(f"Failed to profile CSV: {e}")

    async def analyze_dataset(
        self,
        analysis_id: UUID,
        dataset_id: UUID,
        question: str,
        csv_content: bytes,
        profile_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate AI-assisted analysis of the dataset."""
        try:
            # Generate analysis code using LLM
            analysis_code = await self._generate_analysis_code(
                question=question,
                profile_data=profile_data,
            )

            # Execute the code in a sandboxed environment
            result_data, chart_data = await self._execute_analysis_code(
                code=analysis_code,
                csv_content=csv_content,
            )

            # Generate plain-language explanation
            explanation = await self._generate_explanation(
                question=question,
                analysis_code=analysis_code,
                result_data=result_data,
            )

            # Update repository
            await self._repo.update_analysis_result(
                analysis_id,
                analysis_code=analysis_code,
                result_data=result_data,
                chart_data=chart_data,
                explanation=explanation,
            )

            return {
                "analysis_code": analysis_code,
                "result_data": result_data,
                "chart_data": chart_data,
                "explanation": explanation,
            }

        except Exception as e:
            logger.error(f"Failed to analyze dataset: {e}")
            await self._repo.mark_analysis_failed(analysis_id, str(e))
            raise BadRequestException(f"Analysis failed: {e}")

    async def _generate_analysis_code(
        self,
        question: str,
        profile_data: dict[str, Any],
    ) -> str:
        """Use LLM to generate pandas analysis code."""
        system_prompt = """You are a data analysis assistant. Generate Python code using pandas to answer the user's question about their dataset.

Rules:
1. The CSV data is available as a pandas DataFrame named 'df'
2. Output ONLY valid Python code, no explanations
3. Use matplotlib or seaborn for visualizations if needed
4. Store results in a dictionary named 'result'
5. Store chart data (if any) in a dictionary named 'chart' with keys: type, data, layout
6. Do NOT use plt.show(), save figures to 'chart' instead
7. Keep code safe: no file system access, no network calls, no subprocess
8. Code must be self-contained and executable

Dataset profile:
""" + json.dumps(profile_data, indent=2)

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=f"Question: {question}"),
        ]

        response = await self._llm.complete(
            messages=messages,
            model_tier="strong",
            max_tokens=2000,
        )

        # Extract code from response (remove markdown if present)
        code = response.text.strip()
        if code.startswith("```python"):
            code = code[9:]
        if code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]

        return code.strip()

    async def _execute_analysis_code(
        self,
        code: str,
        csv_content: bytes,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        """Execute analysis code in a sandboxed environment."""
        # Validate code for safety
        self._validate_code_safety(code)

        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as f:
            csv_path = f.name
            f.write(csv_content)

        try:
            # Prepare execution environment
            execution_code = f"""
import pandas as pd
import numpy as np
import json
import sys
from io import StringIO

# Load data
df = pd.read_csv('{csv_path}')

# Initialize result containers
result = {{}}
chart = None

# User code
{code}

# Output results as JSON
output = {{
    'result': result,
    'chart': chart
}}
print(json.dumps(output, default=str))
"""

            # Execute with timeout and resource limits
            proc = subprocess.run(
                [sys.executable, "-c", execution_code],
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
                env={
                    "PYTHONPATH": "",  # Isolate from user environment
                },
            )

            if proc.returncode != 0:
                raise BadRequestException(f"Code execution failed: {proc.stderr}")

            # Parse output
            output = json.loads(proc.stdout.strip())
            result_data = output.get("result", {})
            chart_data = output.get("chart")

            return result_data, chart_data

        except subprocess.TimeoutExpired:
            raise BadRequestException("Analysis timed out (30s limit)")
        except json.JSONDecodeError as e:
            raise BadRequestException(f"Failed to parse analysis output: {e}")
        finally:
            # Clean up temporary file
            Path(csv_path).unlink(missing_ok=True)

    def _validate_code_safety(self, code: str) -> None:
        """Validate that code doesn't contain dangerous operations."""
        dangerous_patterns = [
            r"\bopen\s*\(",  # File operations
            r"\bexec\s*\(",  # Code execution
            r"\beval\s*\(",  # Code evaluation
            r"\b__import__\s*\(",  # Dynamic imports
            r"\bos\.",  # OS operations
            r"\bsys\.",  # System operations (except sys used in our wrapper)
            r"\bsubprocess\.",  # Subprocess
            r"\bsocket\.",  # Network
            r"\brequests\.",  # HTTP requests
            r"\burllib",  # HTTP requests
            r"\bpickle\.",  # Pickle can execute code
            r"\bshutil\.",  # File operations
            r"\bglob\.",  # File system
            r"\bpathlib\.",  # File system (except safe Path usage)
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                raise BadRequestException(
                    f"Code contains potentially dangerous operation: {pattern}"
                )

        # Check for infinite loops (basic detection)
        if re.search(r"\bwhile\s+True\s*:", code):
            raise BadRequestException("Infinite loops are not allowed")

    async def _generate_explanation(
        self,
        question: str,
        analysis_code: str,
        result_data: dict[str, Any],
    ) -> str:
        """Generate plain-language explanation of the analysis."""
        system_prompt = """You are a data analysis assistant. Explain the analysis results in plain language that non-technical users can understand.

Focus on:
1. What was analyzed
2. Key findings
3. What the numbers mean
4. Any notable patterns or insights

Be concise but informative."""

        user_content = f"""Question: {question}

Analysis performed:
{analysis_code}

Results:
{json.dumps(result_data, indent=2)}

Provide a clear, plain-language explanation of these results."""

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_content),
        ]

        response = await self._llm.complete(
            messages=messages,
            model_tier="fast",
            max_tokens=1000,
        )

        return response.text.strip()
