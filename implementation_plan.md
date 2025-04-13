# High-Level Implementation Plan: Multi-Agent Q&A Debate System

This plan summarizes the development of the multi-agent Q&A debate system, culminating in the V2 Streamlit application.

**Phase 1: Agent Foundations (COMPLETED)**

*   **Goal:** Set up project structure, implement core file/LLM handling, develop foundational Question and Answer agents.
*   **Key Activities:** Environment setup, `LLMInterface`, `file_handler`, `token_utils`, `ReportQAAgent`, `QuestionAgent`, unit tests, basic prompts.

**Phase 2: Orchestrator V1 & Initial UI (Completed, Now Legacy)**

*   **Goal:** Develop the initial interactive workflow (V1) based on satisfaction checks and follow-ups.
*   **Key Activities:** Implement `Orchestrator` V1, design related prompts, integrate into CLI (`main.py orchestrate`), build initial Streamlit UI (`streamlit_app.py`).

**Phase 3: V2 Multi-Agent Debate Core (COMPLETED)**

*   **Goal:** Implement the core logic for the multi-agent debate workflow.
*   **Key Activities:** Implement `OrchestratorV2` (initialize multiple AAs, distribute questions, collect answers, synthesize final answer via LLM), design synthesis prompt, implement output file writing, write unit tests for `OrchestratorV2`, add V2 CLI command (`main.py orchestrate_v2`).

**Phase 4: V2 Streamlit UI & Finalization (COMPLETED)**

*   **Goal:** Build the primary Streamlit UI for the V2 debate workflow and finalize the project.
*   **Key Activities:**
    *   Refactor `OrchestratorV2` to use a generator pattern for step-by-step UI updates.
    *   Create `streamlit_app_v2.py` UI (multi-file upload, config).
    *   Implement backend logic in `streamlit_app_v2.py` (agent instantiation, orchestrator invocation, temp file handling).
    *   Implement progressive chat display using the orchestrator generator.
    *   Apply custom CSS styling for improved readability and message differentiation.
    *   Add and refine unit tests for `streamlit_app_v2.py`.
    *   Ensure all `pytest` tests pass.
    *   Update all relevant documentation (`README.md`, `prd.md`, `task_list.md`, `implementation_plan.md`) to reflect the final V2 system.

**Phase 5: Future Considerations (Post-Project)**

*   **Goal:** Identify potential next steps for enhancing the system.
*   **Key Activities:** Consider RAG implementation, advanced debate strategies, user feedback integration, support for more LLM models.

**Phase 6: V3 Multi-Round Debate Implementation (NEW)**

*   **Goal:** Implement the experimental V3 workflow with multi-round agent interaction before synthesis, ensuring compatibility with the V2 Streamlit UI.
*   **Key Activities:**
    *   Design new prompts for debate participation and post-debate synthesis.
    *   Modify `AnswerAgent` (or create `AnswerAgentV3`) to handle debate history and respond within rounds.
    *   Implement `OrchestratorV3` to manage the multi-round debate loop and final synthesis.
    *   Ensure `OrchestratorV3` yields flattened `(speaker, message)` tuples.
    *   Add unit tests for new/modified agent and orchestrator logic.
    *   Add CLI entry point (`orchestrate_v3`).
    *   Update all documentation to describe V3. 