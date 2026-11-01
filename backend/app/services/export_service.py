"""Export service for converting reports to various formats."""

from __future__ import annotations

import importlib.util
import io
import re
from enum import Enum

import markdown
from docx import Document
from docx.shared import Pt, RGBColor

from app.core.errors import ExportError
from app.db.models.report import Report

# Probe for WeasyPrint without importing it: it requires system libraries
# (GTK+, Pango, Cairo) whose absence raises OSError at import time on Windows.
_weasyprint_available = importlib.util.find_spec("weasyprint") is not None


class ExportFormat(str, Enum):
    """Supported export formats for research artifacts."""

    HTML = "html"
    MARKDOWN = "markdown"
    PDF = "pdf"
    DOCX = "docx"
    LATEX = "latex"


class ExportService:
    """Handles export of research artifacts to various formats."""

    def __init__(self) -> None:
        # Configure markdown with extensions for better formatting
        self._markdown = markdown.Markdown(
            extensions=[
                'markdown.extensions.tables',
                'markdown.extensions.fenced_code',
                'markdown.extensions.toc',
                'markdown.extensions.footnotes',
            ]
        )

    async def export_report(
        self,
        report: Report,
        format: ExportFormat
    ) -> tuple[bytes, str, str]:
        """
        Export a report to the specified format.
        
        Returns:
            tuple[bytes, str, str]: (content, filename, content_type)
        """
        if not report.content_markdown:
            raise ExportError("Report has no content to export")

        try:
            if format == ExportFormat.HTML:
                return await self._export_html(report)
            elif format == ExportFormat.MARKDOWN:
                return await self._export_markdown(report)
            elif format == ExportFormat.PDF:
                return await self._export_pdf(report)
            elif format == ExportFormat.DOCX:
                return await self._export_docx(report)
            elif format == ExportFormat.LATEX:
                return await self._export_latex(report)
            else:
                raise ExportError(f"Unsupported export format: {format}")
        except Exception as e:
            raise ExportError(f"Export failed: {e!s}") from e

    async def _export_html(self, report: Report) -> tuple[bytes, str, str]:
        """Export report as HTML."""
        if not report.content_markdown:
            raise ExportError("Report has no content to export")

        html_content = self._markdown.convert(report.content_markdown)
        styled_html = self._create_styled_html(report.title, html_content)

        filename = self._make_filename(report.title, "html")
        return styled_html.encode('utf-8'), filename, "text/html"

    async def _export_markdown(self, report: Report) -> tuple[bytes, str, str]:
        """Export report as Markdown."""
        content = f"# {report.title}\n\n{report.content_markdown}"
        filename = self._make_filename(report.title, "md")
        return content.encode('utf-8'), filename, "text/markdown"

    async def _export_latex(self, report: Report) -> tuple[bytes, str, str]:
        """Export report as LaTeX."""
        if not report.content_markdown:
            raise ExportError("Report has no content to export")

        latex_content = self._markdown_to_latex(report.title, report.content_markdown)
        filename = self._make_filename(report.title, "tex")
        return latex_content.encode('utf-8'), filename, "application/x-latex"

    async def _export_pdf(self, report: Report) -> tuple[bytes, str, str]:
        """Export report as PDF using WeasyPrint."""
        if not _weasyprint_available:
            raise ExportError(
                "PDF export is not available. WeasyPrint requires system libraries "
                "(GTK+, Pango, Cairo) which are not installed on this system. "
                "Use DOCX or HTML export instead, or install the required libraries."
            )
        
        if not report.content_markdown:
            raise ExportError("Report has no content to export")

        # Convert markdown to HTML first
        html_content = self._markdown.convert(report.content_markdown)
        styled_html = self._create_styled_html(report.title, html_content)

        # Convert HTML to PDF
        from weasyprint import HTML

        pdf_bytes = HTML(string=styled_html).write_pdf()

        filename = self._make_filename(report.title, "pdf")
        return pdf_bytes, filename, "application/pdf"

    async def _export_docx(self, report: Report) -> tuple[bytes, str, str]:
        """Export report as DOCX using python-docx."""
        if not report.content_markdown:
            raise ExportError("Report has no content to export")

        document = Document()

        # Title
        title = document.add_heading(report.title, level=0)
        title.alignment = 1  # Center
        
        # Process markdown content line by line
        lines = report.content_markdown.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
            
            # Handle headers
            if line.startswith('### '):
                document.add_heading(line[4:], level=3)
            elif line.startswith('## '):
                document.add_heading(line[3:], level=2)
            elif line.startswith('# '):
                document.add_heading(line[2:], level=1)
            # Handle lists
            elif line.startswith('- ') or line.startswith('* '):
                document.add_paragraph(line[2:], style='List Bullet')
            elif re.match(r'^\d+\. ', line):
                document.add_paragraph(re.sub(r'^\d+\. ', '', line), style='List Number')
            # Handle blockquotes
            elif line.startswith('> '):
                p = document.add_paragraph(line[2:])
                p.style = 'Intense Quote'
            # Handle regular paragraphs
            else:
                p = document.add_paragraph()
                self._add_formatted_text(p, line)
            
            i += 1

        # Save to bytes
        docx_bytes = io.BytesIO()
        document.save(docx_bytes)
        docx_bytes.seek(0)

        filename = self._make_filename(report.title, "docx")
        return docx_bytes.getvalue(), filename, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    def _add_formatted_text(self, paragraph, text: str) -> None:
        """Add formatted text to a paragraph (bold, italic, code)."""
        # Simple regex-based formatting
        parts = re.split(r'(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\([^)]+\))', text)
        
        for part in parts:
            if not part:
                continue
            if part.startswith('**') and part.endswith('**'):
                # Bold
                run = paragraph.add_run(part[2:-2])
                run.bold = True
            elif part.startswith('*') and part.endswith('*'):
                # Italic
                run = paragraph.add_run(part[1:-1])
                run.italic = True
            elif part.startswith('`') and part.endswith('`'):
                # Code
                run = paragraph.add_run(part[1:-1])
                run.font.name = 'Courier New'
                run.font.size = Pt(10)
            elif part.startswith('[') and '](' in part:
                # Link - extract text
                match = re.match(r'\[([^\]]+)\]\([^)]+\)', part)
                if match:
                    run = paragraph.add_run(match.group(1))
                    run.font.color.rgb = RGBColor(0, 0, 255)
                else:
                    paragraph.add_run(part)
            else:
                paragraph.add_run(part)

    def _create_styled_html(self, title: str, content: str) -> str:
        """Create a styled HTML document."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            color: #333;
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: #2c3e50;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }}
        h1 {{
            border-bottom: 2px solid #3498db;
            padding-bottom: 0.5rem;
        }}
        blockquote {{
            border-left: 4px solid #3498db;
            padding-left: 1rem;
            margin-left: 0;
            font-style: italic;
        }}
        code {{
            background-color: #f8f9fa;
            padding: 0.2rem 0.4rem;
            border-radius: 3px;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
        }}
        pre {{
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 5px;
            overflow-x: auto;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1rem 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 0.75rem;
            text-align: left;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: 600;
        }}
        .citation {{
            color: #3498db;
            font-weight: 500;
        }}
        @media print {{
            body {{ margin: 0; }}
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    {content}
</body>
</html>"""

    def _markdown_to_latex(self, title: str, markdown_content: str) -> str:
        """Convert markdown to LaTeX format."""
        latex_content = markdown_content

        # Replace markdown headers with LaTeX commands
        latex_content = re.sub(
            r'^### (.+)$', r'\\subsubsection{\1}', latex_content, flags=re.MULTILINE
        )
        latex_content = re.sub(r'^## (.+)$', r'\\subsection{\1}', latex_content, flags=re.MULTILINE)
        latex_content = re.sub(r'^# (.+)$', r'\\section{\1}', latex_content, flags=re.MULTILINE)

        # Replace bold and italic
        latex_content = re.sub(r'\*\*([^*]+)\*\*', r'\\textbf{\1}', latex_content)
        latex_content = re.sub(r'\*([^*]+)\*', r'\\textit{\1}', latex_content)

        # Replace code blocks
        latex_content = re.sub(r'`([^`]+)`', r'\\texttt{\1}', latex_content)

        # Create complete LaTeX document
        return f"""\\documentclass[12pt]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage{{geometry}}
\\usepackage{{hyperref}}
\\usepackage{{booktabs}}
\\usepackage{{amsmath}}
\\usepackage{{amsfonts}}

\\geometry{{margin=1in}}

\\title{{{title}}}
\\author{{Generated by Aegis Research OS}}
\\date{{\\today}}

\\begin{{document}}

\\maketitle

{latex_content}

\\end{{document}}
"""

    def _make_filename(self, title: str, extension: str) -> str:
        """Create a safe filename from the report title."""
        # Remove or replace unsafe characters
        safe_title = re.sub(r'[^\w\s-]', '', title)
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        safe_title = safe_title.strip('-').lower()

        # Limit length
        if len(safe_title) > 50:
            safe_title = safe_title[:50].rstrip('-')

        return f"{safe_title}.{extension}"
