# Agent Interaction Flow (CLI Orchestrate Command)

This diagram illustrates the interaction flow between the CLI, Orchestrator, Question Agent, and Answer Agent during the `orchestrate` command execution. It focuses on the key function calls and data flow based on the implementation.

```mermaid
sequenceDiagram
    participant CLI (main.py)
    participant O as Orchestrator
    participant QA as QuestionAgent
    participant AA as AnswerAgent
    participant LLM as LLMInterface (Implicit)

    CLI->>O: run_interaction(q_doc_path, a_doc_path)
    activate O

    O->>O: load_answer_doc(a_doc_path)
    Note right of O: Reads report file into self.answer_doc_content

    O->>QA: generate_questions(q_doc_path, num_initial_q)
    activate QA
    Note over QA,LLM: Uses LLMInterface.generate_response to get raw questions
    QA-->>O: initial_questions_list
    deactivate QA

    loop For each initial_question in initial_questions_list
        O->>O: current_question = initial_question
        O->>O: follow_up_count = 0

        loop While follow_up_count < max_follow_ups
            O->>AA: ask_question(current_question, self.answer_doc_content)
            activate AA
            Note over AA,LLM: Uses LLMInterface.generate_response based on report content
            AA-->>O: answer
            deactivate AA

            O->>O: check_satisfaction(current_question, answer)
            Note right of O: Uses LLMInterface.generate_response to assess
            O->>O: (satisfied, reason)

            alt Satisfied is True
                O->>O: Break inner loop
            else Not Satisfied
                O->>O: generate_follow_up(current_question, answer)
                Note right of O: Uses LLMInterface.generate_response to get follow-up
                O->>O: follow_up_question
                O->>O: current_question = follow_up_question
                O->>O: follow_up_count += 1
            end
        end
        Note right of O: Prints interaction summary (initial_q, answers, followups)
    end

    deactivate O
    CLI->>CLI: Process finished

```

**Explanation of the Flow:**

1.  **Initialization:** The CLI calls the Orchestrator's `run_interaction` method with the paths to the question document and the answer document (report file).
2.  **Load Report:** The Orchestrator first loads the content of the answer document using its `load_answer_doc` method.
3.  **Generate Initial Questions:** It then calls the `QuestionAgent.generate_questions` method, providing the path to the question document. The Question Agent uses the LLM Interface internally to generate a list of initial questions based on this document.
4.  **Outer Loop (Initial Questions):** The Orchestrator iterates through each `initial_question` received from the Question Agent.
5.  **Inner Loop (Interaction Cycle):** For each initial question, an inner loop begins:
    *   **Ask:** The Orchestrator calls the `AnswerAgent.ask_question`, providing the current question and the pre-loaded report content. The Answer Agent uses the LLM Interface internally to formulate an answer based *only* on the provided report content.
    *   **Check:** The Orchestrator receives the `answer` and calls its own `check_satisfaction` method. This method uses the LLM Interface to assess if the answer adequately addresses the question. It returns a `satisfied` status (True/False) and potentially a `reason`.
    *   **Follow-up (If Needed):**
        *   If `satisfied` is True, the inner loop breaks for this initial question.
        *   If `satisfied` is False and the maximum number of follow-ups hasn't been reached, the Orchestrator calls its `generate_follow_up` method. This uses the LLM Interface to generate a follow-up question based on the original question and the unsatisfactory answer. The `current_question` is updated to this new follow-up question, the follow-up counter increments, and the inner loop continues (asking the Answer Agent the follow-up question).
        *   If the maximum follow-ups are reached, the inner loop breaks even if the last answer wasn't satisfactory.
6.  **Summary & Next Question:** After the inner loop finishes for an initial question (either satisfied or max follow-ups reached), the Orchestrator prints a summary of that interaction thread and proceeds to the next initial question in the outer loop.
7.  **Completion:** Once all initial questions have been processed, the `run_interaction` method finishes, and control returns to the CLI. 