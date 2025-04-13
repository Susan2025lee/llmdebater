# File Structure: Multi-Agent Q&A Debate System

This structure reflects the final organization for the project, focusing on the V2 multi-agent debate system and Streamlit UI.

```
llmdebater/                 # Project Root
├── .gitignore              # Files to ignore in Git
├── implementation_plan.md  # Final implementation plan summary
├── main.py                 # CLI entry point (contains V1/V2 orchestrator commands - secondary usage)
├── prd.md                  # Final Product Requirements Document (focused on V2)
├── README.md               # Project overview, setup, V2 UI usage instructions
├── requirements.txt        # Python dependencies (including streamlit, typer)
├── streamlit_app.py        # V1 Streamlit UI (satisfaction/follow-up loop - LEGACY)
├── streamlit_app_v2.py     # V2 Streamlit UI (multi-agent debate - PRIMARY UI)
├── task_list.md            # Final task list showing completed V2 work
├── file_structure.md       # This file
├── tech_stack.md           # (If exists) Description of technologies used
├── data/
│   ├── input/              # Sample input documents (optional)
│   └── output/             # Directory for saved debate results (.md files)
├── env/                    # Python virtual environment (created by user)
├── src/
│   ├── __init__.py
│   ├── core/               # Core agent and orchestration logic
│   │   ├── __init__.py
│   │   ├── answer_agent.py    # Defines ReportQAAgent (base for V3)
│   │   ├── answer_agent_v3.py # Defines AnswerAgentV3 (or modify answer_agent.py)
│   │   ├── llm_interface.py # Handles all LLM API communication
│   │   ├── orchestrator.py    # Defines V1 Orchestrator (LEGACY)
│   │   ├── orchestrator_v2.py # Defines V2 Orchestrator (multi-agent debate)
│   │   ├── orchestrator_v3.py # Defines V3 Orchestrator (multi-round debate)
│   │   ├── question_agent.py  # Defines QuestionAgent (used by V2 & V3)
│   │   └── prompts.py         # Contains LLM prompt templates (needs V3 prompts)
│   ├── utils/              # Utility functions
│   │   ├── __init__.py
│   │   ├── file_handler.py  # Utility for reading files
│   │   └── token_utils.py   # Utility for estimating token counts
│   └── config.json         # Configuration (e.g., API keys - add to .gitignore!)
└── tests/                  # Unit and integration tests
    ├── __init__.py
    ├── conftest.py         # Pytest configuration and shared fixtures
    ├── test_answer_agent.py
    ├── test_answer_agent_v3.py # Tests for AnswerAgentV3
    ├── test_file_handler.py
    ├── test_llm_interface.py
    ├── test_orchestrator.py     # Tests for LEGACY V1 orchestrator
    ├── test_orchestrator_v2.py  # Tests for V2 orchestrator
    ├── test_orchestrator_v3.py  # Tests for V3 orchestrator
    ├── test_question_agent.py
    ├── test_streamlit_app_v2.py # Tests for V2 Streamlit app logic
    └── test_token_utils.py
```

**Key Points:**

*   The primary user interface is `streamlit_app_v2.py`.
*   The core logic for the **V3** debate workflow resides in `src/core/orchestrator_v3.py` and `src/core/answer_agent_v3.py` (or modifications to `answer_agent.py`).
*   V1 and V2 components (`streamlit_app.py`, `orchestrator.py`, `orchestrator_v2.py`) are retained as legacy/alternative workflows.
*   Tests cover all core V2 and V3 components.
*   Output from the V2 workflow is saved to the `data/output/` directory.
