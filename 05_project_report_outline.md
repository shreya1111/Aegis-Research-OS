# B.Tech Major Project Report Outline — Aegis Research OS

Map your write-up to this structure as you complete each phase, rather than writing it all at the
end. Suggested source phase for each section is noted in brackets.

1. **Title Page & Certificate** (standard institute format)
2. **Abstract** (write last — 200–300 words summarizing problem, approach, results)
3. **Acknowledgements**
4. **Table of Contents, List of Figures, List of Tables**

5. **Introduction**
   - Problem statement: manual literature review and research synthesis is slow and error-prone
   - Motivation and objectives
   - Scope of the project (explicitly state MVP vs stretch features delivered) [Phase 0]

6. **Literature Survey**
   - Review of comparable systems: Perplexity, NotebookLM, Elicit, OpenAI Deep Research
   - Gaps these systems leave that Aegis Research OS addresses [Phase 0]

7. **System Analysis**
   - Requirement analysis (functional + non-functional)
   - Feasibility study
   - Existing vs proposed system comparison

8. **System Design**
   - Architecture diagram [Phase 0, `04_architecture_and_specs.md`]
   - Database ER diagram and schema [Phase 0/1]
   - Agent design and interaction diagram [Phase 5]
   - API design [Phase 0]
   - UML diagrams: use-case, sequence (e.g., "user asks a research question" flow), class diagram
     for core backend modules

9. **Implementation**
   - Technology stack justification
   - Module-by-module implementation summary (one subsection per phase 1–9)
   - Key algorithms: chunking strategy, hybrid retrieval + fusion, agent orchestration logic
   - Screenshots of the working UI per major feature

10. **Testing**
    - Test strategy (unit, integration, load)
    - Test cases and results table
    - Gold-standard retrieval evaluation results (precision\@k, citation accuracy) [Phase 4]
    - Bug tracking summary

11. **Results & Evaluation**
    - Demo walkthrough (with screenshots) of a full user journey: signup → upload → query →
      generated literature review → export
    - Performance metrics against the non-functional targets in `04_architecture_and_specs.md`
    - Cost analysis: tokens/cost per query type, caching impact [Phase 5/10]

12. **Security & Ethical Considerations**
    - Data privacy for uploaded documents
    - LLM hallucination risk and mitigation (Critic agent, citation grounding)
    - Sandboxing of code execution (if Phase 8 built)

13. **Conclusion & Future Scope**
    - Summary of what was achieved (be explicit about MVP vs stretch delivered)
    - Honest limitations
    - Future work: features from Phases 7/8/10 not completed, scaling considerations

14. **References** (IEEE/APA format per institute requirement)

15. **Appendices**
    - Full API reference
    - Selected source code listings
    - User manual / setup guide
