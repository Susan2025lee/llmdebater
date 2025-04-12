import pytest
from unittest.mock import MagicMock, patch, call
import re
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

# Import the class to be tested
from core.orchestrator import Orchestrator

# Mock dependencies
from core.answer_agent import ReportQAAgent, ContextLengthError
from core.question_agent import QuestionAgent
from core.llm_interface import LLMInterface

# --- Constants for Tests ---
FAKE_Q_PATH = "fake_q.md"
FAKE_A_PATH = "fake_a.md"
Q_CONTENT = "Question Document Content"
A_CONTENT = "Answer Document Content"

@pytest.fixture
def mock_question_agent():
    """Fixture for a mocked QuestionAgent."""
    mock = MagicMock(spec=QuestionAgent)
    # Configure the correct method name
    mock.generate_questions.return_value = ["Initial Question 1?", "Initial Question 2?"]
    return mock

@pytest.fixture
def mock_answer_agent():
    """Fixture for a mocked ReportQAAgent."""
    mock = MagicMock(spec=ReportQAAgent)
    # Configure default mock behavior if needed, e.g., return specific answers
    mock.ask_with_content.return_value = "Mocked Answer."
    return mock

@pytest.fixture
def mock_llm_interface():
    """Fixture for a mocked LLMInterface."""
    mock = MagicMock(spec=LLMInterface)
    # Configure default mock behavior for satisfaction/follow-up calls
    # Example: Always return "Satisfied" initially
    mock.generate_response.return_value = "Assessment: Satisfied"
    return mock

@pytest.fixture
def orchestrator(mock_question_agent, mock_answer_agent, mock_llm_interface):
    """Fixture for an Orchestrator instance with mocked dependencies."""
    return Orchestrator(
        question_agent=mock_question_agent,
        answer_agent=mock_answer_agent,
        llm_interface=mock_llm_interface,
        max_follow_ups=2
    )

# --- Test Cases --- TODO T2.12

def test_orchestrator_initialization(orchestrator, mock_question_agent, mock_answer_agent, mock_llm_interface):
    """Test if the orchestrator initializes correctly with its dependencies."""
    assert orchestrator.question_agent == mock_question_agent
    assert orchestrator.answer_agent == mock_answer_agent
    assert orchestrator.llm_interface == mock_llm_interface
    assert orchestrator.max_follow_ups == 2
    assert "{question}" in orchestrator.satisfaction_prompt_template
    assert "{answer}" in orchestrator.satisfaction_prompt_template
    assert "{question}" in orchestrator.follow_up_prompt_template
    assert "{answer}" in orchestrator.follow_up_prompt_template


@patch('core.orchestrator.read_text_file')
@patch('builtins.input', return_value='n') # Simulate user typing 'n' to stop after first question
@patch('builtins.print')
def test_run_interaction_basic_flow(mock_print, mock_input, mock_read_file, orchestrator, mock_question_agent, mock_answer_agent):
    """Test the basic flow of run_interaction: generates questions, processes one, stops."""
    mock_read_file.return_value = A_CONTENT # Answer doc is loaded by orchestrator
    initial_question = "Initial Question 1?"
    answer = "Satisfactory Answer 1."
    mock_question_agent.generate_questions.return_value = [initial_question]
    mock_answer_agent.ask_with_content.return_value = answer
    
    # Patch the check_satisfaction method directly on the instance for this test
    # This avoids needing to mock the llm_interface call specifically for this test's purpose
    with patch.object(orchestrator, 'check_satisfaction', return_value=(True, "Looks good.")) as mock_check:
        orchestrator.run_interaction(FAKE_Q_PATH, FAKE_A_PATH, num_initial_questions=1)

    mock_read_file.assert_called_once_with(FAKE_A_PATH)
    mock_question_agent.generate_questions.assert_called_once_with(FAKE_Q_PATH, 1)
    mock_answer_agent.ask_with_content.assert_called_once_with(initial_question, A_CONTENT)
    mock_check.assert_called_once_with(initial_question, answer)
    mock_input.assert_not_called()


@patch('core.orchestrator.read_text_file')
@patch('builtins.input', return_value='n') # Simulate user typing 'n' to stop after first question
@patch('builtins.print')
def test_run_interaction_with_follow_up(mock_print, mock_input, mock_read_file, orchestrator, mock_question_agent, mock_answer_agent):
    """Test the flow with one follow-up question needed and answered successfully."""
    mock_read_file.return_value = A_CONTENT 
    initial_question = "Initial Question 1?"
    initial_answer = "Unsatisfactory Answer."
    follow_up_question = "Follow-up Question 1?"
    final_answer = "Now this is satisfactory."
    
    mock_question_agent.generate_questions.return_value = [initial_question]
    mock_answer_agent.ask_with_content.side_effect = [initial_answer, final_answer]

    # Patch public methods directly on the instance
    # No leading underscores needed
    with patch.object(orchestrator, 'check_satisfaction', side_effect=[(False, "Incomplete."), (True, "Complete.")]) as mock_check, \
         patch.object(orchestrator, 'generate_follow_up', return_value=follow_up_question) as mock_generate:
        
        orchestrator.run_interaction(FAKE_Q_PATH, FAKE_A_PATH, num_initial_questions=1)

    mock_question_agent.generate_questions.assert_called_once_with(FAKE_Q_PATH, 1)
    mock_answer_agent.ask_with_content.assert_has_calls([call(initial_question, A_CONTENT), call(follow_up_question, A_CONTENT)])
    mock_check.assert_has_calls([call(initial_question, initial_answer), call(follow_up_question, final_answer)])
    mock_generate.assert_called_once_with(initial_question, initial_answer)
    mock_input.assert_not_called()


@patch('core.orchestrator.read_text_file')
@patch('builtins.input', return_value='n') # Simulate user typing 'n' to stop after first question
@patch('builtins.print')
def test_run_interaction_max_follow_ups(mock_print, mock_input, mock_read_file, orchestrator, mock_question_agent, mock_answer_agent):
    """Test the flow where max_follow_ups is reached because answers remain unsatisfactory."""
    mock_read_file.return_value = A_CONTENT
    max_follow_ups = orchestrator.max_follow_ups 
    num_attempts = max_follow_ups + 1
    
    initial_question = "Initial Question 1?"
    follow_up_questions = [f"Follow-up {i+1}?" for i in range(max_follow_ups)]
    answers = [f"Unsatisfactory Answer {i+1}" for i in range(num_attempts)]

    mock_question_agent.generate_questions.return_value = [initial_question]
    mock_answer_agent.ask_with_content.side_effect = answers

    # Patch public methods
    # No leading underscores
    with patch.object(orchestrator, 'check_satisfaction', side_effect=[(False, f"Ans {i+1} incomplete.") for i in range(num_attempts)]) as mock_check, \
         patch.object(orchestrator, 'generate_follow_up', side_effect=follow_up_questions) as mock_generate:

        orchestrator.run_interaction(FAKE_Q_PATH, FAKE_A_PATH, num_initial_questions=1)

    mock_question_agent.generate_questions.assert_called_once_with(FAKE_Q_PATH, 1)
    assert mock_answer_agent.ask_with_content.call_count == num_attempts
    assert mock_check.call_count == num_attempts
    assert mock_generate.call_count == max_follow_ups
    mock_input.assert_not_called()


@patch('core.orchestrator.read_text_file')
@patch('builtins.input', return_value='n') # Simulate user typing 'n' to stop after first question
@patch('builtins.print')
def test_run_interaction_follow_up_fails(mock_print, mock_input, mock_read_file, orchestrator, mock_question_agent, mock_answer_agent):
    """Test that the loop terminates correctly if follow-up generation returns None."""
    mock_read_file.return_value = A_CONTENT
    initial_question = "Initial Question 1?"
    initial_answer = "Unsatisfactory Answer."

    mock_question_agent.generate_questions.return_value = [initial_question]
    mock_answer_agent.ask_with_content.return_value = initial_answer

    # Patch public methods
    # No leading underscores
    with patch.object(orchestrator, 'check_satisfaction', return_value=(False, "Unsatisfactory")) as mock_check, \
         patch.object(orchestrator, 'generate_follow_up', return_value=None) as mock_generate:

        orchestrator.run_interaction(FAKE_Q_PATH, FAKE_A_PATH, num_initial_questions=1)

    mock_answer_agent.ask_with_content.assert_called_once_with(initial_question, A_CONTENT)
    mock_check.assert_called_once_with(initial_question, initial_answer)
    mock_generate.assert_called_once_with(initial_question, initial_answer)
    mock_input.assert_not_called()


# --- Tests for Internal Methods ---

# Test _check_satisfaction parsing
@pytest.mark.parametrize("response_text, expected_satisfied, expected_reason", [
    ("Assessment: Satisfied", True, None),
    ("Assessment: Unsatisfied\nReason: Missing details about X.", False, "Missing details about X."),
    ("assessment: satisfied", True, None),
    ("Assessment:Unsatisfied\nReason: Vague answer.", False, "Vague answer."),
    ("Assessment: Unsatisfied \n Reason: Needs more data.", False, "Needs more data."),
    ("Assessment: Satisfied\nReason: N/A", True, "N/A"),
    ("Satisfied", False, None),
    ("Assessment: Maybe", False, None),
    ("Reason: Something is wrong", False, "Something is wrong"),
    ("Assessment: Unsatisfied", False, None), # Expect None reason if block missing
    ("", False, None),
])
def test_check_satisfaction_parsing(orchestrator, mock_llm_interface, response_text, expected_satisfied, expected_reason):
    """Refactored: Test check_satisfaction by mocking the LLM call it makes."""
    mock_llm_interface.generate_response.return_value = response_text

    is_satisfied, reason = orchestrator.check_satisfaction("test_q", "test_a")

    assert is_satisfied == expected_satisfied
    assert reason == expected_reason

    mock_llm_interface.generate_response.assert_called_once()


# Test _generate_follow_up parsing
@pytest.mark.parametrize("response_text, expected_follow_up", [
    ("Follow-up Question: What about detail Y?", "What about detail Y?"),
    ("follow-up question:  Explain Z further.", "Explain Z further."),
    ("What is the specific value for X?", "What is the specific value for X?"),
    ("Follow-up Question:", None),
    ("", None),
])
def test_generate_follow_up_parsing(orchestrator, mock_llm_interface, response_text, expected_follow_up):
    """Refactored: Test generate_follow_up by mocking the LLM call it makes."""
    mock_llm_interface.generate_response.return_value = response_text
    
    follow_up = orchestrator.generate_follow_up("orig_q", "bad_answer")
    
    assert follow_up == expected_follow_up
    mock_llm_interface.generate_response.assert_called_once()


def test_generate_follow_up_llm_error(orchestrator, mock_llm_interface):
    mock_llm_interface.generate_response.side_effect = Exception("API timeout")
    follow_up = orchestrator.generate_follow_up("orig_q", "bad_answer")
    assert follow_up is None


@patch('core.orchestrator.read_text_file')
@patch('builtins.input')
@patch('builtins.print')
def test_run_interaction_user_input_variations(mock_print, mock_input, mock_read_file, orchestrator, mock_question_agent, mock_answer_agent):
    """Test the continue/stop logic with various user inputs ('y', 'n', case variations)."""
    mock_read_file.return_value = A_CONTENT 
    initial_questions = ["Q1?", "Q2?"]
    mock_question_agent.generate_questions.return_value = initial_questions
    mock_answer_agent.ask_with_content.return_value = "Some Answer"
    # Patch public method
    with patch.object(orchestrator, 'check_satisfaction', return_value=(True, None)) as mock_check:
        mock_input.side_effect = [' y ', 'N'] 
        orchestrator.run_interaction(FAKE_Q_PATH, FAKE_A_PATH, num_initial_questions=2)

    assert mock_check.call_count == 2
    mock_input.assert_called_once_with("\nContinue with the next initial question? (y/n): ")


@patch('core.orchestrator.read_text_file')
@patch('builtins.input')
@patch('builtins.print')
def test_run_interaction_file_not_found(mock_print, mock_input, mock_read_file, orchestrator, mock_question_agent):
    """Test the behavior when an input file is not found."""
    # Simulate read_text_file raising FileNotFoundError
    # The actual exception message might vary slightly, but let's assume it includes the path
    exception_instance = FileNotFoundError(f"File not found: {FAKE_A_PATH}")
    mock_read_file.side_effect = exception_instance
    
    orchestrator.run_interaction(FAKE_Q_PATH, FAKE_A_PATH, num_initial_questions=5)
    
    # Assert read_text_file was called (and raised error)
    assert mock_read_file.called
    assert mock_read_file.call_args == call(FAKE_A_PATH)
    mock_question_agent.generate_questions.assert_not_called()
    
    # Check error message was printed
    error_print_call = None
    for call_args in mock_print.call_args_list:
        args, kwargs = call_args
        # Check if stderr was used (requires Python 3.3+ for file=sys.stderr capture in print mock)
        # Simpler check for now:
        if args and isinstance(args[0], str) and "Error: Input file not found" in args[0]:
             error_print_call = call_args
             break
    assert error_print_call is not None, "Error message for FileNotFoundError not printed"
    assert str(exception_instance) in error_print_call[0][0]
    mock_input.assert_not_called()


@patch('core.orchestrator.read_text_file')
@patch('builtins.input')
@patch('builtins.print')
def test_run_interaction_error_during_processing(mock_print, mock_input, mock_read_file, orchestrator, mock_question_agent, mock_answer_agent):
    """Test error handling for unexpected errors during processing."""
    mock_read_file.return_value = A_CONTENT
    initial_questions = ["Q1?"]
    mock_question_agent.generate_questions.return_value = initial_questions
    error_message = "Unexpected processing error!"
    
    # Patch the public check_satisfaction method to raise an error
    with patch.object(orchestrator, 'check_satisfaction', side_effect=RuntimeError(error_message)) as mock_check:
        orchestrator.run_interaction(FAKE_Q_PATH, FAKE_A_PATH, num_initial_questions=1)

    mock_answer_agent.ask_with_content.assert_called_once()
    mock_check.assert_called_once()
    # Check error message was printed by the specific RuntimeError handler
    error_print_call = None
    for call_args in mock_print.call_args_list:
        args, kwargs = call_args
        # Look for the message from the RuntimeError except block
        if args and isinstance(args[0], str) and f"Error: Runtime issue during processing. {error_message}" in args[0]:
             error_print_call = call_args
             break
    assert error_print_call is not None, "Expected error message not found in print calls"
    mock_input.assert_not_called()


# TODO T2.12: Add more tests:
# - Test different user inputs for continuing interaction (y, n, invalid)
# - Test error handling within the loop 