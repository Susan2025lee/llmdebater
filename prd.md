**Product Requirements Document: Multi-Agent Q&A Debate System**

**1. Introduction**

This document outlines requirements for the **Multi-Agent Q&A Debate System**. The system utilizes multiple AI agents to analyze provided documents and generate consolidated answers to questions derived from those documents. The core workflow involves:

1.  **Question Agent:** Generates initial questions based on a user-provided "question document".
2.  **Answer Agents (Multiple):** Each agent receives a unique source document. They answer questions posed by the Orchestrator based *only* on their assigned document.
3.  **Orchestrator Agent (V2):** Manages the debate workflow by:
    *   Generating initial questions via the Question Agent.
    *   Distributing each question to all Answer Agents.
    *   Collecting the individual answers.
    *   Utilizing an LLM to synthesize a final, consolidated answer from the individual agent responses.
    *   Saving the Question/Final Answer pairs.

All agents use an LLM (e.g., `gpt-o3-mini`) accessed through a central `LLMInterface`. The system primarily operates via a Streamlit web interface (`streamlit_app_v2.py`).

**2. Goals**

*   **Automated Question Generation:** Generate relevant questions about a topic document.
*   **Contextual Multi-Perspective Answering:** Provide answers to questions based strictly on the content of multiple, potentially differing source documents, with each source handled by a dedicated agent.
*   **Answer Synthesis:** Consolidate potentially diverse answers from multiple agents into a single, coherent final answer using an LLM.
*   **User-Friendly Interface:** Provide an intuitive Web UI (Streamlit) for uploading documents, configuring parameters, running the debate, and viewing the results.
*   **Output Persistence:** Save the generated Question/Final Answer pairs to a user-specified file.
*   **Modularity:** Maintain distinct components for question generation, answering, orchestration, and LLM interaction.

**3. Non-Goals**

*   **Handling Documents Exceeding Context Limits:** The system relies on inputs fitting within the LLM context window. This is a known limitation.
*   **V1 Workflow Maintenance:** The previous satisfaction/follow-up loop (V1 Orchestrator, `streamlit_app.py`, related CLI commands) is considered legacy and not actively maintained or required for the final V2 system.
*   **Real-time User Interaction During Debate:** The debate runs automatically after initiation; user interaction is limited to setup and viewing results.
*   **Fact-Checking / External Knowledge:** Agents operate solely based on the provided documents.

**4. User Stories / Use Cases**

*   **As an Analyst:**
    *   I want to upload a summary document to generate questions.
    *   I want to upload multiple related reports (e.g., different versions, different perspectives) to be used by separate Answer Agents.
    *   I want the system to automatically generate questions, get answers from each report via its agent, and synthesize a final answer for each question.
    *   I want to view the process unfold in a chat interface.
    *   I want the final Question/Synthesized Answer pairs saved to a file for later review.

**5. Functional Requirements**

*   **FR-A1..A4 (Answer Agent):** Ingest assigned document, take query, generate answer from context, output answer, handle context limits.
*   **FR-Q1..Q3 (Question Agent):** Ingest question doc, generate N initial questions, output questions.
*   **FR-OV2-1: Multi-Agent Initialization:** Orchestrator V2 initializes one Question Agent and a list of Answer Agents (one per provided answer document).
*   **FR-OV2-2: Workflow Management:** Orchestrator V2 manages the flow: generate questions -> distribute question -> collect answers -> synthesize answer -> save result -> repeat for next question.
*   **FR-OV2-3: Multi-Answer Collection:** Collects answers from all active Answer Agents for the current question, handling potential errors (e.g., context length) from individual agents.
*   **FR-OV2-4: Answer Synthesis:** Uses an LLM via `LLMInterface` with a specific prompt to generate a consolidated final answer based on the collection of individual answers.
*   **FR-OV2-5: Output Management:** Writes the initial question and the synthesized final answer to a specified markdown output file.
*   **FR-UI-1: Document Upload:** Web UI allows uploading one question document and multiple answer documents.
*   **FR-UI-2: Parameter Configuration:** Web UI allows configuring the number of initial questions and the output filename.
*   **FR-UI-3: Workflow Control:** Web UI provides "Start" and "Reset" buttons.
*   **FR-UI-4: Chat Display:** Web UI displays the interaction log (system messages, questions, agent answers, synthesized answers) progressively in a styled chat format.
*   **FR-LLM-1: Centralized Interface:** All LLM interactions occur through `LLMInterface`.

**6. Non-Functional Requirements**

*   **NFR1 (Context Limitation):** System performance and functionality are limited by the LLM's context window size. This must be documented.
*   **NFR2 (Modularity):** Core logic resides in separate modules (`question_agent.py`, `answer_agent.py`, `orchestrator_v2.py`, `llm_interface.py`).
*   **NFR3 (Configuration):** LLM access details are configurable.
*   **NFR4 (Readability):** Code is well-commented and follows style guidelines.
*   **NFR5 (Testability):** Core logic is unit-testable with mocking for LLM interactions.
*   **NFR6 (Usability - Web UI):** The V2 Streamlit UI is intuitive, providing clear instructions, status updates, and error feedback. Styling enhances readability.
*   **NFR7 (Output Format):** Results are saved in a readable markdown format.

**7. Design Considerations/Constraints**

*   **Core Technology:** Python, Streamlit, `gpt-o3-mini` (or other model via `LLMInterface`).
*   **No RAG.**
*   **Orchestration:** Implemented via `OrchestratorV2` using a generator pattern to yield results step-by-step for the UI.
*   **Prompt Engineering:** Key prompts exist for question generation, answering within context, and answer synthesis/debate.
*   **UI Styling:** Custom styling applied in `streamlit_app_v2.py` for message differentiation and readability.

**8. Evaluation Metrics**

*   **Functionality:** Successful execution of the V2 debate workflow from start to finish, producing an output file.
*   **Synthesized Answer Quality:** Human judgment on the coherence, relevance, and faithfulness (to the source documents) of the final synthesized answers.
*   **Question Quality:** Relevance and insightfulness of generated questions.
*   **UI/UX:** Clarity and usability of the `streamlit_app_v2.py` interface.

**9. Future Considerations**

*   Implementing RAG to handle larger documents.
*   More sophisticated synthesis/debate strategies.
*   Allowing user feedback on synthesized answers.
*   Support for different LLM models.

**10. Open Questions**

*   What are the detailed prompt structures for the Orchestrator's satisfaction check and follow-up generation?
*   How to parse the satisfaction check response reliably (e.g., specific keywords, JSON format)?
*   How to parse the follow-up question response reliably?
*   What is a reasonable maximum number of follow-up attempts?
*   How much context (original Q, previous A/follow-ups) can realistically be passed to the Orchestrator's LLM calls within limits?
*   How will the CLI manage the setup (paths for Q-doc and A-doc)?
*   How to effectively structure prompts for multi-round debate participation (critique, refinement, defense)?
*   How to best represent the debate history for the LLM within context limits?
*   What are effective termination conditions for the debate rounds?
*   How should the final answer be determined post-debate (synthesis vs. selection)?

---

**11. V2 Workflow: Multi-Agent Debate (Alternative)**

*   **Concept:** An alternative workflow (`OrchestratorV2`) can be invoked to facilitate a debate among multiple Answer Agents.
*   **Process:**
    1.  A single `QuestionAgent` generates initial questions.
    2.  For each question, *multiple* `AnswerAgent` instances (each potentially with its own report context) provide answers independently.
    3.  `OrchestratorV2` gathers all answers for the current question.
    4.  `OrchestratorV2` uses a specific LLM prompt (the "Debate Prompt") to analyze and synthesize all provided answers into a single, consolidated "Final Answer".
    5.  The question and its Final Answer are stored in a designated output file.
    6.  The process repeats for all initial questions.
*   **Goal:** Leverage multiple perspectives (from different agents/contexts) to potentially generate a more robust or comprehensive final answer compared to the single-agent V1 workflow.
*   **Use Case:** Useful when comparing outputs based on slightly different reports or simply exploring variations in LLM responses to the same query.
*   **Requirements:**
    *   **FR-OV2-1: Multi-Agent Initialization:** `OrchestratorV2` must initialize one `QuestionAgent` and a list of `AnswerAgent` instances.
    *   **FR-OV2-2: Multi-Answer Collection:** Must collect answers from all initialized `AnswerAgents` for each question.
    *   **FR-OV2-3: Debate/Synthesis:** Must implement the centralized LLM call using the "Debate Prompt" to generate a final answer from multiple inputs.
    *   **FR-OV2-4: Output Management:** Must write Question/Final Answer pairs to a specified output file.
    *   **FR-OV2-5: CLI Integration:** A new CLI command (`orchestrate-debate`) is required to accept inputs for the question document, *multiple* answer documents, and the output file path.

---

**12. V3 Workflow: Multi-Round Debate (Experimental)**

*   **Concept:** Extend the V2 workflow to include multiple rounds of interaction between Answer Agents for each question before final synthesis.
*   **Process:**
    1.  Question Agent generates initial questions.
    2.  For each question, OrchestratorV3 initiates Round 0:
        *   Distributes question to all `AnswerAgentV3` instances.
        *   Collects initial answers.
    3.  OrchestratorV3 initiates Debate Rounds (e.g., 1 to `max_debate_rounds`):
        *   Provides the original question and the *entire debate history so far* to each `AnswerAgentV3`.
        *   Each `AnswerAgentV3` formulates a response (critique, refinement, defense) based on history and its own document.
        *   Orchestrator collects responses for the current round and adds them to the history.
    4.  After debate rounds conclude, OrchestratorV3 synthesizes a final answer based on the full debate history.
    5.  Question and Final Answer are saved to the output file.
*   **Goal:** Generate potentially more refined or nuanced answers by allowing agents to interact and challenge each other based on their respective source documents.
*   **Use Case:** Scenarios requiring deeper analysis or reconciliation of information from multiple conflicting/complementary sources.
*   **Requirements:**
    *   **FR-AAV3-1: Debate Participation:** A new or modified Answer Agent (`AnswerAgentV3`) must implement a method (`participate_in_debate`) that accepts the question, the debate history, and its document path, and generates a relevant contribution for the current round.
    *   **FR-OV3-1: Multi-Round Orchestration:** `OrchestratorV3` must manage the multi-round loop, passing the accumulating debate history to agents each round.
    *   **FR-OV3-2: Debate History Management:** `OrchestratorV3` must maintain the structured history of the debate for each question.
    *   **FR-OV3-3: Configurable Rounds:** The maximum number of debate rounds should be configurable.
    *   **FR-OV3-4: Final Synthesis (Post-Debate):** `OrchestratorV3` uses an LLM to synthesize a final answer based on the *complete* debate history.
    *   **FR-OV3-5: CLI Integration:** (Optional but recommended) A new CLI command (`orchestrate_v3`) to run this workflow.
    *   **FR-OV3-6: UI Compatibility:** `OrchestratorV3` *must* yield its output as a flattened sequence of `(speaker, message)` tuples to remain compatible with the existing `streamlit_app_v2.py` interface. This includes yielding messages indicating round transitions and using prefixes/suffixes to clarify agent roles and rounds within the flat output stream. 