# Task List: Multi-Agent Q&A Debate System

This task list documents the development of the multi-agent debate system.

**Phase 1: Agent Foundations (COMPLETED)**

*   [x] **T1.1:** Initialize Git repository.
*   [x] **T1.2:** Set up virtual environment and dependency management (`requirements.txt`).
*   [x] **T1.3:** Implement `LLMInterface` for centralized LLM access.
*   [x] **T1.4:** Implement `file_handler.py` for reading documents.
*   [x] **T1.5:** Design Answer Agent prompt structure (`prompts.py`).
*   [x] **T1.6:** Implement `estimate_token_count` function (`token_utils.py`).
*   [x] **T1.7:** Implement core Answer Agent logic (`ReportQAAgent` in `answer_agent.py`).
*   [x] **T1.8:** Write unit tests for `token_utils` and `answer_agent`.
*   [x] **T1.9:** Design Question Agent prompt (`prompts.py`).
*   [x] **T1.10:** Implement `QuestionAgent` class (`question_agent.py`).
*   [x] **T1.11:** Write unit tests for `QuestionAgent`.
*   [x] **T1.12:** Create initial CLI (`main.py`) for testing individual agents (now legacy).

**Phase 2: Orchestrator V1 & Initial UI (Completed, Now Legacy)**

*   [x] **T2.1:** Implement V1 Orchestrator (`orchestrator.py`) for satisfaction/follow-up loop.
*   [x] **T2.2:** Write tests for `orchestrator.py`.
*   [x] **T2.3:** Integrate V1 Orchestrator into CLI (`main.py orchestrate`).
*   [x] **T2.4:** Implement V1 Streamlit UI (`streamlit_app.py`) for V1 workflow.

**Phase 3: V2 Multi-Agent Debate Core (COMPLETED)**

*   [x] **T3.1:** Create `OrchestratorV2` class (`orchestrator_v2.py`).
*   [x] **T3.2:** Implement `OrchestratorV2` initialization (1 QA, list of AAs).
*   [x] **T3.3:** Implement `OrchestratorV2.run_debate_interaction` generator logic (generate questions, distribute to AAs, collect answers).
*   [x] **T3.4:** Design prompt for answer synthesis/debate (`prompts.py`).
*   [x] **T3.5:** Implement LLM call within `OrchestratorV2` for synthesis.
*   [x] **T3.6:** Implement output file writing in `OrchestratorV2`.
*   [x] **T3.7:** Write unit tests for `OrchestratorV2` (`test_orchestrator_v2.py`).
*   [x] **T3.8:** Add CLI command (`main.py orchestrate_v2`) for V2 workflow (now secondary usage).

**Phase 4: V2 Streamlit UI & Finalization (COMPLETED)**

*   [x] **T4.1:** Create `streamlit_app_v2.py` based on V1 UI.
*   [x] **T4.2:** Modify V2 UI for multiple answer doc uploads and output filename config.
*   [x] **T4.3:** Implement `streamlit_app_v2.py` backend:
    *   [x] Handle file uploads and temp file creation.
    *   [x] Instantiate all agents and `OrchestratorV2`.
    *   [x] Call `OrchestratorV2.run_debate_interaction`.
    *   [x] Implement temp file cleanup.
*   [x] **T4.4:** Implement progressive chat display in V2 UI by iterating through the `OrchestratorV2` generator.
*   [x] **T4.5:** Implement custom styling for V2 chat messages (colors, alignment, width, system message format).
*   [x] **T4.6:** Add unit tests for `streamlit_app_v2.py` setup and basic interaction logic.
*   [x] **T4.7:** Resolve all test failures and ensure `pytest` passes.
*   [x] **T4.8:** Update `README.md` to reflect final V2 system and usage.
*   [x] **T4.9:** Update `prd.md` to reflect final V2 system requirements.
*   [x] **T4.10:** Update `task_list.md` (this file) to reflect completed steps.

**Phase 5: Future Considerations**

*   [ ] **T5.1:** Plan RAG implementation for agents to handle larger documents.
*   [ ] **T5.2:** Explore more advanced debate/synthesis strategies.
*   [ ] **T5.3:** Consider user feedback mechanisms within the UI.
*   [ ] **T5.4:** Investigate support for different/newer LLM models.

**Phase 6: V3 Multi-Round Debate Implementation (NEW)**

*   [x] **T6.1:** Design prompts for `AnswerAgentV3.participate_in_debate` method.
*   [x] **T6.2:** Design prompt for `OrchestratorV3` post-debate synthesis.
*   [x] **T6.3:** Implement/Modify `AnswerAgentV3` (or `ReportQAAgent`) to include `participate_in_debate` method using new prompt.
*   [x] **T6.6:** Write unit tests for `AnswerAgentV3` (`test_answer_agent_v3.py`).
*   [x] **T6.4:** Implement `OrchestratorV3` class (`orchestrator_v3.py`).
*   [x] **T6.5:** Implement `OrchestratorV3.run_full_debate` generator logic:
    *   [x] Initial question generation.
    *   [x] Round 0: Call `ask_question` on `AnswerAgentV3` instances, yield flattened output.
    *   [x] Debate Rounds Loop (1 to `max_debate_rounds`):
        *   [x] Call `participate_in_debate` on agents, passing history.
        *   [x] Yield flattened output for each agent turn.
        *   [x] Update debate history.
    *   [x] Call internal synthesis method.
    *   [x] Yield flattened synthesis output.
    *   [x] Write final Q/A to file.
*   [x] **T6.7:** Write unit tests for `OrchestratorV3` (`test_orchestrator_v3.py`), mocking agents and focusing on loop logic and flattened yield format.
*   [x] **T6.8:** Add CLI command (`main.py orchestrate_v3`) to invoke the V3 workflow.
*   [x] **T6.9:** Update documentation (`prd.md`, `file_structure.md`, `README.md`, `implementation_plan.md`, `agent_interaction_v3.md`) to include V3 details. 