# High-Level Implementation Plan: Question/Answer Orchestration System (Direct Context)

This plan covers the development of the Answer Agent, Question Agent, and the Orchestrator Agent, focusing on the interactive workflow using the direct context approach and providing CLI and Web UI access.

**Phase 1: Agent Foundations (COMPLETED)**

*   **Goal:** Set up project, implement report reading, develop core answer generation logic (Answer Agent) and question generation logic (Question Agent) using direct LLM context, build basic standalone CLIs for testing.
*   **Key Activities:** Environment setup, file handling, Answer Agent prompt design, `AnswerAgent` implementation, Question Agent prompt design, `QuestionAgent` implementation, token limit checks for both, unit tests for both, basic CLIs (`chat`, `generate-questions`) in `main.py`.

**Phase 2: Orchestrator Agent Development (COMPLETED)**

*   **Goal:** Develop the Orchestrator Agent to manage the core interactive loop, including LLM-based satisfaction checks and follow-up question generation.
*   **Key Activities:** Design prompts (Satisfaction Check, Follow-up), Implement `Orchestrator` class (`src/core/orchestrator.py`) including loop logic, LLM calls (satisfaction/follow-up), response parsing, state management. Write unit tests for `Orchestrator` (mocking agents and LLM calls).

**Phase 3: CLI Integration & Initial Workflow Testing (COMPLETED)**

*   **Goal:** Integrate the Orchestrator into the main CLI (`typer`) and test the end-to-end interactive console workflow.
*   **Key Activities:** Update `main.py` CLI: Add `orchestrate` command, instantiate agents/orchestrator, call orchestrator. Perform end-to-end testing with the `orchestrate` command using sample documents. Verify interactive loop (initial Qs -> answers -> satisfaction -> follow-ups -> user prompt -> next Q/stop). Perform initial evaluation of satisfaction/follow-up quality. Update `README.md` for CLI usage.

**Phase 4: Web UI & Refinement (In Progress)**

*   **Goal:** Implement a Streamlit web interface for the orchestrated workflow. Refine agents and orchestrator based on further testing.
*   **Key Activities:**
    *   Refactor `Orchestrator` to return results for batch processing by UI.
    *   Add `streamlit` dependency.
    *   Implement `streamlit_app.py`:
        *   UI components (file upload, parameters, buttons).
        *   Agent/Orchestrator initialization.
        *   Call orchestrator and handle results.
        *   Implement step-by-step display logic using session state.
    *   Update `README.md` for Streamlit usage.
    *   **T4.1:** Conduct further end-to-end testing with diverse documents (CLI and Streamlit).
    *   **T4.2:** Explicitly test context limit handling for *all* LLM calls.
    *   **T4.3:** Performance testing (measure latency).
    *   **T4.4:** *(Optional)* Add more sophisticated error handling or state display.
    *   **T4.5:** Finalize documentation.

**Phase 5: Future Development Planning (Ongoing)**

*   **Goal:** Prioritize future improvements based on current limitations and feedback.
*   **Key Activities:** Plan for RAG implementation, Orchestrator logic improvements, user feedback integration, address bugs. 