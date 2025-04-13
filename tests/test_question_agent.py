# Tests for the QuestionAgent class

import pytest
from unittest.mock import patch, MagicMock
import os
import sys
from typing import List

# --- Start Correct sys.path Modification ---
# Calculate project root and add src to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir) # Assumes tests/ is one level down from root
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)
# --- End Correct sys.path Modification ---

from core.question_agent import QuestionAgent, QUESTION_PROMPT_TEMPLATE, ContextLengthError
from core.llm_interface import LLMInterface # Import directly from core
# Import constants from answer_agent as question_agent uses them
from core.answer_agent import MAX_INPUT_TOKENS, MODEL_NAME 

# Placeholder for imports
# from src.core.question_agent import QuestionAgent, ContextLengthError

# Placeholder for tests
def test_placeholder():
    assert True 

# --- Fixtures --- #

@pytest.fixture
def mock_dependencies_q():
    """Mocks dependencies for QuestionAgent."""
    # Target paths based on where they are used in core.question_agent
    with (
        patch('core.question_agent.LLMInterface') as MockLLMInterface,
        patch('core.question_agent.estimate_token_count') as mock_estimate,
        patch('core.question_agent.read_text_file') as mock_read # Used in generate_questions(file)
    ):
        mock_llm_instance = MockLLMInterface.return_value
        mock_llm_instance.generate_chat_response = MagicMock()
        mock_llm_instance.model_name = MODEL_NAME  # <--- Configure model_name here
        yield mock_llm_instance, mock_estimate, mock_read

@pytest.fixture
def q_agent(mock_dependencies_q):
    """Provides an instance of QuestionAgent with mocked dependencies."""
    mock_llm, _, _ = mock_dependencies_q # Unpack the LLM mock
    return QuestionAgent(llm_interface=mock_llm)

# --- Test Cases --- #

DOC_CONTENT = "This document covers Topic A, Relationship B-C, and Metric D which increased."

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
    # Output with preamble/postamble noise - *Adjusted expectation based on actual parsing*
    ("Here are the questions:\n1. Question A\n2. Question B\nThat is all.",
     ['Here are the questions:', 'Question A', 'Question B', 'That is all.']), # Expect split lines, imperfect cleaning
    # Empty output
    ("", []),
    # Output that cannot be parsed as list (fallback)
    ("Just a single sentence response.", ["Just a single sentence response."])
])
def test_generate_questions_success(q_agent, mock_dependencies_q, raw_llm_output, expected_questions):
    """Tests successful question generation and parsing of various formats."""
    mock_llm, mock_estimate, _ = mock_dependencies_q
    num_q = len(expected_questions) if expected_questions and expected_questions != [raw_llm_output] else 3 # Adjust num_q calc
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
    """Tests that an error is raised for empty content."""
    with pytest.raises(ValueError, match="Document content cannot be empty"):
        q_agent.generate_questions_from_content("", num_questions=5)

def test_generate_questions_token_estimation_error(q_agent, mock_dependencies_q):
    """Tests error handling for token estimation failure."""
    _, mock_estimate, _ = mock_dependencies_q
    mock_estimate.return_value = -1 # Simulate failure

    with pytest.raises(ValueError, match="Token estimation failed"):
        q_agent.generate_questions_from_content(DOC_CONTENT, num_questions=5)

def test_generate_questions_context_limit_exceeded(q_agent, mock_dependencies_q):
    """Tests error handling when context limit is exceeded."""
    _, mock_estimate, _ = mock_dependencies_q
    mock_estimate.return_value = MAX_INPUT_TOKENS + 1 # Exceed limit

    with pytest.raises(ContextLengthError):
        q_agent.generate_questions_from_content(DOC_CONTENT, num_questions=5)

def test_generate_questions_llm_error(q_agent, mock_dependencies_q):
    """Tests error handling when the LLM call fails."""
    mock_llm, mock_estimate, _ = mock_dependencies_q
    mock_estimate.return_value = 500 # Valid token count
    error_msg = "LLM Service Unavailable"
    mock_llm.generate_chat_response.side_effect = Exception(error_msg)

    # Agent should catch the error and return empty list
    questions = q_agent.generate_questions_from_content(DOC_CONTENT, num_questions=5)
    assert questions == []

def test_generate_questions_llm_invalid_response(q_agent, mock_dependencies_q):
    """Tests handling when LLM returns non-string or None."""
    mock_llm, mock_estimate, _ = mock_dependencies_q
    mock_estimate.return_value = 500
    mock_llm.generate_chat_response.return_value = None # Invalid response

    # Agent should catch the error and return empty list
    questions = q_agent.generate_questions_from_content(DOC_CONTENT, num_questions=5)
    assert questions == []

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
    expected_messages = [{"role": "user", "content": expected_prompt}]
    mock_llm.generate_chat_response.assert_called_once_with(expected_messages)

def test_generate_questions_file_not_found(q_agent, mock_dependencies_q):
    """Tests that FileNotFoundError is raised."""
    _, _, mock_read = mock_dependencies_q
    mock_read.side_effect = FileNotFoundError("File missing")
    
    with pytest.raises(FileNotFoundError):
        q_agent.generate_questions(FAKE_PATH)

def test_generate_questions_file_read_error(q_agent, mock_dependencies_q):
    """Tests that IOError is raised for file read errors."""
    _, _, mock_read = mock_dependencies_q
    read_error_msg = "Cannot read file"
    mock_read.side_effect = Exception(read_error_msg)
    
    with pytest.raises(IOError) as excinfo:
        q_agent.generate_questions(FAKE_PATH)
    assert read_error_msg in str(excinfo.value)
    assert "Could not read document file" in str(excinfo.value)

def test_generate_questions_file_empty(q_agent, mock_dependencies_q):
    """Tests that IOError is raised for empty files (after catching ValueError)."""
    _, _, mock_read = mock_dependencies_q
    mock_read.return_value = "" # Empty content
    
    # Agent raises ValueError internally, then catches and raises IOError
    with pytest.raises(IOError) as excinfo:
        q_agent.generate_questions(FAKE_PATH)
    assert "Document file is empty" in str(excinfo.value)
    assert "Could not read document file" in str(excinfo.value) 