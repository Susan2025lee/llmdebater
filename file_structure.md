# Proposed File Structure: Question/Answer Orchestration System

This structure provides a suggested organization for the project files, accommodating the three-agent system and both CLI and Web interfaces.

```
qa_agent_system/
├── .env                    # (Optional) For storing API keys if not in config.json
├── .gitignore
├── config.json             # Existing config for models and potentially API keys
├── Dockerfile              # (Optional) For containerizing API/service
├── README.md               # Updated project overview, setup, usage (CLI & Web UI)
├── implementation_plan.md  # Updated high-level plan (includes UI)
├── prd.md                  # Updated PRD (includes UI)
├── task_list.md            # Updated detailed task breakdown (includes UI)
├── tech_stack.md           # Updated tech stack (includes Streamlit)
├── file_structure.md       # This file
├── requirements.txt        # Includes streamlit
├── main.py                 # CLI entry point (Typer commands)
├── streamlit_app.py        # Web UI entry point (Streamlit app with enhanced chat interface)
├── auto_scroll.py          # Auto-scroll functionality for Streamlit chat container
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── llm_interface.py    # Abstraction for LLM access (EXISTING)
│   │   ├── answer_agent.py     # Logic for answering questions based on report context (EXISTING)
│   │   ├── question_agent.py   # Logic for generating questions based on input document (EXISTING)
│   │   ├── orchestrator.py     # Logic for managing the workflow (used by CLI & UI) (EXISTING)
│   │   ├── models.py           # Shared data models (Pydantic/dataclasses)
│   │   └── prompts.py          # (Optional) Centralized prompt templates
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── file_handler.py     # File reading utilities (EXISTING)
│   │   └── token_utils.py      # Token counting utility (EXISTING)
├── tests/
│   ├── __init__.py
│   ├── test_llm_interface.py # Tests for LLMInterface (EXISTING)
│   ├── test_answer_agent.py  # Unit tests for AnswerAgent (EXISTING)
│   ├── test_question_agent.py# Unit tests for QuestionAgent (EXISTING)
│   ├── test_orchestrator.py  # Unit tests for Orchestrator (EXISTING)
│   ├── test_file_handler.py  # Tests for file handling (EXISTING)
│   └── test_token_utils.py   # Tests for token counting (EXISTING)
├── data/
│   ├── reports/              # Directory for storing sample reports (for Answer Agent)
│   │   ├── report_A.md
│   │   └── ...
│   └── summaries/            # Directory for storing sample summaries/docs (for Question Agent)
│       ├── summary_A.md
│       └── ...
├── scripts/
│   └── (Optional)              # Utility or evaluation scripts
└── .github/
    └── workflows/              # (Optional) CI/CD
        └── ci.yml
```

**Key Changes:**

*   **`streamlit_app.py`**: Added a new file in the root for the Streamlit Web UI.
*   Documentation files updated to reflect the inclusion of the Web UI.
*   `Orchestrator` now designed to return results for consumption by different interfaces (CLI, UI).
*   **`auto_scroll.py`**: Added a new file in the root for auto-scroll functionality.

```
arqj/
├── .env                    # For storing API keys and environment variables (add to .gitignore!)
├── .gitignore              # Git ignore file
├── Dockerfile              # (Optional) For containerizing the application
├── README.md               # Project overview, setup, usage instructions
├── implementation_plan.md  # High-level implementation phases
├── prd.md                  # Product Requirements Document
├── task_list.md            # Detailed task breakdown
├── tech_stack.md           # Technology stack decisions
├── file_structure.md       # This file
├── requirements.txt        # Or pyproject.toml for dependency management
├── test_llm_interface.py   # Test script for validating LLMInterface functionality
├── src/
│   ├── __init__.py
│   ├── main.py               # Entry point for API (FastAPI/Flask) or CLI (Typer/Click)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── llm_interface.py    # Abstraction for LLM access with proxy support (COMPLETED)
│   │   ├── evaluator.py        # Uses LLMInterface to evaluate reports
│   │   ├── models.py           # Data models (e.g., Pydantic for API, dataclasses)
│   │   └── prompts.py          # Stores and manages prompt templates used by LLMInterface
│   ├── utils/
│   │   ├── __init__.py
│   │   └── file_handler.py     # Functions for reading/handling input files
│   └── config.py             # Loads configuration (e.g., API keys from .env)
├── tests/
│   ├── __init__.py
│   ├── test_evaluator.py     # Unit tests for the evaluation logic using LLMInterface
│   ├── test_file_handler.py  # Unit tests for file handling
│   └── test_api.py           # (If API) Integration tests for the API endpoints
│   └── test_cli.py           # (If CLI) Integration tests for the CLI commands
├── data/
│   └── evaluation_set/       # Directory for storing sample reports for evaluation
│       ├── report_high_1.md
│       ├── report_medium_1.md
│       └── report_low_1.md
│       └── ...
│   └── human_evaluations.csv # (Example) File storing human scores for the evaluation set
├── scripts/
│   └── run_evaluation.py     # Script to run ARQJ on the evaluation set and compare results
└── .github/                  # (Optional) For CI/CD workflows
    └── workflows/
        └── ci.yml
```

**Notes:**

*   The `src/` directory contains the main application code, organized into submodules (`core`, `utils`).
*   `llm_interface.py` provides the standardized way to communicate with the LLM behind a firewall, using the existing ModelManager and proxy configuration. This is already implemented.
*   `evaluator.py` will use the LLMInterface for report quality assessment rather than directly communicating with the LLM.
*   `main.py` acts as the entry point, delegating tasks to modules within `src/`.
*   `tests/` mirrors the `src/` structure for clear test organization.
*   `data/` holds sample reports and potentially human evaluation results used for testing and validation.
*   `scripts/` can contain utility scripts, like the one for running batch evaluations.
*   Configuration (like API keys) is kept separate (`.env`, `config.py`) and out of version control (`.gitignore`). We use the existing `config.json` and proxy settings from `interactive_chat.py`.
*   **`streamlit_app.py`**: Added a new file in the root for the Streamlit Web UI.
*   **`auto_scroll.py`**: Added a new file in the root for auto-scroll functionality.
*   **`streamlit_app.py`** implements a user-friendly web interface with a messaging-style chat layout and auto-scrolling functionality.
*   **`auto_scroll.py`** contains the JavaScript-based auto-scrolling solution for the Streamlit chat interface.
*   Configuration (like API keys) is kept separate (`.env`, `config.py`) and out of version control (`.gitignore`). We use the existing `config.json` and proxy settings from `interactive_chat.py`. 