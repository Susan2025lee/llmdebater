# Tests for the QuestionAgent class

import pytest
from unittest.mock import patch, MagicMock
import os

from src.core.question_agent import QuestionAgent, ContextLengthError, MAX_INPUT_TOKENS, QUESTION_PROMPT_TEMPLATE
from src.core.llm_interface import LLMInterface # To mock

# Placeholder for imports
# from src.core.question_agent import QuestionAgent, ContextLengthError

# Placeholder for tests
def test_placeholder():
    assert True 

# --- Fixtures --- #

@pytest.fixture
def mock_dependencies_q(): # Renamed fixture for clarity
    """Mocks dependencies for QuestionAgent."""
    # Only need to mock LLMInterface for QuestionAgent
    with (
        patch('src.core.question_agent.LLMInterface') as MockLLMInterface,
        patch('src.core.question_agent.estimate_token_count') as mock_estimate,
        patch('src.core.question_agent.read_text_file') as mock_read # Mock read for file-based method
    ): # Added closing parenthesis
        
        mock_llm_instance = MockLLMInterface.return_value
        mock_llm_instance.generate_chat_response = MagicMock()
        
        yield mock_llm_instance, mock_estimate, mock_read

@pytest.fixture
def q_agent(mock_dependencies_q): # Depends on the new fixture
    """Provides an instance of QuestionAgent with mocked dependencies."""
    return QuestionAgent()

# --- Test Cases --- #

DOC_CONTENT = "Topic A is important. Topic B relates to C. Data point D showed a 5% increase."

# Test successful generation and parsing
@pytest.mark.parametrize("raw_llm_output, expected_questions", [
    # Standard numbered list
    ("1. What is Topic A?\n2. How does B relate to C?\n3. What was the increase in D?", 
     ["What is Topic A?", "How does B relate to C?", "What was the increase in D?"]),
    # Numbered list with parentheses
    ("1) Detail Topic A.\n2) Explain B and C.\n3) Elaborate on D.", 
     ["Detail Topic A.", "Explain B and C.", "Elaborate on D."]),
    # List with hyphens
    ("- Question 1\n- Question 2", 
     ["Question 1", "Question 2"]),
    # List with asterisks and extra whitespace
    ("*  Item 1?\n * Item 2? ", 
     ["Item 1?", "Item 2?"]),
    # Output with preamble/postamble noise
    ("Here are the questions:\n1. Question A\n2. Question B\nThat is all.", 
     ["Question A", "Question B"]),
    # Empty output
    ("", []),
    # Output that cannot be parsed as list (fallback)
    ("Just a single sentence response.", ["Just a single sentence response."])
])
def test_generate_questions_success(q_agent, mock_dependencies_q, raw_llm_output, expected_questions):
    """Tests successful question generation and parsing of various formats."""
    mock_llm, mock_estimate, _ = mock_dependencies_q
    num_q = len(expected_questions) if expected_questions else 3 # Use expected length or default
    estimated_tokens = 500

    # Configure mocks
    mock_estimate.return_value = estimated_tokens
    mock_llm.generate_chat_response.return_value = raw_llm_output

    # Call using content
    questions = q_agent.generate_questions_from_content(DOC_CONTENT, num_questions=num_q)

    assert questions == expected_questions
    
    # Check prompt formatting and token estimation call
    expected_prompt = QUESTION_PROMPT_TEMPLATE.format(
        num_questions=num_q,
        document_content=DOC_CONTENT
    )
    mock_estimate.assert_called_once_with(expected_prompt, model_name=MODEL_NAME)
    
    # Check LLM call
    expected_messages = [{"role": "user", "content": expected_prompt}]
    mock_llm.generate_chat_response.assert_called_once_with(expected_messages)

def test_generate_questions_empty_content(q_agent):
    """Tests that an error is raised for empty document content."""
    with pytest.raises(ValueError, match="Document content cannot be empty."):
        q_agent.generate_questions_from_content("")

def test_generate_questions_token_estimation_error(q_agent, mock_dependencies_q):
    """Tests error handling when token estimation fails."""
    mock_llm, mock_estimate, _ = mock_dependencies_q
    mock_estimate.return_value = -1 # Simulate error

    with pytest.raises(ValueError, match="Token estimation failed."):
        q_agent.generate_questions_from_content(DOC_CONTENT)

def test_generate_questions_context_limit_exceeded(q_agent, mock_dependencies_q):
    """Tests raising ContextLengthError for oversized input."""
    mock_llm, mock_estimate, _ = mock_dependencies_q
    estimated_tokens_over = MAX_INPUT_TOKENS + 1
    mock_estimate.return_value = estimated_tokens_over

    with pytest.raises(ContextLengthError) as excinfo:
        q_agent.generate_questions_from_content(DOC_CONTENT)
    
    assert str(estimated_tokens_over) in str(excinfo.value)
    assert str(MAX_INPUT_TOKENS) in str(excinfo.value)
    assert "question generation" in str(excinfo.value)

def test_generate_questions_llm_error(q_agent, mock_dependencies_q):
    """Tests error handling when the LLM call fails."""
    mock_llm, mock_estimate, _ = mock_dependencies_q
    mock_estimate.return_value = 500 # Valid token count
    mock_llm.generate_chat_response.side_effect = Exception("LLM Service Unavailable")

    with pytest.raises(RuntimeError, match="Error generating questions via LLM: LLM Service Unavailable"):
        q_agent.generate_questions_from_content(DOC_CONTENT)

def test_generate_questions_llm_invalid_response(q_agent, mock_dependencies_q):
    """Tests handling when LLM returns non-string or None."""
    mock_llm, mock_estimate, _ = mock_dependencies_q
    mock_estimate.return_value = 500
    mock_llm.generate_chat_response.return_value = None # Invalid response

    with pytest.raises(ValueError, match="Received invalid response from the language model."):
         q_agent.generate_questions_from_content(DOC_CONTENT)

# --- Tests for file-based method --- #

FAKE_PATH = "fake/doc.txt"

def test_generate_questions_file_success(q_agent, mock_dependencies_q):
    """Tests the file-based method successfully calls the content method."""
    mock_llm, mock_estimate, mock_read = mock_dependencies_q
    raw_llm_output = "1. Q1? \n 2. Q2?"
    expected_questions = ["Q1?", "Q2?"]
    num_q = 2
    
    mock_read.return_value = DOC_CONTENT
    mock_estimate.return_value = 500
    mock_llm.generate_chat_response.return_value = raw_llm_output
    
    questions = q_agent.generate_questions(FAKE_PATH, num_questions=num_q)
    
    assert questions == expected_questions
    mock_read.assert_called_once_with(FAKE_PATH)
    # Verify estimate and LLM call were made (via the content method)
    expected_prompt = QUESTION_PROMPT_TEMPLATE.format(num_questions=num_q, document_content=DOC_CONTENT)
    mock_estimate.assert_called_once_with(expected_prompt, model_name=MODEL_NAME)
    mock_llm.generate_chat_response.assert_called_once()

def test_generate_questions_file_not_found(q_agent, mock_dependencies_q):
    """Tests that FileNotFoundError is propagated."""
    _, _, mock_read = mock_dependencies_q
    mock_read.side_effect = FileNotFoundError("Not found")
    
    with pytest.raises(FileNotFoundError):
        q_agent.generate_questions(FAKE_PATH)

def test_generate_questions_file_read_error(q_agent, mock_dependencies_q):
    """Tests that IOError is propagated for read errors."""
    _, _, mock_read = mock_dependencies_q
    mock_read.side_effect = IOError("Read fail")
    
    with pytest.raises(IOError):
        q_agent.generate_questions(FAKE_PATH)

def test_generate_questions_file_empty(q_agent, mock_dependencies_q):
    """Tests that ValueError is raised for empty files."""
    _, _, mock_read = mock_dependencies_q
    mock_read.return_value = "" # Empty content
    
    with pytest.raises(ValueError, match="Document file is empty"):
        q_agent.generate_questions(FAKE_PATH) 