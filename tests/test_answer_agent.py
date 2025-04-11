import pytest
from unittest.mock import patch, MagicMock
import os

# Ensure imports work correctly based on project structure
# Adjust if necessary, e.g., if tests are run from the root directory
from core.answer_agent import ReportQAAgent, ContextLengthError, MAX_INPUT_TOKENS
from src.core.llm_interface import LLMInterface # Import to mock it

# --- Fixtures --- #

@pytest.fixture
def mock_dependencies():
    """Mocks all external dependencies for AnswerAgent."""
    with (
        patch('src.core.answer_agent.read_text_file') as mock_read,
        patch('src.core.answer_agent.estimate_token_count') as mock_estimate,
        patch('src.core.answer_agent.LLMInterface') as MockLLMInterface
    ):
        mock_llm_instance = MockLLMInterface.return_value
        mock_llm_instance.generate_chat_response = MagicMock()
        yield mock_read, mock_estimate, mock_llm_instance

@pytest.fixture
def agent(mock_dependencies): # Depends on the mock_dependencies fixture
    """Provides an instance of ReportQAAgent with mocked dependencies."""
    # No config needed as LLMInterface is mocked
    return ReportQAAgent(llm_config=None)

# --- Test Cases --- #

def test_ask_question_success(agent, mock_dependencies):
    """Tests the successful flow of asking a question."""
    mock_read, mock_estimate, mock_llm = mock_dependencies
    
    report_path = "test_report.txt"
    query = "What is the revenue?"
    report_content = "Revenue was $10M."
    expected_answer = "The report states revenue was $10M."
    estimated_tokens = 500 # Well within limits

    # Configure mocks
    mock_read.return_value = report_content
    mock_estimate.return_value = estimated_tokens
    mock_llm.generate_chat_response.return_value = expected_answer
    
    # Call the method
    answer = agent.ask_question(query, report_path)
    
    # Assertions
    assert answer == expected_answer
    mock_read.assert_called_once_with(report_path)
    # Check that estimate_token_count was called with the correctly formatted prompt
    expected_prompt = agent.PROMPT_TEMPLATE.format(report_content=report_content, user_query=query)
    mock_estimate.assert_called_once_with(expected_prompt, model_name=agent.MODEL_NAME)
    # Check that llm was called with the correct message structure
    expected_messages = [{"role": "user", "content": expected_prompt}]
    mock_llm.generate_chat_response.assert_called_once_with(expected_messages)

def test_ask_question_file_not_found(agent, mock_dependencies):
    """Tests handling when the report file is not found."""
    mock_read, _, _ = mock_dependencies
    report_path = "non_existent.txt"
    query = "Any question?"

    # Configure mock_read to raise FileNotFoundError
    mock_read.side_effect = FileNotFoundError(f"File not found: {report_path}")
    
    # Assert that FileNotFoundError is raised
    with pytest.raises(FileNotFoundError):
        agent.ask_question(query, report_path)
        
    mock_read.assert_called_once_with(report_path)

def test_ask_question_read_error(agent, mock_dependencies):
    """Tests handling for generic file reading errors."""
    mock_read, _, _ = mock_dependencies
    report_path = "error_file.txt"
    query = "Any question?"

    # Configure mock_read to raise a generic Exception
    mock_read.side_effect = IOError("Disk read error")

    # Call and assert the returned error message
    result = agent.ask_question(query, report_path)
    assert "Error: Could not read report file. Disk read error" in result
    mock_read.assert_called_once_with(report_path)

def test_ask_question_empty_file(agent, mock_dependencies):
    """Tests handling when the report file is empty."""
    mock_read, _, _ = mock_dependencies
    report_path = "empty_report.txt"
    query = "Any question?"

    # Configure mock_read to return empty string
    mock_read.return_value = ""

    # Call and assert the returned error message
    result = agent.ask_question(query, report_path)
    assert "Error: The report file is empty." in result
    mock_read.assert_called_once_with(report_path)

def test_ask_question_context_length_exceeded(agent, mock_dependencies):
    """Tests raising ContextLengthError when token estimate is too high."""
    mock_read, mock_estimate, _ = mock_dependencies
    report_path = "large_report.txt"
    query = "Summarize everything."
    report_content = "This is some report content."
    # Make estimate return a value just over the limit
    estimated_tokens = MAX_INPUT_TOKENS + 1 

    # Configure mocks
    mock_read.return_value = report_content
    mock_estimate.return_value = estimated_tokens
    
    # Assert that ContextLengthError is raised
    with pytest.raises(ContextLengthError) as excinfo:
        agent.ask_question(query, report_path)
    
    # Check the error message contains relevant info
    assert str(MAX_INPUT_TOKENS) in str(excinfo.value)
    assert str(estimated_tokens) in str(excinfo.value)
    mock_read.assert_called_once_with(report_path)
    expected_prompt = agent.PROMPT_TEMPLATE.format(report_content=report_content, user_query=query)
    mock_estimate.assert_called_once_with(expected_prompt, model_name=agent.MODEL_NAME)

def test_ask_question_token_estimation_error(agent, mock_dependencies):
    """Tests handling when token estimation itself fails."""
    mock_read, mock_estimate, _ = mock_dependencies
    report_path = "report.txt"
    query = "Any query?"
    report_content = "Some content."

    # Configure mocks
    mock_read.return_value = report_content
    mock_estimate.return_value = -1 # Simulate estimation error

    # Call and assert the returned error message
    result = agent.ask_question(query, report_path)
    assert "Error: Could not process the request due to token estimation failure." in result
    mock_read.assert_called_once_with(report_path)
    expected_prompt = agent.PROMPT_TEMPLATE.format(report_content=report_content, user_query=query)
    mock_estimate.assert_called_once_with(expected_prompt, model_name=agent.MODEL_NAME)

def test_ask_question_llm_error(agent, mock_dependencies):
    """Tests handling when the LLM call raises an exception."""
    mock_read, mock_estimate, mock_llm = mock_dependencies
    report_path = "test_report.txt"
    query = "What is the revenue?"
    report_content = "Revenue was $10M."
    estimated_tokens = 500

    # Configure mocks
    mock_read.return_value = report_content
    mock_estimate.return_value = estimated_tokens
    # Configure mock_llm to raise an exception
    mock_llm.generate_chat_response.side_effect = Exception("LLM API Error")
    
    # Call and assert the returned error message
    result = agent.ask_question(query, report_path)
    assert "Error: Failed to get response from language model. LLM API Error" in result
    mock_read.assert_called_once_with(report_path)
    expected_prompt = agent.PROMPT_TEMPLATE.format(report_content=report_content, user_query=query)
    mock_estimate.assert_called_once_with(expected_prompt, model_name=agent.MODEL_NAME)
    expected_messages = [{"role": "user", "content": expected_prompt}]
    mock_llm.generate_chat_response.assert_called_once_with(expected_messages)

def test_ask_question_llm_invalid_response(agent, mock_dependencies):
    """Tests handling when the LLM returns an invalid response (e.g., None)."""
    mock_read, mock_estimate, mock_llm = mock_dependencies
    report_path = "test_report.txt"
    query = "What is the revenue?"
    report_content = "Revenue was $10M."
    estimated_tokens = 500

    # Configure mocks
    mock_read.return_value = report_content
    mock_estimate.return_value = estimated_tokens
    # Configure mock_llm to return None
    mock_llm.generate_chat_response.return_value = None
    
    # Call and assert the returned error message
    result = agent.ask_question(query, report_path)
    assert "Error: Received invalid response from the language model." in result
    mock_read.assert_called_once_with(report_path)
    expected_prompt = agent.PROMPT_TEMPLATE.format(report_content=report_content, user_query=query)
    mock_estimate.assert_called_once_with(expected_prompt, model_name=agent.MODEL_NAME)
    expected_messages = [{"role": "user", "content": expected_prompt}]
    mock_llm.generate_chat_response.assert_called_once_with(expected_messages) 