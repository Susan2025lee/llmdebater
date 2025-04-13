# Multi-Agent Q&A Debate System

This project implements a multi-agent system designed to analyze documents and generate insightful question-answer pairs through a simulated debate process. It leverages Large Language Models (LLMs) to drive question generation, answer formulation based on provided source documents, and synthesis of final answers.

The primary interface is a Streamlit web application (`streamlit_app_v2.py`) that visualizes the debate process.

**Core Functionality:**

1.  **Question Agent:** Generates initial questions based on a provided "question document" (e.g., a summary or topic document).
2.  **Answer Agents (Multiple):** Each agent is provided with a different source document (e.g., different reports, articles, or perspectives on a topic). When asked a question by the Orchestrator, each Answer Agent formulates an answer based *only* on its assigned document.
3.  **Orchestrator Agent (V2):** Manages the debate workflow:
    *   Gets initial questions from the Question Agent.
    *   Poses each question to all Answer Agents simultaneously.
    *   Collects the answers from each Answer Agent.
    *   (Implicitly, via the generator structure) Coordinates the flow.
4.  **Synthesizer (within Orchestrator):** Although not explicitly shown as a separate agent in the final UI, the Orchestrator uses an LLM call to synthesize a final, consolidated answer based on the individual answers provided by the Answer Agents for each question.
5.  **Web Interface (V2):** Provides a user-friendly interface to:
    *   Upload the question document.
    *   Upload multiple answer documents (one per Answer Agent).
    *   Configure parameters (number of questions, output filename).
    *   Start the debate workflow.
    *   View the interaction log (system messages, questions, agent answers, synthesized results) in a chat-style format.
    *   Save the final Q&A pairs to a specified markdown file.

**Warning:** The system loads the *entire* content of each document into the LLM prompts. Ensure the documents are reasonably sized to fit within the LLM's context window (e.g., `gpt-o3-mini` currently used, check `MODEL_NAME` in `src/core/answer_agent.py`).

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-directory>
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv env
    source env/bin/activate  # On Windows use `env\Scripts\activate`
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure LLM Access:** Ensure the `LLMInterface` (`src/core/llm_interface.py`) is correctly configured, potentially via `src/config.json` or environment variables, to access the required LLM (e.g., `gpt-o3-mini`).

## Usage

The primary way to use the system is through the V2 Streamlit Web Interface.

### Web Interface (V2 - Multi-Agent Debate)

This interface runs the multi-agent debate workflow.

1.  **Run the V2 Streamlit app:**
    ```bash
    streamlit run streamlit_app_v2.py
    ```
    *(Ensure your virtual environment is activated)*
2.  **Open your web browser** to the local URL provided (usually http://localhost:8501).
3.  **Upload Document for Question Generation:** Provide the document that the Question Agent will use to create initial questions.
4.  **Upload Answer Documents for Debate:** Upload *one or more* source documents. Each document will be assigned to a separate Answer Agent.
5.  **Configure Parameters:**
    *   Set the desired *Number of Initial Questions to Generate*.
    *   Specify the *Output Filename (.md)* where the final Q&A pairs will be saved (e.g., `debate_results.md`). This file will be created in the `data/output/` directory.
6.  **Start Workflow:** Click the "Start V2 Debate" button.
7.  **Monitor:** Observe the chat interface as the system initializes, generates questions, gathers answers from each agent, and synthesizes the final results.
8.  **Results:** Once complete, the final Q&A pairs will be displayed in the chat and saved to the specified output markdown file in `data/output/`.

### Command-Line Interface (CLI)

While the Streamlit app is the primary UI, `main.py` provides CLI commands for running workflows.

**V2 Multi-Agent Debate (CLI):**

```bash
# Example:
env/bin/python main.py orchestrate_v2 \
    data/input/question_doc.md \
    data/input/answer_doc1.md data/input/answer_doc2.md \
    data/output/v2_results.md \
    --num-initial-questions 3
```

**V3 Multi-Round Debate (CLI - Experimental):**

This runs an experimental workflow where Answer Agents participate in multiple rounds before final synthesis.

```bash
# Example:
env/bin/python main.py orchestrate_v3 \
    data/input/question_doc.md \
    data/input/answer_doc1.md data/input/answer_doc2.md data/input/answer_doc3.md \
    data/output/v3_results.md \
    --num-initial-questions 2 \
    --max-debate-rounds 2 # Specify number of debate rounds (after initial answers)
```
*   `--max-debate-rounds`: Controls how many rounds of back-and-forth occur between the agents (default is 2). A value of 0 means only initial answers are gathered before synthesis.

*(Note: The V1 Streamlit app (`streamlit_app.py`) and the CLI command `orchestrate` related to the satisfaction/follow-up loop represent an earlier version and are considered legacy.)*

## Project Structure

```
llmdebater/
├── data/
│   ├── input/             # Sample input documents (optional)
│   └── output/            # Directory for saved debate results (.md files)
├── env/                   # Python virtual environment (created by user)
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── answer_agent.py    # Defines the ReportQAAgent (Base V2)
│   │   ├── answer_agent_v3.py # Defines AnswerAgentV3 (Multi-round debate)
│   │   ├── llm_interface.py # Handles LLM API communication
│   │   ├── orchestrator.py    # Defines V1 Orchestrator (LEGACY)
│   │   ├── orchestrator_v2.py # Defines V2 Orchestrator (Single-round debate)
│   │   ├── orchestrator_v3.py # Defines V3 Orchestrator (Multi-round debate)
│   │   ├── question_agent.py  # Defines QuestionAgent
│   │   └── prompts.py         # Contains LLM prompt templates
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── file_handler.py  # Utility for reading files
│   │   └── token_utils.py   # Utility for estimating token counts
│   └── __init__.py
│   └── config.json        # Configuration (e.g., API keys - add to .gitignore!)
├── tests/
│   ├── __init__.py
│   ├── conftest.py        # Pytest configuration and fixtures
│   ├── test_answer_agent.py
│   ├── test_answer_agent_v3.py # Tests for V3 Answer Agent
│   ├── test_file_handler.py
│   ├── test_llm_interface.py
│   ├── test_orchestrator.py     # Tests for LEGACY V1 orchestrator
│   ├── test_orchestrator_v2.py  # Tests for V2 orchestrator
│   ├── test_orchestrator_v3.py  # Tests for V3 orchestrator
│   ├── test_question_agent.py
│   ├── test_streamlit_app_v2.py # Tests for V2 Streamlit app logic
│   └── test_token_utils.py
├── .gitignore
├── agent_interaction_v3.md # V3 Interaction Flow Diagram
├── implementation_plan.md
├── main.py                # CLI entry point (includes V1/V2/V3 orchestrators)
├── prd.md                 # Product Requirements Document
├── README.md              # This file
├── requirements.txt       # Python dependencies
├── streamlit_app.py       # V1 Streamlit UI (LEGACY)
└── streamlit_app_v2.py    # V2 Streamlit UI (PRIMARY UI)
```

## Key Components (`src/core/`)

*   **`llm_interface.py`:** Centralized class for all interactions with the configured LLM.
*   **`question_agent.py`:** Uses the LLM to generate questions based on an input document.
*   **`answer_agent.py` / `answer_agent_v3.py`:** Use the LLM to answer questions based *only* on the content of their assigned document context. V3 adds multi-round debate participation.
*   **`orchestrator_v2.py` / `orchestrator_v3.py`:** Implement the debate workflows. Coordinate agents, structure debate turns, use the LLM for synthesizing final answers, and yield results. V3 manages multiple rounds.
*   **`prompts.py`:** Stores the prompt templates used by the agents and orchestrators.