"""Report generation service for Phase 6 research artifacts."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.db.models.report import Report, ReportStatus, ReportType
from app.db.repositories.report_repository import ReportRepository


class ReportService:
    """Orchestrates report generation using the agent pipeline."""

    def __init__(
        self,
        *,
        report_repository: ReportRepository,
        agent_service: Any,  # AgentService or compatible mock
    ) -> None:
        self._reports = report_repository
        self._agent_service = agent_service

    async def create_report(
        self,
        *,
        project_id: UUID,
        type: ReportType,
        title: str,
    ) -> Report:
        """Create a new report and return it in PENDING status."""
        return await self._reports.create(
            project_id=project_id,
            type=type,
            title=title,
        )

    async def generate_report(self, report: Report) -> None:
        """Generate content for a report using the agent pipeline."""
        try:
            await self._reports.update_status(report, ReportStatus.GENERATING)

            # Create appropriate research request based on report type
            request = self._build_research_request(report.type, report.title)

            # Run the agent pipeline to generate the content
            result = await self._agent_service.run(
                project_id=report.project_id,
                request=request,
            )

            # Update the report with the generated content
            await self._reports.update_content(report, result.answer)

        except Exception as e:
            # Mark the report as failed
            error_message = f"Report generation failed: {e!s}"
            await self._reports.update_error(report, error_message)
            raise

    def _build_research_request(self, report_type: ReportType, title: str) -> str:
        """Build an appropriate research request for the agent pipeline."""
        if report_type == ReportType.LITERATURE_REVIEW:
            return (
                f"Generate a comprehensive literature review on '{title}'. "
                "Provide a structured review with: 1) Introduction explaining the research area, "
                "2) Thematic sections organizing the literature by key themes or approaches, "
                "3) Synthesis highlighting relationships and patterns across sources, "
                "4) Research gaps and limitations identified in the literature, "
                "5) References section with all cited sources. "
                "Ensure all claims are properly cited with inline citations."
            )
        if report_type == ReportType.GAP_ANALYSIS:
            return (
                f"Conduct a research gap analysis on '{title}'. "
                "Identify and analyze: 1) Areas where current research is insufficient "
                "or incomplete, 2) Contradictions or disagreements between different sources, "
                "3) Methodological limitations in existing studies, "
                "4) Unexplored research questions or approaches, "
                "5) Future research directions. "
                "Support each gap identified with specific citations and evidence."
            )
        if report_type == ReportType.SOURCE_COMPARISON:
            return (
                f"Compare and contrast the key sources on '{title}'. "
                "Provide a structured comparison including: "
                "1) Methodology comparison across sources, "
                "2) Key findings and how they align or differ, "
                "3) Limitations and scope of each source, "
                "4) Strengths and weaknesses of different approaches, "
                "5) Summary table highlighting the main differences. "
                "Cite specific sources for each comparison point."
            )
        if report_type == ReportType.SURVEY:
            return (
                f"Create a comprehensive research survey on '{title}'. "
                "Provide an extensive overview including: 1) Background and context, "
                "2) Literature review of key works and developments, "
                "3) Comparative analysis of different approaches and methodologies, "
                "4) Current state of research and recent advances, "
                "5) Research gaps and future directions, "
                "6) Conclusion summarizing the field. "
                "This should be a thorough, well-structured survey suitable for "
                "researchers entering the field."
            )

        # Default case for unknown report types
        return f"Conduct comprehensive research on '{title}' and provide a structured analysis."  # type: ignore[unreachable]

    async def get_report(self, report_id: UUID, project_id: UUID) -> Report | None:
        """Get a report by ID, scoped to a project."""
        return await self._reports.get_by_id_for_project(report_id, project_id)

    async def list_reports(self, project_id: UUID) -> list[Report]:
        """List all reports for a project."""
        return await self._reports.list_for_project(project_id)

    async def delete_report(self, report: Report) -> None:
        """Delete a report."""
        await self._reports.delete(report)

    async def generate_executive_summary(self, report: Report) -> str:
        """Generate a 1-page executive summary of a report using LLM."""
        if not report.content_markdown:
            raise ValueError("Report has no content to summarize")

        # Use the agent service's LLM to generate summary
        summary_request = (
            f"Generate a concise 1-page executive summary of the following research report. "
            f"The summary should:\n"
            f"1. Capture the main research question and objectives\n"
            f"2. Highlight 3-5 key findings or insights\n"
            f"3. Identify the most important conclusions\n"
            f"4. Mention any critical limitations or gaps\n"
            f"5. Be written in clear, professional language\n"
            f"6. Be approximately 300-500 words\n\n"
            f"Report Title: {report.title}\n\n"
            f"Full Report Content:\n{report.content_markdown[:10000]}"  # Limit to avoid token limits
        )

        # Generate summary using agent service (which has LLM access)
        result = await self._agent_service.run(
            project_id=report.project_id,
            request=summary_request,
        )

        return result.answer
