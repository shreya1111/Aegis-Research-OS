"""Unit tests for report export (Phase 9), including escaping of untrusted content."""

from __future__ import annotations

import io
import re
from types import SimpleNamespace
from typing import Any, cast

import pytest
from docx import Document

from app.core.errors import ExportError
from app.db.models.report import Report
from app.services.export_service import ExportFormat, ExportService


def _report(
    title: str = "Climate review", content: str | None = "# Heading\n\nBody text"
) -> Report:
    return cast(Report, SimpleNamespace(title=title, content_markdown=content))


@pytest.fixture
def service() -> ExportService:
    return ExportService()


@pytest.mark.unit
async def test_markdown_export_prefixes_the_title(service: ExportService) -> None:
    content, filename, media_type = await service.export_report(_report(), ExportFormat.MARKDOWN)

    assert content.decode().startswith("# Climate review\n\n# Heading")
    assert filename == "climate-review.md"
    assert media_type == "text/markdown"


@pytest.mark.unit
async def test_html_export_renders_markdown(service: ExportService) -> None:
    content, filename, media_type = await service.export_report(_report(), ExportFormat.HTML)

    html_text = content.decode()
    assert ">Heading</h1>" in html_text
    assert "<p>Body text</p>" in html_text
    assert filename == "climate-review.html"
    assert media_type == "text/html"


@pytest.mark.unit
async def test_html_export_escapes_the_title(service: ExportService) -> None:
    content, _, _ = await service.export_report(
        _report(title="<script>alert(1)</script>"), ExportFormat.HTML
    )

    assert "<script>alert(1)</script>" not in content.decode()
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in content.decode()


@pytest.mark.unit
@pytest.mark.parametrize(
    "body",
    [
        "<script>alert(1)</script>",
        "text with <img src=x onerror=alert(1)> inline",
        "<iframe src='https://evil.example'></iframe>",
    ],
)
async def test_html_export_does_not_pass_raw_html_through(
    service: ExportService, body: str
) -> None:
    content, _, _ = await service.export_report(_report(content=body), ExportFormat.HTML)

    rendered = content.decode().split("<body>", 1)[1]
    assert "<script" not in rendered
    assert "<iframe" not in rendered
    assert "<img" not in rendered


@pytest.mark.unit
@pytest.mark.parametrize(
    "link",
    [
        "[click](javascript:alert(1))",
        "[click](  JavaScript:alert(1))",
        "[click](data:text/html;base64,PHNjcmlwdD4=)",
        "<javascript:alert(1)>",
    ],
)
async def test_html_export_neutralises_script_urls(service: ExportService, link: str) -> None:
    content, _, _ = await service.export_report(_report(content=link), ExportFormat.HTML)

    rendered = content.decode().split("<body>", 1)[1]
    assert not re.search(
        r"(?:href|src)\s*=\s*[\"']\s*(?:javascript|data):", rendered, re.IGNORECASE
    )


@pytest.mark.unit
async def test_html_export_keeps_safe_links(service: ExportService) -> None:
    content, _, _ = await service.export_report(
        _report(content="[paper](https://arxiv.org/abs/1706.03762)"), ExportFormat.HTML
    )

    assert 'href="https://arxiv.org/abs/1706.03762"' in content.decode()


@pytest.mark.unit
async def test_latex_export_builds_a_document(service: ExportService) -> None:
    content, filename, media_type = await service.export_report(
        _report(content="# Intro\n\n**bold** and *italic* and `code`"), ExportFormat.LATEX
    )

    latex = content.decode()
    assert latex.startswith("\\documentclass[12pt]{article}")
    assert "\\section{Intro}" in latex
    assert "\\textbf{bold}" in latex
    assert "\\textit{italic}" in latex
    assert "\\texttt{code}" in latex
    assert latex.rstrip().endswith("\\end{document}")
    assert filename == "climate-review.tex"
    assert media_type == "application/x-latex"


@pytest.mark.unit
async def test_latex_export_escapes_control_characters(service: ExportService) -> None:
    content, _, _ = await service.export_report(
        _report(
            title="R&D_100% {draft}",
            content="Cost is $5 & 50% of #1 \\input{/etc/passwd} a_b ~ x^2",
        ),
        ExportFormat.LATEX,
    )

    latex = content.decode()
    assert "\\title{R\\&D\\_100\\% \\{draft\\}}" in latex
    assert "Cost is \\$5 \\& 50\\% of \\#1" in latex
    assert "\\textbackslash{}input\\{/etc/passwd\\}" in latex
    assert "a\\_b \\textasciitilde{} x\\textasciicircum{}2" in latex
    assert "\\input{/etc/passwd}" not in latex


@pytest.mark.unit
async def test_docx_export_is_a_readable_document(service: ExportService) -> None:
    content, filename, media_type = await service.export_report(
        _report(content="## Methods\n\n- first\n- second\n\nSome **bold** text"),
        ExportFormat.DOCX,
    )

    document = Document(io.BytesIO(content))
    texts = [paragraph.text for paragraph in document.paragraphs]
    assert "Climate review" in texts
    assert "Methods" in texts
    assert "first" in texts
    assert "Some bold text" in texts
    assert filename == "climate-review.docx"
    assert media_type.endswith("wordprocessingml.document")


@pytest.mark.unit
@pytest.mark.parametrize("fmt", list(ExportFormat))
async def test_export_rejects_a_report_without_content(
    service: ExportService, fmt: ExportFormat
) -> None:
    with pytest.raises(ExportError):
        await service.export_report(_report(content=None), fmt)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("A Very Long Title " * 10, None),
        ("研究報告", "report.md"),
        ("../../etc/passwd", "etcpasswd.md"),
        ('quo"te; name=x', "quote-namex.md"),
        ("   ", "report.md"),
    ],
)
def test_filenames_are_ascii_and_header_safe(
    service: ExportService, title: str, expected: str | None
) -> None:
    name: Any = service._make_filename(title, "md")

    assert name.isascii()
    assert '"' not in name
    assert ";" not in name
    assert "/" not in name
    assert name.endswith(".md")
    if expected is not None:
        assert name == expected
    else:
        assert len(name) <= 53
