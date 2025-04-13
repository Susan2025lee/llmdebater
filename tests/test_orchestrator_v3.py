# Tests for OrchestratorV3 

import pytest
from unittest.mock import patch, MagicMock, call, mock_open
import os
import sys
from typing import List, Tuple, Iterator

# --- Add src to sys.path --- #
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)
# --- End sys.path Modification ---

# Import the class to test and dependencies to mock
from core.orchestrator_v3 import OrchestratorV3, ContextLengthError
# Import agent classes only for type hinting and mocking purposes
from core.question_agent import QuestionAgent 
from core.answer_agent_v3 import AnswerAgentV3
from core.llm_interface import LLMInterface

# --- Fixtures --- #

@pytest.fixture
def mock_question_agent():
    mock = MagicMock(spec=QuestionAgent)
    mock.generate_questions.return_value = ["Q1?", "Q2?"] # Default success
    return mock

@pytest.fixture
def mock_answer_agents_v3():
    # Create two mock V3 answer agents
    agent1 = MagicMock(spec=AnswerAgentV3)
    agent1.ask_question.return_value = "Agent 1 Initial Answer (R0)"
    agent1.participate_in_debate.return_value = "Agent 1 Debate Response"
    # Helper method needed for synthesis formatting in orchestrator
    agent1._format_debate_history.side_effect = lambda history: "Formatted: " + str(history)
    
    agent2 = MagicMock(spec=AnswerAgentV3)
    agent2.ask_question.return_value = "Agent 2 Initial Answer (R0)"
    agent2.participate_in_debate.return_value = "Agent 2 Debate Response"
    agent2._format_debate_history.side_effect = lambda history: "Formatted: " + str(history)
    
    return [agent1, agent2]

@pytest.fixture
def mock_llm_interface():
    mock = MagicMock(spec=LLMInterface)
    # For synthesis call
    mock.generate_response.return_value = "Synthesized Final Answer"
    return mock

@pytest.fixture
def orchestrator_v3(mock_question_agent, mock_answer_agents_v3, mock_llm_interface):
    """Provides a default OrchestratorV3 instance with mocked dependencies."""
    return OrchestratorV3(
        question_agent=mock_question_agent,
        answer_agents=mock_answer_agents_v3,
        output_file_path="mock_output_v3.md",
        llm_interface=mock_llm_interface,
        num_initial_questions=2,
        max_debate_rounds=1 # Default to 1 debate round for tests
    )

# --- Test Cases --- #

def test_orchestrator_v3_init_success(orchestrator_v3, mock_question_agent, mock_answer_agents_v3, mock_llm_interface):
    """Tests successful initialization."""
    assert orchestrator_v3.question_agent == mock_question_agent
    assert orchestrator_v3.answer_agents == mock_answer_agents_v3
    assert orchestrator_v3.llm == mock_llm_interface
    assert orchestrator_v3.output_file_path == "mock_output_v3.md"
    assert orchestrator_v3.num_initial_questions == 2
    assert orchestrator_v3.max_debate_rounds == 1

def test_orchestrator_v3_init_no_agents():
    """Tests initialization failure with no answer agents."""
    with pytest.raises(ValueError, match="At least one AnswerAgentV3"):
        OrchestratorV3(MagicMock(), [], "out.md", MagicMock(), 2, 1)

def test_orchestrator_v3_init_negative_rounds():
    """Tests initialization failure with negative debate rounds."""
    with pytest.raises(ValueError, match="Maximum debate rounds cannot be negative"):
        OrchestratorV3(MagicMock(), [MagicMock()], "out.md", MagicMock(), 2, -1)

def test_run_full_debate_success_flow(orchestrator_v3, mock_question_agent, mock_answer_agents_v3, mock_llm_interface):
    """Tests the happy path of the run_full_debate generator."""
    q_doc_path = "q_doc.md"
    a_doc_paths = ["a1.md", "a2.md"]
    mock_agent1, mock_agent2 = mock_answer_agents_v3

    # Mock open for reading agent docs and writing output
    # Simulate reading content, then handle writing
    read_content = { a_doc_paths[0]: "Doc 1 Content", a_doc_paths[1]: "Doc 2 Content" }
    mock_write = mock_open()

    def mock_open_side_effect(path, mode='r', encoding=None):
        if mode in ('w', 'a') and path == orchestrator_v3.output_file_path: # Handle write and append
            return mock_write.return_value # Use the write mock
        elif mode == 'r' and path in read_content:
            # Return a mock file handle that reads specific content
            return mock_open(read_data=read_content[path]).return_value 
        else:
            # Fallback for unexpected open calls
            raise FileNotFoundError(f"Unexpected path in mock_open: {path}")

    with patch('builtins.open', side_effect=mock_open_side_effect) as mock_file_open:
        # Consume the generator
        results = list(orchestrator_v3.run_full_debate(q_doc_path, a_doc_paths))

    # Basic assertions on yields (more detailed checks needed)
    assert len(results) > 10 # Expect several steps
    assert results[0][0] == "System" # First message is System start
    assert results[-1][0] == "System" # Last message is System complete
    # Check if specific agent messages were yielded
    assert any(r[0] == "Question Agent" for r in results)
    assert any("Answer Agent V3 1" in r[0] for r in results)
    assert any("Answer Agent V3 2" in r[0] for r in results)
    assert any(r[0] == "Synthesizer" for r in results)

    # Check agent calls
    mock_question_agent.generate_questions.assert_called_once_with(q_doc_path, 2)
    # Round 0 calls
    mock_agent1.ask_question.assert_called_with("Q2?", a_doc_paths[0]) # Called for Q1 and Q2
    mock_agent2.ask_question.assert_called_with("Q2?", a_doc_paths[1])
    assert mock_agent1.ask_question.call_count == 2
    assert mock_agent2.ask_question.call_count == 2
    # Round 1 calls (max_debate_rounds=1)
    # History will contain R0 answers when R1 is called
    mock_agent1.participate_in_debate.assert_called()
    mock_agent2.participate_in_debate.assert_called()
    assert mock_agent1.participate_in_debate.call_count == 2 # Once per initial question
    assert mock_agent2.participate_in_debate.call_count == 2
    # Check synthesis call (LLM interface)
    mock_llm_interface.generate_response.assert_called()
    assert mock_llm_interface.generate_response.call_count == 2 # Once per initial question

    # Check output file writing
    mock_file_open.assert_any_call(orchestrator_v3.output_file_path, "w", encoding="utf-8") # Header write
    mock_file_open.assert_any_call(orchestrator_v3.output_file_path, "a", encoding="utf-8") # Append Q/A
    # Check content written (basic check on final call)
    handle = mock_write() # Get the file handle mock used for writing
    handle.write.assert_any_call("## Question:\nQ2?\n\n") # Check for last question
    handle.write.assert_any_call("### Final Answer (Synthesized V3):\nSynthesized Final Answer\n\n") # Check for last answer
    handle.write.assert_any_call("---\n\n")

def test_run_full_debate_agent_path_mismatch(orchestrator_v3):
    """Tests generator behavior when agent/path counts mismatch."""
    q_doc_path = "q.md"
    a_doc_paths = ["a1.md"] # Only one path for two agents
    
    results = list(orchestrator_v3.run_full_debate(q_doc_path, a_doc_paths))
    
    assert len(results) == 2 # Start message + Error message
    assert results[1][0] == "System"
    assert "does not match" in results[1][1]

def test_run_full_debate_question_gen_error(orchestrator_v3, mock_question_agent):
    """Tests generator behavior when question generation fails."""
    q_doc_path = "q.md"; a_doc_paths = ["a1.md", "a2.md"]
    mock_question_agent.generate_questions.side_effect = Exception("LLM Q Error")

    results = list(orchestrator_v3.run_full_debate(q_doc_path, a_doc_paths))
    
    assert len(results) == 3 # Start, Generating Q, Error
    assert results[2][0] == "System"
    assert "Error generating initial questions" in results[2][1]
    assert "LLM Q Error" in results[2][1]

def test_run_full_debate_no_questions_generated(orchestrator_v3, mock_question_agent):
    """Tests generator behavior when no questions are generated but no error."""
    q_doc_path = "q.md"; a_doc_paths = ["a1.md", "a2.md"]
    mock_question_agent.generate_questions.return_value = [] # No questions

    results = list(orchestrator_v3.run_full_debate(q_doc_path, a_doc_paths))
    
    assert len(results) == 4 # Start, Generating Q, Warning, Stopping
    assert results[2][0] == "Question Agent"
    assert "Warning: No initial questions" in results[2][1]
    assert results[3][0] == "System"
    assert "No initial questions generated. Stopping workflow." in results[3][1]

def test_run_full_debate_file_init_error(orchestrator_v3):
    """Tests generator behavior when output file initialization fails."""
    q_doc_path = "q.md"; a_doc_paths = ["a1.md", "a2.md"]
    
    with patch('builtins.open', mock_open()) as mock_file_open: # Use default mock_open
        mock_file_open.side_effect = IOError("Permission denied")
        results = list(orchestrator_v3.run_full_debate(q_doc_path, a_doc_paths))

    assert len(results) == 4 # Start, Gen Q, Q Generated, File Error
    assert results[-1][0] == "System"
    assert "Error creating/accessing output file" in results[-1][1]
    assert "Permission denied" in results[-1][1]

# --- TODO: Add More Tests --- #
# - Test error handling within Round 0 (ask_question fails)
# - Test error handling within Debate Rounds (participate_in_debate fails)
# - Test error handling during synthesis (LLM generate_response fails)
# - Test error handling during final file write (_write_output fails)
# - Test behavior with max_debate_rounds = 0
# - Test complex yield sequence verification 