"""Unit tests for the analytics code sandbox (design FR-H4)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.errors import ValidationError
from app.services.analytics_service import AnalyticsService


@pytest.fixture
def service() -> AnalyticsService:
    return AnalyticsService(repository=AsyncMock(), llm_provider=AsyncMock())


@pytest.mark.unit
@pytest.mark.parametrize(
    "code",
    [
        "import os\nresult['x'] = os.listdir('/')",
        "result['x'] = open('/etc/passwd').read()",
        "result['x'] = __import__('os').system('id')",
        "result['x'] = getattr(__builtins__, 'eval')('1+1')",
        "import subprocess\nresult['x'] = 1",
        "result['x'] = pd.read_pickle('/tmp/x.pkl')",
        "result['x'] = df.to_csv('/tmp/out.csv')",
        "while True:\n    pass",
        "result['x'] = df.__class__",
        "from pathlib import Path\nresult['x'] = Path('/').read_text()",
    ],
)
def test_rejects_host_access(service: AnalyticsService, code: str) -> None:
    with pytest.raises(ValidationError):
        service._validate_code_safety(code)


@pytest.mark.unit
def test_allows_ordinary_pandas_analysis(service: AnalyticsService) -> None:
    service._validate_code_safety(
        "import pandas as pd\n"
        "import matplotlib.pyplot as plt\n"
        "result['mean'] = float(df['value'].mean())\n"
        "result['rows'] = int(len(df))\n"
        "chart = {'type': 'bar', 'data': df.groupby('group')['value'].sum().to_dict()}"
    )


@pytest.mark.unit
async def test_executes_harmless_analysis_in_isolation(service: AnalyticsService) -> None:
    result, chart = await service._execute_analysis_code(
        "result['mean'] = float(df['value'].mean())\nresult['rows'] = int(len(df))",
        b"value\n1\n3\n",
    )

    assert result == {"mean": 2.0, "rows": 2}
    assert chart is None
