# Task List: Question/Answer Orchestration System (Direct Context)

This task list reflects the three-agent system (Question, Answer, Orchestrator) development plan.

**Phase 1: Agent Foundations (COMPLETED)**

*   [x] **T1.1:** ~~Initialize Git repository.~~
*   [x] **T1.2:** ~~Set up virtual environment and dependency management.~~
*   [x] **T1.3:** ~~Ensure `LLMInterface` is set up for `gpt-o3-mini` (proxy/API keys).~~
*   [x] **T1.4:** ~~Verify/adapt `file_handler.py` for reading full content.~~
*   [x] **T1.5:** ~~Design Answer Agent prompt V1 structure.~~
*   [x] **T1.6:** ~~Implement `estimate_token_count` function.~~
*   [x] **T1.7:** ~~Determine approximate token limit for `gpt-o3-mini`.~~
*   [x] **T1.8:** ~~Implement core Answer Agent logic (`ask_question`, `ask_with_content` in `answer_agent.py`).~~
*   [x] **T1.9:** ~~Write unit tests for `estimate_token_count`.~~
*   [x] **T1.10:** ~~Write unit tests for Answer Agent logic.~~
*   [x] **T1.11:** ~~Create basic interactive CLI for Answer Agent (`chat` command in `main.py`).~~
*   [x] **T1.12:** ~~Design Question Agent prompt V1.~~
*   [x] **T1.13:** ~~Implement `QuestionAgent` class (`src/core/question_agent.py`), including response parsing.~~
*   [x] **T1.14:** ~~Write unit tests for `QuestionAgent`.~~
*   [x] **T1.15:** ~~Create basic CLI for Question Agent (`generate-questions` command in `main.py`).~~
*   [x] **T1.16:** ~~Update `README.md` for initial standalone agent CLIs.~~

**Phase 2: Orchestrator Agent Development**

*   [x] **T2.1:** Design Orchestrator prompt V1 for Satisfaction Check.
*   [x] **T2.2:** Design Orchestrator prompt V1 for Follow-up Question Generation.
*   [x] **T2.3:** Create `src/core/orchestrator.py`.
*   [x] **T2.4:** Implement `Orchestrator` class skeleton (`__init__`, method signatures).
*   [x] **T2.5:** Implement Orchestrator initialization (accept Answer/Question agents).
*   [x] **T2.6:** Implement Orchestrator's main loop logic (`run_interaction`):
    *   Call Question Agent to get initial questions.
    *   Loop through initial questions.
*   [x] **T2.7:** Implement Orchestrator's inner loop logic:
    *   Call Answer Agent to get answer for current question.
    *   Call LLM for satisfaction check.
    *   Parse satisfaction check response.
    *   If unsatisfactory, call LLM for follow-up question.
    *   Parse follow-up question response.
    *   Handle retry limit.
*   [x] **T2.8:** Implement Orchestrator LLM calls (satisfaction, follow-up) using `LLMInterface` (Note: Actual LLM calls are placeholders for now).
*   [x] **T2.9:** Implement Orchestrator state management (current Q, retry count, etc.).
*   [x] **T2.10:** Implement user interaction prompt (continue/stop).
*   [x] **T2.11:** Create `tests/test_orchestrator.py`.
*   [x] **T2.12:** Write unit tests for `Orchestrator` (mock agents, LLM calls, test loops, parsing).

**Phase 3: CLI Integration & Full Workflow Testing**

*   [x] **T3.1:** Update `main.py` CLI: Add `orchestrate <q_doc_path> <a_doc_path>` command (using Typer).
*   [x] **T3.2:** Implement logic in `main.py` to instantiate agents and orchestrator for the `orchestrate` command.
*   [x] **T3.3:** Implement logic in `main.py` to call the Orchestrator's `run_interaction` method.
*   [x] **T3.4:** Perform end-to-end testing using the `orchestrate` command (initial successful run).
*   [ ] **T3.5:** Evaluate satisfaction check accuracy (human judgment - pending further runs).
*   [ ] **T3.6:** Evaluate follow-up question quality (human judgment - pending further runs).
*   [ ] **T3.7:** Evaluate overall workflow behavior (human judgment - pending further runs).
*   [x] **T3.8:** Refine Orchestrator prompts (T2.1, T2.2) based on evaluation (pending T3.5-T3.7).
*   [x] **T3.9:** Update `README.md` with instructions for `orchestrate` command and the overall system concept.

**Phase 4: Refinement & Evaluation**

*   [ ] **T4.1:** Conduct further end-to-end testing with various documents (CLI and Streamlit).
*   [ ] **T4.2:** Test context limit handling for *all* LLM calls (agents + orchestrator).
*   [ ] **T4.3:** Measure performance/latency for the full orchestrated loop.
*   [ ] **T4.4:** *(Optional)* Add more sophisticated error handling or state display.
*   [x] **T4.5:** Finalize documentation (CLI and Streamlit UI documented in README).
*   [x] **T4.6:** Implement Streamlit UI (`streamlit_app.py`):
    *   [x] **T4.6.1:** Refactor `Orchestrator.run_interaction` to return results.
    *   [x] **T4.6.2:** Add `streamlit` to `requirements.txt`.
    *   [x] **T4.6.3:** Create `streamlit_app.py` with UI elements (uploaders, inputs, button).
    *   [x] **T4.6.4:** Implement agent/orchestrator initialization and invocation in Streamlit app.
    *   [x] **T4.6.5:** Implement results display logic (step-by-step) in Streamlit app.
    *   [x] **T4.6.6:** Implement message auto-scrolling functionality with JavaScript.
    *   [x] **T4.6.7:** Create messaging-style UI with directional message alignment.
    *   [x] **T4.6.8:** Implement responsive chat container sizing.
*   [x] **T4.7:** Update `README.md` with instructions for running Streamlit app.

**Phase 5: Future Development Planning**

*   [ ] **T5.1:** Plan RAG implementation for all agents.
*   [ ] **T5.2:** Plan Orchestrator logic improvements (satisfaction, follow-up, user override).
*   [ ] **T5.3:** Gather user feedback.
*   [ ] **T5.4:** Address bugs. 