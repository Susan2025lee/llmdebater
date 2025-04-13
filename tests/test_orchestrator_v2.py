import pytest
import sys
import os
from unittest.mock import MagicMock, patch, call

# Add src directory to sys.path to allow importing core modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from core.orchestrator_v2 import OrchestratorV2
from core.question_agent import QuestionAgent
from core.answer_agent import ReportQAAgent, ContextLengthError
from core.llm_interface import LLMInterface

# --- Fixtures --- (Similar to test_orchestrator.py)

@pytest.fixture
def mock_question_agent():
    mock = MagicMock(spec=QuestionAgent)
    mock.generate_questions.return_value = ["Q1?", "Q2?"]
    return mock

@pytest.fixture
def mock_answer_agent_factory(): # Factory to create multiple mocks
    def _factory(name="Agent"):
        mock = MagicMock(spec=ReportQAAgent)
        mock.ask_question.return_value = f"Answer from {name}"
        # Simulate loading content during init if needed, or assume pre-loaded
        mock.agent_name = name # Add a name for easier debugging
        return mock
    return _factory

@pytest.fixture
def mock_llm_interface():
    mock = MagicMock(spec=LLMInterface)
    # We'll configure this later for debate prompt testing
    mock.generate_response.return_value = "Synthesized Final Answer"
    return mock

@pytest.fixture
def mock_open():
    with patch('builtins.open', MagicMock()) as mock_open:
        yield mock_open

# --- Test Cases ---

FAKE_Q_DOC = "path/to/q_doc.md"
FAKE_OUTPUT = "path/to/output.md"
FAKE_ANSWER_DOC_1 = "path/to/answer1.md"
FAKE_ANSWER_DOC_2 = "path/to/answer2.md"

# --- Initialization Tests ---

def test_orchestrator_v2_initialization(
    mock_question_agent, mock_answer_agent_factory, mock_llm_interface
):
    """Tests successful initialization."""
    mock_aa1 = mock_answer_agent_factory("AA1")
    mock_aa2 = mock_answer_agent_factory("AA2")
    orchestrator = OrchestratorV2(
        question_agent=mock_question_agent,
        answer_agents=[mock_aa1, mock_aa2],
        output_file_path=FAKE_OUTPUT,
        llm_interface=mock_llm_interface,
        num_initial_questions=3,
    )
    assert orchestrator.question_agent == mock_question_agent
    assert orchestrator.answer_agents == [mock_aa1, mock_aa2]
    assert orchestrator.output_file_path == FAKE_OUTPUT
    assert orchestrator.llm == mock_llm_interface
    assert orchestrator.num_initial_questions == 3

def test_orchestrator_v2_init_no_answer_agents(mock_question_agent, mock_llm_interface):
    """Tests ValueError if no answer agents are provided."""
    with pytest.raises(ValueError, match="At least one ReportQAAgent must be provided."):
        OrchestratorV2(
            question_agent=mock_question_agent,
            answer_agents=[],
            output_file_path=FAKE_OUTPUT,
            llm_interface=mock_llm_interface,
        )

# --- Workflow Tests (Testing T6.3 logic) ---

def test_run_debate_interaction_success(
    mock_question_agent, mock_answer_agent_factory, mock_llm_interface, mock_open
):
    """Tests the basic successful workflow using placeholder synthesis/write."""
    mock_aa1 = mock_answer_agent_factory("AA1")
    mock_aa2 = mock_answer_agent_factory("AA2")
    orchestrator = OrchestratorV2(
        question_agent=mock_question_agent,
        answer_agents=[mock_aa1, mock_aa2],
        output_file_path=FAKE_OUTPUT,
        llm_interface=mock_llm_interface,
    )

    # Patch the internal methods we aren't testing yet
    with patch.object(orchestrator, '_synthesize_final_answer', return_value="Synth Final Answer") as mock_synth, patch.object(orchestrator, '_write_output') as mock_write:

        # Consume the generator to execute the interaction
        results = list(orchestrator.run_debate_interaction(FAKE_Q_DOC, [FAKE_ANSWER_DOC_1, FAKE_ANSWER_DOC_2]))

        # 1. Check QA call
        mock_question_agent.generate_questions.assert_called_once_with(FAKE_Q_DOC, 5) # Default num q

        # 2. Check AA calls (for each question)
        questions = mock_question_agent.generate_questions.return_value
        assert mock_aa1.ask_question.call_count == len(questions)
        assert mock_aa2.ask_question.call_count == len(questions)
        if questions: # Check last call if questions were generated
            # Expect call with question AND the corresponding doc path
            mock_aa1.ask_question.assert_called_with(questions[-1], FAKE_ANSWER_DOC_1)
            mock_aa2.ask_question.assert_called_with(questions[-1], FAKE_ANSWER_DOC_2)

        # 3. Check synthesis calls
        assert mock_synth.call_count == len(questions)
        expected_synth_calls = [
            call(q, [mock_aa1.ask_question.return_value, mock_aa2.ask_question.return_value])
            for q in questions
        ]
        mock_synth.assert_has_calls(expected_synth_calls)

        # 4. Check write calls
        assert mock_write.call_count == len(questions)
        expected_write_calls = [
            call(q, mock_synth.return_value) for q in questions
        ]
        mock_write.assert_has_calls(expected_write_calls)

        # 5. Check file opening and initial write
        mock_open.assert_called_once_with(FAKE_OUTPUT, "w", encoding="utf-8")
        mock_file_handle = mock_open.return_value.__enter__.return_value
        expected_header = f"# Multi-Agent Debate Log for {os.path.basename(FAKE_Q_DOC)}\n\n"
        mock_file_handle.write.assert_called_once_with(expected_header)

def test_run_debate_no_initial_questions(
    mock_question_agent, mock_answer_agent_factory, mock_llm_interface, mock_open
):
    """Tests behavior when QuestionAgent returns no questions."""
    mock_question_agent.generate_questions.return_value = []
    mock_aa1 = mock_answer_agent_factory("AA1")
    orchestrator = OrchestratorV2(
        question_agent=mock_question_agent,
        answer_agents=[mock_aa1],
        output_file_path=FAKE_OUTPUT,
        llm_interface=mock_llm_interface,
    )
    with patch.object(orchestrator, '_synthesize_final_answer') as mock_synth, patch.object(orchestrator, '_write_output') as mock_write:

        results = list(orchestrator.run_debate_interaction(FAKE_Q_DOC, [FAKE_ANSWER_DOC_1]))

        mock_question_agent.generate_questions.assert_called_once()
        mock_aa1.ask_question.assert_not_called()
        mock_synth.assert_not_called()
        mock_write.assert_not_called()
        mock_open.assert_not_called() # Should not try to open output if no questions

def test_run_debate_question_agent_error(
    mock_question_agent, mock_answer_agent_factory, mock_llm_interface, mock_open
):
    """Tests behavior when QuestionAgent raises an error."""
    mock_question_agent.generate_questions.side_effect = Exception("QA Failed")
    mock_aa1 = mock_answer_agent_factory("AA1")
    orchestrator = OrchestratorV2(
        question_agent=mock_question_agent,
        answer_agents=[mock_aa1],
        output_file_path=FAKE_OUTPUT,
        llm_interface=mock_llm_interface,
    )
    with patch.object(orchestrator, '_synthesize_final_answer') as mock_synth, patch.object(orchestrator, '_write_output') as mock_write:

        results = list(orchestrator.run_debate_interaction(FAKE_Q_DOC, [FAKE_ANSWER_DOC_1]))

        mock_question_agent.generate_questions.assert_called_once()
        mock_aa1.ask_question.assert_not_called()
        mock_synth.assert_not_called()
        mock_write.assert_not_called()
        mock_open.assert_not_called()

def test_run_debate_answer_agent_error(
    mock_question_agent, mock_answer_agent_factory, mock_llm_interface, mock_open
):
    """Tests behavior when one AnswerAgent raises a generic error."""
    mock_aa1 = mock_answer_agent_factory("AA1")
    mock_aa2 = mock_answer_agent_factory("AA2")
    mock_aa2.ask_question.side_effect = Exception("AA2 Failed")
    orchestrator = OrchestratorV2(
        question_agent=mock_question_agent,
        answer_agents=[mock_aa1, mock_aa2],
        output_file_path=FAKE_OUTPUT,
        llm_interface=mock_llm_interface,
    )
    with patch.object(orchestrator, '_synthesize_final_answer', return_value="Synth Final Answer") as mock_synth, patch.object(orchestrator, '_write_output') as mock_write:

        results = list(orchestrator.run_debate_interaction(FAKE_Q_DOC, [FAKE_ANSWER_DOC_1, FAKE_ANSWER_DOC_2]))

        questions = mock_question_agent.generate_questions.return_value
        assert mock_aa1.ask_question.call_count == len(questions)
        assert mock_aa2.ask_question.call_count == len(questions) # Still called

        # Check that synth is called with the error message for AA2
        expected_answers_q1 = [mock_aa1.ask_question.return_value, "Error: Answer Agent 2 failed to generate an answer."]
        expected_answers_q2 = [mock_aa1.ask_question.return_value, "Error: Answer Agent 2 failed to generate an answer."]
        mock_synth.assert_has_calls([
            call(questions[0], expected_answers_q1),
            call(questions[1], expected_answers_q2)
        ])
        mock_write.assert_called()

def test_run_debate_answer_agent_context_error(
    mock_question_agent, mock_answer_agent_factory, mock_llm_interface, mock_open
):
    """Tests behavior when one AnswerAgent raises ContextLengthError."""
    mock_aa1 = mock_answer_agent_factory("AA1")
    mock_aa2 = mock_answer_agent_factory("AA2")
    mock_aa2.ask_question.side_effect = ContextLengthError("Too long")
    orchestrator = OrchestratorV2(
        question_agent=mock_question_agent,
        answer_agents=[mock_aa1, mock_aa2],
        output_file_path=FAKE_OUTPUT,
        llm_interface=mock_llm_interface,
    )
    with patch.object(orchestrator, '_synthesize_final_answer', return_value="Synth Final Answer") as mock_synth, patch.object(orchestrator, '_write_output') as mock_write:

        results = list(orchestrator.run_debate_interaction(FAKE_Q_DOC, [FAKE_ANSWER_DOC_1, FAKE_ANSWER_DOC_2]))

        questions = mock_question_agent.generate_questions.return_value
        # Check that synth is called with the specific context error message for AA2
        expected_answers_q1 = [mock_aa1.ask_question.return_value, "Error: Context Length Error for Answer Agent 2."]
        expected_answers_q2 = [mock_aa1.ask_question.return_value, "Error: Context Length Error for Answer Agent 2."]
        mock_synth.assert_has_calls([
            call(questions[0], expected_answers_q1),
            call(questions[1], expected_answers_q2)
        ])
        mock_write.assert_called()

def test_run_debate_all_answer_agents_fail(
    mock_question_agent, mock_answer_agent_factory, mock_llm_interface, mock_open
):
    """Tests behavior when all answer agents fail for a question."""
    mock_aa1 = mock_answer_agent_factory("AA1")
    mock_aa2 = mock_answer_agent_factory("AA2")
    mock_aa1.ask_question.side_effect = Exception("AA1 Failed")
    mock_aa2.ask_question.side_effect = ContextLengthError("AA2 Too Long")
    orchestrator = OrchestratorV2(
        question_agent=mock_question_agent,
        answer_agents=[mock_aa1, mock_aa2],
        output_file_path=FAKE_OUTPUT,
        llm_interface=mock_llm_interface,
    )
    with patch.object(orchestrator, '_synthesize_final_answer') as mock_synth, patch.object(orchestrator, '_write_output') as mock_write:

        results = list(orchestrator.run_debate_interaction(FAKE_Q_DOC, [FAKE_ANSWER_DOC_1, FAKE_ANSWER_DOC_2]))

        questions = mock_question_agent.generate_questions.return_value
        mock_synth.assert_not_called() # Synthesis should be skipped

        # Write should be called with an error message
        expected_write_calls = [
            call(q, "Error: No valid answers obtained from agents.") for q in questions
        ]
        mock_write.assert_has_calls(expected_write_calls) 

# --- Tests for Internal Methods ---

def test_synthesize_final_answer_success(
    mock_question_agent, mock_answer_agent_factory, mock_llm_interface
):
    """Tests the _synthesize_final_answer method calls the LLM correctly."""
    mock_aa1 = mock_answer_agent_factory("AA1")
    orchestrator = OrchestratorV2(
        question_agent=mock_question_agent,
        answer_agents=[mock_aa1], # Only need one for this test
        output_file_path=FAKE_OUTPUT,
        llm_interface=mock_llm_interface,
    )

    question = "Test Q?"
    answers = ["Ans 1", "Ans 2 from AA2", "Error: Agent 3 failed..."]
    expected_response = "Synthesized Ans"
    mock_llm_interface.generate_response.return_value = expected_response

    result = orchestrator._synthesize_final_answer(question, answers)

    assert result == expected_response
    mock_llm_interface.generate_response.assert_called_once()
    # Check that the prompt passed to the LLM is constructed correctly
    call_args, call_kwargs = mock_llm_interface.generate_response.call_args
    assert 'prompt' in call_kwargs
    prompt_arg = call_kwargs['prompt']

    assert f'The original question was:\n"{question}' in prompt_arg
    assert f'Here are the answers provided by {len(answers)} different agents:' in prompt_arg
    assert "--- Agent 1 Answer ---\nAns 1\n--- END Agent 1 Answer ---" in prompt_arg
    assert "--- Agent 2 Answer ---\nAns 2 from AA2\n--- END Agent 2 Answer ---" in prompt_arg
    assert "--- Agent 3 Answer ---\nError: Agent 3 failed...\n--- END Agent 3 Answer ---" in prompt_arg
    assert "--- Final Synthesized Answer ---" in prompt_arg

def test_synthesize_final_answer_llm_error(
    mock_question_agent, mock_answer_agent_factory, mock_llm_interface
):
    """Tests that _synthesize_final_answer raises error if LLM fails."""
    mock_llm_interface.generate_response.side_effect = Exception("LLM Boom")
    mock_aa1 = mock_answer_agent_factory("AA1")
    orchestrator = OrchestratorV2(
        question_agent=mock_question_agent,
        answer_agents=[mock_aa1],
        output_file_path=FAKE_OUTPUT,
        llm_interface=mock_llm_interface,
    )

    with pytest.raises(RuntimeError, match="LLM synthesis failed: LLM Boom"):
        orchestrator._synthesize_final_answer("Test Q?", ["Ans 1"])

def test_synthesize_final_answer_llm_empty(
    mock_question_agent, mock_answer_agent_factory, mock_llm_interface
):
    """Tests that _synthesize_final_answer returns error string if LLM returns empty."""
    mock_llm_interface.generate_response.return_value = "" # Empty response
    mock_aa1 = mock_answer_agent_factory("AA1")
    orchestrator = OrchestratorV2(
        question_agent=mock_question_agent,
        answer_agents=[mock_aa1],
        output_file_path=FAKE_OUTPUT,
        llm_interface=mock_llm_interface,
    )

    result = orchestrator._synthesize_final_answer("Test Q?", ["Ans 1"])
    assert result == "Error: Failed to get synthesized answer from LLM."

def test_write_output_success(mock_open):
    """Tests the _write_output method successfully writes to file."""
    # Need a dummy orchestrator just to call the method
    orchestrator = OrchestratorV2(MagicMock(), [MagicMock()], FAKE_OUTPUT, MagicMock())

    question = "Q for output?"
    final_answer = "Final Answer for output."

    orchestrator._write_output(question, final_answer)

    mock_open.assert_called_once_with(FAKE_OUTPUT, "a", encoding="utf-8")
    mock_file_handle = mock_open.return_value.__enter__.return_value
    expected_calls = [
        call(f"## Question:\n{question}\n\n"),
        call(f"### Final Answer:\n{final_answer}\n\n"),
        call("---\n\n")
    ]
    mock_file_handle.write.assert_has_calls(expected_calls)

def test_write_output_io_error(mock_open):
    """Tests that _write_output handles IOError gracefully."""
    mock_open.side_effect = IOError("Disk full")
    orchestrator = OrchestratorV2(MagicMock(), [MagicMock()], FAKE_OUTPUT, MagicMock())

    # We just check that it doesn't raise an exception, error is printed (captured stdout)
    # We could also patch print to assert the error message.
    try:
        orchestrator._write_output("Q?", "Final Ans")
    except Exception as e:
        pytest.fail(f"_write_output raised unexpected exception: {e}") 