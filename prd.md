**Product Requirements Document: Orchestrated Question/Answer Agent System (Direct Context)**

**1. Introduction**

This document outlines requirements for the **Orchestrated Question/Answer Agent System (Direct Context version)**. This system employs three AI agents:

1.  **Answer Agent:** Answers a given question based *only* on the content of its assigned report file (loaded entirely into LLM context).
2.  **Question Agent:** Analyzes an assigned input document and generates a list of initial questions about its content (using direct LLM context).
3.  **Orchestrator Agent:** Manages the interactive workflow. It uses the Question Agent to get initial questions, then for each initial question, it uses the Answer Agent to get an answer. It then uses an LLM to check if the answer is satisfactory based on the question. If not, it prompts the LLM to generate a follow-up question and repeats the answer/check cycle. It interacts with the user for continuation prompts.

All agents utilize the `gpt-o3-mini` LLM via `LLMInterface` and operate within its context window limitations.
The primary goal is an interactive system where AI-generated questions probe a document, answers are retrieved strictly from that document, and an AI orchestrator manages follow-ups and user interaction.

**2. Goals**

*   **Automate Q&A:** Automatically generate relevant questions from a source document.
*   **Contextual Answering:** Provide answers based *strictly* on the content of a separate target document.
*   **Interactive Refinement:** Implement an interactive loop involving satisfaction checks and follow-up questions to improve answer quality when initial answers are insufficient.
*   **User Control:** Allow the user to observe the process and step through results.
*   **Accessibility:** Provide both a CLI for developers/power users and an easy-to-use Web UI for broader access.
*   **Modularity:** Design agents (Question, Answer, Orchestrator) as distinct components.

**3. Non-Goals**

*   **Handling Documents Exceeding Context Limits:** The system relies on inputs fitting within the LLM context window.
*   **Sophisticated State Management:** Initial version may have limited memory across follow-up questions due to context constraints.
*   **Complex Satisfaction Criteria:** Satisfaction checks will rely on LLM judgment based on a specific prompt, not complex metrics.
*   **User Input During Follow-up Loop:** The user is only prompted *after* the Orchestrator deems an answer satisfactory for an initial question.
*   **Fact-Checking, General Knowledge Answers, etc.:** Same non-goals apply as for the individual agents.

**4. User Stories / Use Cases**

*   **As an Analyst:**
    *   I want to provide a document (e.g., summary) to the Question Agent and a full report to the Answer Agent.
    *   I want the Orchestrator Agent to automatically take the first question, get an answer, and ask follow-up questions until it deems the answer satisfactory, showing me the conversation.
    *   After a satisfactory answer is reached for one initial question, I want the system to ask me if I want to continue with the next initial question.

**5. Functional Requirements**

*   **FR-A1..A4 (Answer Agent):** As previously defined (ingest report, take query, generate answer from context, output answer).
*   **FR-Q1..Q3 (Question Agent):** As previously defined (ingest doc, generate initial questions, output questions).
*   **FR-O1: Orchestrator - Initialization:** Must initialize Answer and Question Agents.
*   **FR-O2: Orchestrator - Workflow Management:** Must orchestrate the main loop (get initial questions, loop through them) and the inner loop (ask, check satisfaction, generate follow-up).
*   **FR-O3: Orchestrator - Satisfaction Check:** Must construct a prompt containing the question and answer, call LLM, and parse response to determine if the answer is satisfactory.
*   **FR-O4: Orchestrator - Follow-up Generation:** If an answer is unsatisfactory, must construct a prompt to generate a relevant follow-up question based on the original question and the unsatisfactory answer, call LLM, and parse the response.
*   **FR-O5: Orchestrator - Loop Control:** Must include a mechanism to limit the number of follow-up attempts per initial question.
*   **FR-O6: Orchestrator - User Interaction:** Must prompt the user to continue/stop after each initial question's cycle completes.
*   **FR-C1: Context Limit Handling:** All LLM calls (Answer, Question, Orchestrator checks) must respect context limits.

**6. Non-Functional Requirements**

*   **NFR1 (Context Limitation):** The initial version will load entire documents into context. Performance and functionality are limited by the LLM's context window size (e.g., `gpt-o3-mini`). This limitation must be clearly documented.
*   **NFR2 (Modularity):** Core logic for each agent (Question, Answer, Orchestrator) should reside in separate modules/classes.
*   **NFR3 (Configuration):** LLM access details (e.g., model name, API keys if applicable) should be configurable (e.g., via `config.json` or environment variables used by `LLMInterface`).
*   **NFR4 (Readability):** Code should be well-commented and follow standard Python style guidelines (e.g., PEP 8).
*   **NFR5 (Testability):** Core agent and orchestrator logic should be unit-testable, ideally using mocking for LLM interactions.
*   **NFR6 (Usability - CLI):** The CLI should provide clear usage instructions and error messages.
*   **NFR7 (Usability - Web UI):** The Streamlit UI should be intuitive, providing clear instructions, status updates (e.g., spinners), and error feedback.
*   **NFR8 (Extensibility):** The design should allow for future replacement of the direct context approach with RAG (Retrieval-Augmented Generation) without rewriting the entire agent interaction logic.

**7. Design Considerations/Constraints**

*   **Core Technology:** `gpt-o3-mini` via `LLMInterface` for all three agents.
*   **No RAG.**
*   **Modularity:** Clear separation between Orchestrator, Question Agent, Answer Agent logic.
*   **Prompt Engineering (Orchestrator):** Critical prompts needed for:
    *   Satisfaction Check (Input: Q, A; Output: Satisfied/Unsatisfied reason).
    *   Follow-up Question Generation (Input: Original Q, Unsatisfactory A; Output: New follow-up Q).
*   **State Management (Orchestrator):** Needs to track current initial question, current follow-up question, retry counts, etc.
*   **Context Window Management:** Even more critical now with Orchestrator LLM calls potentially needing Q+A context.
*   **UI Considerations:**
    *   **Web UI Style:** Messaging-style chat interface with left-aligned questions/orchestrator messages and right-aligned answers
    *   **Auto-scrolling:** Reliable auto-scrolling mechanism for the chat container to ensure new messages are visible
    *   **Responsive Design:** Chat container scales with viewport height for better user experience across devices

**8. Evaluation Metrics (for the Project)**

*   **Functionality:** Successful execution of the orchestrated interactive loop.
*   **Satisfaction Check Accuracy:** Human judgment on whether the Orchestrator's satisfaction decision was reasonable.
*   **Follow-up Question Quality:** Human judgment on relevance and usefulness of follow-ups.
*   **Answer Faithfulness & Relevance:** Continued evaluation of Answer Agent output.
*   **Initial Question Quality:** Continued evaluation of Question Agent output.
*   **Loop Termination:** Verify max retries and user stop commands work.

**9. Future Considerations**

*   **Implementing RAG:** Remains top priority.
*   **More Sophisticated Orchestrator Logic:** Improve satisfaction checks, follow-up strategies, context management across turns.
*   **User Feedback Integration:** Allow user to override Orchestrator's satisfaction judgment.
*   **UI/API:** Create better interfaces.

**10. Open Questions**

*   What are the detailed prompt structures for the Orchestrator's satisfaction check and follow-up generation?
*   How to parse the satisfaction check response reliably (e.g., specific keywords, JSON format)?
*   How to parse the follow-up question response reliably?
*   What is a reasonable maximum number of follow-up attempts?
*   How much context (original Q, previous A/follow-ups) can realistically be passed to the Orchestrator's LLM calls within limits?
*   How will the CLI manage the setup (paths for Q-doc and A-doc)?

--- 