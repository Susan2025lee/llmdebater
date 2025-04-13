import pytest
from unittest.mock import patch, MagicMock
import os
import sys

# --- Start Correct sys.path Modification ---
# Calculate project root and add src to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir) # Assumes tests/ is one level down from root
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)
# --- End Correct sys.path Modification ---

# Now imports from src/core should work directly
# Import PROMPT_TEMPLATE directly
# Also import MODEL_NAME constant
from core.answer_agent import ReportQAAgent, ContextLengthError, MAX_INPUT_TOKENS, MODEL_NAME
from core.prompts import ANSWER_PROMPT_TEMPLATE # Import the correct template
from core.llm_interface import LLMInterface # Import directly from core

# --- Fixtures --- #

@pytest.fixture
def mock_dependencies():
    """Mocks all external dependencies for AnswerAgent."""
    # Ensure mock paths target the module as imported (e.g., 'core.answer_agent...')
    with (
        patch('core.answer_agent.read_text_file') as mock_read,
        patch('core.answer_agent.estimate_token_count') as mock_estimate,
        patch('core.answer_agent.LLMInterface') as MockLLMInterface
    ):
        mock_llm_instance = MockLLMInterface.return_value
        mock_llm_instance.generate_chat_response = MagicMock()
        yield mock_read, mock_estimate, mock_llm_instance

@pytest.fixture
def agent(mock_dependencies):
    """Provides an instance of ReportQAAgent with mocked dependencies."""
    try:
        # Pass None for llm_config if AnswerAgent init expects it
        return ReportQAAgent(llm_config=None)
    except TypeError:
        # Fallback if it needs an LLMInterface instance
        return ReportQAAgent(llm_interface=MockLLMInterface()) # Pass mocked instance

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
    # Use the imported PROMPT_TEMPLATE
    expected_prompt = ANSWER_PROMPT_TEMPLATE.format(report_content=report_content, user_query=query)
    # Use the imported MODEL_NAME
    mock_estimate.assert_called_once_with(expected_prompt, model_name=MODEL_NAME)
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
    
    # Assert that FileNotFoundError is raised (as it's propagated)
    with pytest.raises(FileNotFoundError):
        agent.ask_question(query, report_path)
        
    mock_read.assert_called_once_with(report_path)

def test_ask_question_read_error(agent, mock_dependencies):
    """Tests handling for generic file reading errors."""
    mock_read, _, _ = mock_dependencies
    report_path = "error_file.txt"
    query = "Any question?"
    error_message = "Disk read error"

    # Configure mock_read to raise a generic Exception
    mock_read.side_effect = IOError(error_message)

    # Call and assert the specific OSError is raised by the agent
    # Use OSError because IOError might be an alias in some Python versions
    with pytest.raises(OSError) as excinfo:
        agent.ask_question(query, report_path)
    # Check that the raised exception contains the original error message
    assert error_message in str(excinfo.value)
    assert f"Could not read report file {report_path}" in str(excinfo.value)
    mock_read.assert_called_once_with(report_path)

def test_ask_question_empty_file(agent, mock_dependencies):
    """Tests handling when the report file is empty."""
    mock_read, _, _ = mock_dependencies
    report_path = "empty_report.txt"
    query = "Any question?"
    error_message = f"Report file is empty: {report_path}"

    # Configure mock_read to return empty string
    mock_read.return_value = ""

    # Call and assert the specific OSError is raised by the agent
    # (Agent catches ValueError and raises IOError/OSError)
    with pytest.raises(OSError) as excinfo:
        agent.ask_question(query, report_path)
    # Check that the raised exception contains the original ValueError message
    assert error_message in str(excinfo.value)
    assert f"Could not read report file {report_path}" in str(excinfo.value) 
    mock_read.assert_called_once_with(report_path)

def test_ask_question_context_length_exceeded(agent, mock_dependencies):
    """Tests returning error string when token estimate is too high."""
    mock_read, mock_estimate, _ = mock_dependencies
    report_path = "large_report.txt"
    query = "Summarize everything."
    report_content = "This is some report content."
    # Make estimate return a value just over the limit
    estimated_tokens = MAX_INPUT_TOKENS + 1 

    # Configure mocks
    mock_read.return_value = report_content
    mock_estimate.return_value = estimated_tokens
    
    # Assert that the agent *returns* an error string
    result = agent.ask_question(query, report_path)
    assert f"Input (report + query) exceeds the maximum allowed tokens" in result
    assert str(MAX_INPUT_TOKENS) in result
    assert str(estimated_tokens) in result
    
    mock_read.assert_called_once_with(report_path)
    # Check estimate was still called
    expected_prompt = ANSWER_PROMPT_TEMPLATE.format(report_content=report_content, user_query=query)
    # Use the imported MODEL_NAME
    mock_estimate.assert_called_once_with(expected_prompt, model_name=MODEL_NAME)

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
    # Assert the actual returned error message
    assert result == "Token estimation failed."
    mock_read.assert_called_once_with(report_path)
    expected_prompt = ANSWER_PROMPT_TEMPLATE.format(report_content=report_content, user_query=query)
    # Use the imported MODEL_NAME
    mock_estimate.assert_called_once_with(expected_prompt, model_name=MODEL_NAME)

def test_ask_question_llm_error(agent, mock_dependencies):
    """Tests handling when the LLM call raises an exception."""
    mock_read, mock_estimate, mock_llm = mock_dependencies
    report_path = "test_report.txt"
    query = "What is the revenue?"
    report_content = "Revenue was $10M."
    estimated_tokens = 500
    error_message = "LLM API Error"

    # Configure mocks
    mock_read.return_value = report_content
    mock_estimate.return_value = estimated_tokens
    # Configure mock_llm to raise an exception
    mock_llm.generate_chat_response.side_effect = Exception(error_message)
    
    # Call and assert the returned error message
    result = agent.ask_question(query, report_path)
    # Assert the actual returned error message
    assert result == f"Error getting response from language model: {error_message}"
    mock_read.assert_called_once_with(report_path)
    expected_prompt = ANSWER_PROMPT_TEMPLATE.format(report_content=report_content, user_query=query)
    # Use the imported MODEL_NAME
    mock_estimate.assert_called_once_with(expected_prompt, model_name=MODEL_NAME)
    expected_messages = [{"role": "user", "content": expected_prompt}]
    mock_llm.generate_chat_response.assert_called_once_with(expected_messages)

def test_ask_question_llm_invalid_response(agent, mock_dependencies):
    """Tests handling when the LLM returns an invalid response (e.g., None)."""
    mock_read, mock_estimate, mock_llm = mock_dependencies
    report_path = "test_report.txt"
    query = "What is the revenue?"
    report_content = "Revenue was $10M."
    estimated_tokens = 500
    error_message = "Received invalid response from the language model."

    # Configure mocks
    mock_read.return_value = report_content
    mock_estimate.return_value = estimated_tokens
    # Configure mock_llm to return None
    mock_llm.generate_chat_response.return_value = None
    
    # Call and assert the returned error message
    result = agent.ask_question(query, report_path)
    # Assert the actual returned error message
    assert result == f"Error getting response from language model: {error_message}"
    mock_read.assert_called_once_with(report_path)
    expected_prompt = ANSWER_PROMPT_TEMPLATE.format(report_content=report_content, user_query=query)
    # Use the imported MODEL_NAME
    mock_estimate.assert_called_once_with(expected_prompt, model_name=MODEL_NAME)
    expected_messages = [{"role": "user", "content": expected_prompt}]
    mock_llm.generate_chat_response.assert_called_once_with(expected_messages) 