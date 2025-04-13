import os
from typing import List, Dict, Any, Iterator, Tuple

from .llm_interface import LLMInterface
from .answer_agent import ReportQAAgent, ContextLengthError
from .question_agent import QuestionAgent
from .prompts import DEBATE_SYNTHESIS_PROMPT_TEMPLATE


class OrchestratorV2:
    """
    Orchestrates a multi-agent debate workflow:
    1. Gets initial questions from a QuestionAgent.
    2. For each question, gets answers from multiple AnswerAgents.
    3. Runs a debate/synthesis step using an LLM to produce a final answer.
    4. Writes the question and final answer pairs to an output file.
    """

    def __init__(
        self,
        question_agent: QuestionAgent,
        answer_agents: List[ReportQAAgent],
        output_file_path: str,
        llm_interface: LLMInterface, # For the debate/synthesis step
        num_initial_questions: int = 5,
    ):
        """
        Initializes the OrchestratorV2.

        Args:
            question_agent: An instance of QuestionAgent.
            answer_agents: A list of initialized ReportQAAgent instances.
            output_file_path: Path to the markdown file for storing results.
            llm_interface: An instance of LLMInterface for the debate/synthesis call.
            num_initial_questions: The number of initial questions to generate.
        """
        if not answer_agents:
            raise ValueError("At least one ReportQAAgent must be provided.")

        self.question_agent = question_agent
        self.answer_agents = answer_agents
        self.output_file_path = output_file_path
        self.llm = llm_interface
        self.num_initial_questions = num_initial_questions

        # Initial messages will be yielded by the generator
        # print(f"OrchestratorV2 initialized with {len(self.answer_agents)} Answer Agents.")
        # print(f"Output log file: {self.output_file_path}")

    # --- Main interaction method (NOW A GENERATOR) ---
    def run_debate_interaction(self, question_doc_path: str, answer_doc_paths: List[str]) -> Iterator[Tuple[str, str]]:
        """
        Runs the full multi-agent debate workflow as a generator, yielding messages.
        Writes results to the output file.

        Args:
            question_doc_path: Path to the document for the QuestionAgent.
            answer_doc_paths: A list of paths for the AnswerAgents.

        Yields:
            Tuples of (speaker: str, message: str) representing each step.

        Returns:
            None. (Final results are implicitly logged to file or managed by caller)
        """
        yield "System", f"Starting V2 debate interaction for document: {os.path.basename(question_doc_path)}"

        if len(self.answer_agents) != len(answer_doc_paths):
            err_msg = "Error: The number of answer agents and answer document paths must match."
            yield "System", err_msg
            return # Stop generation

        # 1. Get initial questions
        yield "Orchestrator", f"Generating {self.num_initial_questions} questions from {os.path.basename(question_doc_path)}..."
        initial_questions = []
        try:
            initial_questions = self.question_agent.generate_questions(
                question_doc_path, self.num_initial_questions
            )
            if initial_questions:
                questions_list_str = "\n".join([f"- {q}" for q in initial_questions])
                yield "Question Agent", f"Generated {len(initial_questions)} initial questions:\n{questions_list_str}"
            else:
                 yield "Question Agent", "No initial questions were generated."
        except Exception as e:
            err_msg = f"Error generating initial questions: {e}"
            yield "System", err_msg
            return # Stop generation

        if not initial_questions:
            yield "System", "No initial questions generated. Exiting."
            return # Stop generation

        # Initialize output file (clear or add header)
        try:
            with open(self.output_file_path, "w", encoding="utf-8") as f:
                f.write(f"# Multi-Agent Debate Log for {os.path.basename(question_doc_path)}\n\n")
            yield "System", f"Initialized output log file: {self.output_file_path}"
        except IOError as e:
            err_msg = f"Error creating/accessing output file {self.output_file_path}: {e}. Exiting."
            yield "System", err_msg
            return # Stop generation

        # 2. Loop through each initial question
        for i, question in enumerate(initial_questions):
            yield "Orchestrator", f"--- Processing Question {i+1}/{len(initial_questions)} ---\n{question}"
            current_answers = []

            # 3. Get answers from all AnswerAgents
            for agent_idx, answer_agent in enumerate(self.answer_agents):
                agent_name = f"Answer Agent {agent_idx + 1}"
                doc_name = os.path.basename(answer_doc_paths[agent_idx])
                yield "Orchestrator", f"Asking {agent_name} (using {doc_name})..."
                try:
                    answer = answer_agent.ask_question(question, answer_doc_paths[agent_idx])
                    current_answers.append(answer)
                    yield agent_name, answer
                except FileNotFoundError:
                    err_msg = f"Error for {agent_name}: Report file not found at {answer_doc_paths[agent_idx]}"
                    yield "System", err_msg
                    current_answers.append(f"Error: Report file not found for {agent_name}.")
                except ContextLengthError as cle:
                    err_msg = f"Error for {agent_name}: Context Length Error - {cle}"
                    yield "System", err_msg
                    current_answers.append(f"Error: Context Length Error for {agent_name}.")
                except Exception as e:
                    err_msg = f"Error getting answer from {agent_name}: {e}"
                    yield "System", err_msg
                    current_answers.append(f"Error: {agent_name} failed to generate an answer.")

            if not current_answers or all("Error:" in ans for ans in current_answers):
                yield "Orchestrator", "No valid answers received from any agent for this question. Skipping synthesis."
                final_answer = "Error: No valid answers obtained from agents."
                self._write_output(question, final_answer)
                # No need to store results log here, caller manages display
                continue # Move to the next question

            # 4. Synthesize final answer
            yield "Orchestrator", f"Synthesizing final answer for Question {i+1}..."
            final_answer = "Error: Failed to synthesize final answer." # Default error
            try:
                final_answer = self._synthesize_final_answer(question, current_answers)
                yield "Synthesizer", final_answer # Report final synthesized answer
            except Exception as e:
                err_msg = f"Error during final answer synthesis: {e}"
                yield "System", err_msg
                # final_answer remains the default error message

            # 5. Write output to file
            self._write_output(question, final_answer)

            # 6. Loop continues for next question

        yield "System", "Debate interaction finished."
        # Generator implicitly returns None when done

    # --- Debate/synthesis method ---
    def _synthesize_final_answer(self, question: str, answers: List[str]) -> str:
        """
        Uses the LLM to synthesize a final answer from multiple agent answers.

        Args:
            question: The original question.
            answers: A list of answers from the different AnswerAgents.

        Returns:
            The synthesized final answer.
        """
        # print(f"Synthesizing final answer for: {question}") # Replaced by callback in calling function

        # Construct the list of answers string
        answers_str = ""
        for i, ans in enumerate(answers):
            answers_str += f"--- Agent {i+1} Answer ---\n{ans}\n--- END Agent {i+1} Answer ---\n\n"

        # Format the imported prompt
        formatted_prompt = DEBATE_SYNTHESIS_PROMPT_TEMPLATE.format(
            question=question,
            len_answers=len(answers),
            answers_str=answers_str.strip() # Strip here before formatting
        )

        # TODO: Add token check/truncation for the prompt if needed
        # estimated_tokens = estimate_token_count(debate_prompt, model_name=self.llm.model_key) # Needs model_key access
        # if estimated_tokens > SOME_LIMIT:
        #    handle truncation or raise error

        try:
            # Use generate_response as it's a single completion task
            final_answer = self.llm.generate_response(prompt=formatted_prompt)
            if not final_answer:
                # Send error via callback? No, let the main loop handle it.
                # print("Warning: LLM returned empty response for synthesis.")
                return "Error: Failed to get synthesized answer from LLM."
            return final_answer.strip()
        except Exception as e:
            # Error will be caught and sent via callback in the main loop
            # print(f"Error during LLM call for synthesis: {e}")
            raise RuntimeError(f"LLM synthesis failed: {e}")

    # --- Output writing ---
    def _write_output(self, question: str, final_answer: str):
        """
        Appends a question and its final answer to the output file.

        Args:
            question: The original question.
            final_answer: The synthesized final answer.
        """
        # print(f"Writing output for question: {question[:50]}...") # Removed, less noisy
        try:
            # Use 'a' mode to append
            with open(self.output_file_path, "a", encoding="utf-8") as f:
                f.write(f"## Question:\n{question}\n\n")
                f.write(f"### Final Answer:\n{final_answer}\n\n")
                f.write("---\n\n")
            # print(f"Successfully wrote to {self.output_file_path}") # Optional: success log
        except IOError as e:
            # Log the error but allow the main loop to continue if possible
            print(f"[OrchestratorV2 IO Error] Error writing to output file {self.output_file_path}: {e}") 