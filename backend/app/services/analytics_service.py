"""Analytics service for Phase 8 - data profiling and AI-assisted analysis."""

from __future__ import annotations

import io
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from uuid import UUID

import pandas as pd

from app.core.config import get_settings
from app.core.errors import ValidationError
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
            raise ValidationError(f"Failed to profile CSV: {e}")

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
            raise ValidationError(f"Analysis failed: {e}")

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
        """Execute generated analysis code in a constrained child process.

        Containment is layered (design FR-H4): static rejection of host-access
        constructs, an isolated interpreter (``-I``) started in a scratch
        directory holding only the dataset, a minimum environment, a wall-clock
        timeout, and — on POSIX — CPU, address-space, file-size and process
        limits. The static check is defence in depth rather than the security
        boundary; the process limits contain anything it misses.
        """
        self._validate_code_safety(code)

        with tempfile.TemporaryDirectory(prefix="aegis-analysis-") as work_dir:
            work_path = Path(work_dir)
            (work_path / "data.csv").write_bytes(csv_content)
            (work_path / "mpl").mkdir()

            execution_code = """
import pandas as pd
import numpy as np
import json

# The dataset is the only file in the child's working directory.
df = pd.read_csv('data.csv')

result = {}
chart = None

""" + code + """

print(json.dumps({'result': result, 'chart': chart}, default=str))
"""
            proc = subprocess.run(  # noqa: S603 - fixed argv, isolated interpreter
                [sys.executable, "-I", "-c", execution_code],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=work_dir,
                stdin=subprocess.DEVNULL,
                env=self._sandbox_environment(work_path),
                preexec_fn=self._child_limits() if os.name == "posix" else None,
                check=False,
            )

        if proc.returncode != 0:
            # Child stderr may contain paths or dataset fragments; record it
            # server-side and return a non-revealing message (design §9.5).
            logger.warning(
                "analytics.analysis_code_failed",
                extra={
                    "event": "analytics.analysis_code_failed",
                    "returncode": proc.returncode,
                    "stderr_tail": proc.stderr[-500:] if proc.stderr else "",
                },
            )
            raise ValidationError("The generated analysis could not be executed.")

        try:
            output = json.loads(proc.stdout.strip())
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValidationError(
                "The generated analysis did not return a readable result."
            ) from exc

        return output.get("result", {}), output.get("chart")

    @staticmethod
    def _sandbox_environment(work_path: Path) -> dict[str, str]:
        """A minimum environment: no secrets, no Python paths, scratch HOME."""
        allowed = ("PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "LANG", "LC_ALL")
        env = {key: os.environ[key] for key in allowed if key in os.environ}
        env.update(
            {
                "HOME": str(work_path),
                "TMPDIR": str(work_path),
                "TEMP": str(work_path),
                "TMP": str(work_path),
                "MPLCONFIGDIR": str(work_path / "mpl"),
                "PYTHONNOUSERSITE": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )
        return env

    @staticmethod
    def _child_limits() -> Any:
        """Build a POSIX ``preexec_fn`` that caps the child's resources."""

        def limit() -> None:  # pragma: no cover - runs in the forked child
            import resource

            resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
            resource.setrlimit(resource.RLIMIT_AS, (1_073_741_824, 1_073_741_824))
            resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024 * 1024, 16 * 1024 * 1024))
            resource.setrlimit(resource.RLIMIT_NPROC, (32, 32))

        return limit

    #: Modules generated code may import. Everything else is host access, not
    #: analysis: pandas/numpy are preloaded, so imports are rarely needed.
    _ALLOWED_IMPORT_ROOTS = frozenset(
        {"pandas", "numpy", "matplotlib", "seaborn", "json", "math", "statistics", "datetime"}
    )

    _FORBIDDEN_CODE_PATTERNS: tuple[tuple[str, str], ...] = (
        (r"__", "dunder access"),
        (
            r"\b(?:eval|exec|compile|getattr|setattr|delattr|globals|locals|vars|input|breakpoint|open)\s*\(",
            "dynamic execution or file access",
        ),
        (
            r"\b(?:os|sys|subprocess|socket|requests|urllib|http|ftplib|smtplib|ctypes|"
            r"importlib|pickle|shutil|pathlib|glob|tempfile|builtins|multiprocessing)\b",
            "host or network access",
        ),
        (
            r"\.(?:read_[a-z_]+|to_(?:csv|pickle|excel|sql|parquet|html|xml|clipboard))\s*\(",
            "file access",
        ),
        (r"\bwhile\s+(?:True|1)\s*:", "unbounded loop"),
    )

    def _validate_code_safety(self, code: str) -> None:
        """Reject code that reaches outside the analysis sandbox (design FR-H4)."""
        for pattern, reason in self._FORBIDDEN_CODE_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                logger.warning(
                    "analytics.analysis_code_rejected",
                    extra={"event": "analytics.analysis_code_rejected", "reason": reason},
                )
                raise ValidationError(
                    "The generated analysis code contains a disallowed operation."
                )

        for line in code.splitlines():
            stripped = line.strip()
            modules: list[str] = []
            if stripped.startswith("import "):
                modules = [part.split(" as ")[0].strip() for part in stripped[7:].split(",")]
            elif stripped.startswith("from "):
                modules = [stripped[5:].split(" import ")[0].strip()]

            for module in modules:
                if module.split(".")[0] not in self._ALLOWED_IMPORT_ROOTS:
                    raise ValidationError(
                        "The generated analysis code imports a disallowed module."
                    )

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
