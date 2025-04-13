import pytest
from unittest.mock import patch, MagicMock
import os
import sys

# --- Add src to sys.path --- #
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)
# --- End sys.path Modification ---

# Import the class and dependencies to test/mock
from core.answer_agent_v3 import AnswerAgentV3, ContextLengthError, MAX_INPUT_TOKENS_V3, MODEL_NAME
from core.prompts import DEBATE_PARTICIPATION_PROMPT_TEMPLATE, ANSWER_PROMPT_TEMPLATE
from core.llm_interface import LLMInterface # To mock the instance

# --- Fixtures --- #

@pytest.fixture
def mock_dependencies_v3():
    """Mocks all external dependencies for AnswerAgentV3."""
    with (
        patch('core.answer_agent_v3.read_text_file') as mock_read,
        patch('core.answer_agent_v3.estimate_token_count') as mock_estimate,
        patch('core.answer_agent_v3.LLMInterface') as MockLLMInterface # Mock the class used in init
    ):
        # Create a mock instance that the agent's __init__ will receive
        mock_llm_instance = MockLLMInterface.return_value
        mock_llm_instance.generate_chat_response = MagicMock() # For ask_question
        mock_llm_instance.generate_response = MagicMock()      # For participate_in_debate
        # Make model_name accessible on the mock instance
        mock_llm_instance.model_name = MODEL_NAME 
        yield mock_read, mock_estimate, mock_llm_instance

@pytest.fixture
def agent_v3(mock_dependencies_v3):
    """Provides an instance of AnswerAgentV3 with mocked dependencies."""
    _, _, mock_llm = mock_dependencies_v3 # Unpack to get the instance
    # Pass the *mock instance* to the constructor
    return AnswerAgentV3(llm_interface=mock_llm)

# --- Test Cases for ask_question (Round 0 - Copied Logic) --- #

def test_ask_question_success_v3(agent_v3, mock_dependencies_v3):
    """Tests successful flow of ask_question in V3 agent."""
    # (Test logic similar to test_answer_agent.py::test_ask_question_success)
    mock_read, mock_estimate, mock_llm = mock_dependencies_v3
    
    report_path = "test_report_v3.txt"
    query = "What is the profit margin?"
    report_content = "Profit margin was 15% in Q1."
    expected_answer = "The report states the profit margin was 15% in Q1."
    estimated_tokens = 450

    # Configure mocks
    mock_read.return_value = report_content
    mock_estimate.return_value = estimated_tokens
    mock_llm.generate_chat_response.return_value = expected_answer # Checks chat response mock
    
    # Call the method
    answer = agent_v3.ask_question(query, report_path)
    
    # Assertions
    assert answer == expected_answer
    mock_read.assert_called_once_with(report_path)
    expected_prompt = ANSWER_PROMPT_TEMPLATE.format(report_content=report_content, user_query=query)
    mock_estimate.assert_called_once_with(expected_prompt, model_name=MODEL_NAME)
    expected_messages = [{"role": "user", "content": expected_prompt}]
    mock_llm.generate_chat_response.assert_called_once_with(expected_messages)

def test_ask_question_file_not_found_v3(agent_v3, mock_dependencies_v3):
    """Tests ask_question file not found handling."""
    # (Test logic similar to test_answer_agent.py::test_ask_question_file_not_found)
    mock_read, _, _ = mock_dependencies_v3
    report_path = "non_existent_v3.txt"
    query = "Any question? v3"

    mock_read.side_effect = FileNotFoundError(f"File not found: {report_path}")
    
    with pytest.raises(FileNotFoundError):
        agent_v3.ask_question(query, report_path)
        
    mock_read.assert_called_once_with(report_path)

def test_ask_question_context_limit_exceeded_v3(agent_v3, mock_dependencies_v3):
    """Tests ask_question context limit handling."""
    # (Test logic similar to test_answer_agent.py::test_ask_question_context_limit_exceeded)
    mock_read, mock_estimate, _ = mock_dependencies_v3
    report_path = "large_report_v3.txt"
    query = "Summarize everything V3."
    report_content = "This is some report content V3."
    # Use MAX_INPUT_TOKENS from original answer_agent for this test
    from core.answer_agent import MAX_INPUT_TOKENS 
    estimated_tokens = MAX_INPUT_TOKENS + 1 

    mock_read.return_value = report_content
    mock_estimate.return_value = estimated_tokens
    
    # Call the method - ask_question delegates to ask_with_content, 
    # which catches ContextLengthError and returns a string
    result = agent_v3.ask_question(query, report_path)
    
    # Assert the returned error string contains expected info
    assert f"Input (report + query) exceeds the maximum allowed tokens" in result
    assert str(MAX_INPUT_TOKENS) in result
    assert str(estimated_tokens) in result
    
    mock_read.assert_called_once_with(report_path)
    expected_prompt = ANSWER_PROMPT_TEMPLATE.format(report_content=report_content, user_query=query)
    mock_estimate.assert_called_once_with(expected_prompt, model_name=MODEL_NAME)

# --- Test Cases for participate_in_debate (V3 Specific) --- #

def test_participate_in_debate_success(agent_v3, mock_dependencies_v3):
    """Tests the successful flow of participating in a debate round."""
    _, mock_estimate, mock_llm = mock_dependencies_v3 # mock_read not used here
    
    question = "Original question?"
    debate_history = [
        ("Agent 1", 0, "Initial answer from agent 1."),
        ("Agent 2", 0, "Initial answer from agent 2.")
    ]
    doc_content = "This agent's specific document content."
    current_round = 1
    expected_response = "Agent 3's response for round 1."
    estimated_tokens = 600

    # Configure mocks
    mock_estimate.return_value = estimated_tokens
    mock_llm.generate_response.return_value = expected_response # Use generate_response mock

    # Call the method
    response = agent_v3.participate_in_debate(question, debate_history, doc_content, current_round)

    # Assertions
    assert response == expected_response
    
    # Check prompt formatting and LLM call
    expected_history_str = agent_v3._format_debate_history(debate_history)
    expected_prompt = DEBATE_PARTICIPATION_PROMPT_TEMPLATE.format(
        question=question,
        document_context=doc_content,
        debate_history=expected_history_str,
        current_round=current_round
    )
    mock_estimate.assert_called_once_with(expected_prompt, model_name=MODEL_NAME)
    # Verify generate_response was called
    mock_llm.generate_response.assert_called_once_with(prompt=expected_prompt)

def test_participate_in_debate_empty_history(agent_v3, mock_dependencies_v3):
    """Tests debate participation with empty history (should still work)."""
    _, mock_estimate, mock_llm = mock_dependencies_v3
    
    question = "Original question?"; debate_history = [] # Empty history
    doc_content = "Doc content."; current_round = 1; expected_response = "Response round 1 empty history."
    estimated_tokens = 300

    mock_estimate.return_value = estimated_tokens
    mock_llm.generate_response.return_value = expected_response

    response = agent_v3.participate_in_debate(question, debate_history, doc_content, current_round)

    assert response == expected_response
    expected_history_str = "No debate history yet."
    expected_prompt = DEBATE_PARTICIPATION_PROMPT_TEMPLATE.format(
        question=question, document_context=doc_content, 
        debate_history=expected_history_str, current_round=current_round
    )
    mock_estimate.assert_called_once_with(expected_prompt, model_name=MODEL_NAME)
    mock_llm.generate_response.assert_called_once_with(prompt=expected_prompt)

def test_participate_in_debate_context_limit_exceeded(agent_v3, mock_dependencies_v3):
    """Tests debate participation context limit handling."""
    _, mock_estimate, _ = mock_dependencies_v3
    question = "Q"; debate_history = []; doc_content = "Content"; current_round = 1
    estimated_tokens = MAX_INPUT_TOKENS_V3 + 1

    mock_estimate.return_value = estimated_tokens

    with pytest.raises(ContextLengthError) as excinfo:
        agent_v3.participate_in_debate(question, debate_history, doc_content, current_round)
    
    assert str(MAX_INPUT_TOKENS_V3) in str(excinfo.value)
    assert str(estimated_tokens) in str(excinfo.value)
    assert f"debate round {current_round}" in str(excinfo.value)

    expected_history_str = agent_v3._format_debate_history(debate_history)
    expected_prompt = DEBATE_PARTICIPATION_PROMPT_TEMPLATE.format(
        question=question, document_context=doc_content, 
        debate_history=expected_history_str, current_round=current_round
    )
    mock_estimate.assert_called_once_with(expected_prompt, model_name=MODEL_NAME)

def test_participate_in_debate_token_estimation_error(agent_v3, mock_dependencies_v3):
    """Tests debate participation token estimation failure."""
    _, mock_estimate, _ = mock_dependencies_v3
    question = "Q"; debate_history = []; doc_content = "Content"; current_round = 1

    mock_estimate.return_value = -1 # Simulate error

    with pytest.raises(ValueError) as excinfo:
        agent_v3.participate_in_debate(question, debate_history, doc_content, current_round)
    
    assert "Token estimation failed" in str(excinfo.value)

    expected_history_str = agent_v3._format_debate_history(debate_history)
    expected_prompt = DEBATE_PARTICIPATION_PROMPT_TEMPLATE.format(
        question=question, document_context=doc_content, 
        debate_history=expected_history_str, current_round=current_round
    )
    mock_estimate.assert_called_once_with(expected_prompt, model_name=MODEL_NAME)

def test_participate_in_debate_llm_error(agent_v3, mock_dependencies_v3):
    """Tests debate participation LLM communication error."""
    _, mock_estimate, mock_llm = mock_dependencies_v3
    question = "Q"; debate_history = []; doc_content = "Content"; current_round = 1
    estimated_tokens = 500
    error_message = "LLM Service Unavailable"

    mock_estimate.return_value = estimated_tokens
    mock_llm.generate_response.side_effect = Exception(error_message)

    with pytest.raises(RuntimeError) as excinfo:
        agent_v3.participate_in_debate(question, debate_history, doc_content, current_round)
    
    assert error_message in str(excinfo.value)
    assert "Error generating debate response via LLM" in str(excinfo.value)

    expected_history_str = agent_v3._format_debate_history(debate_history)
    expected_prompt = DEBATE_PARTICIPATION_PROMPT_TEMPLATE.format(
        question=question, document_context=doc_content, 
        debate_history=expected_history_str, current_round=current_round
    )
    mock_estimate.assert_called_once_with(expected_prompt, model_name=MODEL_NAME)
    mock_llm.generate_response.assert_called_once_with(prompt=expected_prompt)

def test_participate_in_debate_empty_doc_content(agent_v3, mock_dependencies_v3):
    """Tests participate_in_debate with empty document content."""
    question = "Q"; debate_history = []; doc_content = ""; current_round = 1

    with pytest.raises(ValueError) as excinfo:
        agent_v3.participate_in_debate(question, debate_history, doc_content, current_round)
    
    assert "Document content cannot be empty" in str(excinfo.value)

# ... potentially add more tests for edge cases ... 