# Tech Stack: Question/Answer Orchestration System (Direct Context)

This document outlines the proposed technologies for building the simplified Direct Context version of the Question/Answer Orchestration System.

*   **Programming Language:**
    *   **Python (3.9+):** Chosen for its extensive ecosystem of libraries for AI/ML, data processing, web development, and scripting.

*   **Core LLM Interaction:**
    *   **LLM Provider:** `gpt-o3-mini` model accessed via `LLMInterface` for all agents (Question, Answer, Orchestrator).
    *   **LLM Client Library:** Handled internally by `LLMInterface`.

*   **Report Parsing/Text Extraction (Future Consideration):**
    *   Libraries like `pypdf2`, `PyMuPDF`, `python-docx`, `unstructured` for extracting text from various file formats (.pdf, .docx) if support beyond .txt/.md is added.

*   **Interfaces:**
    *   **CLI:**
        *   **CLI Framework:** Typer.
    *   **Web UI:**
        *   **Web Framework:** Streamlit.

*   **Dependency Management:**
    *   **pip** with `requirements.txt`.

*   **Testing:**
    *   **Testing Framework:** `pytest`.
    *   **Mocking Library:** `unittest.mock`.

*   **Containerization (Optional):**
    *   **Docker**.

*   **CI/CD (Optional):**
    *   **Platform:** GitHub Actions, GitLab CI, etc.

*   **Development Environment:**
    *   **Version Control:** Git.
    *   **IDE/Editor:** VS Code, PyCharm, etc.
    *   **Virtual Environment:** `venv`. 