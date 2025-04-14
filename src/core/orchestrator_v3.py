import os
import logging
from typing import List, Dict, Any, Iterator, Tuple

# Core components for V3
from .llm_interface import LLMInterface
from .answer_agent_v3 import AnswerAgentV3, ContextLengthError # Use the V3 Answer Agent
from .question_agent import QuestionAgent
from .prompts import FINAL_SYNTHESIS_PROMPT_TEMPLATE_V3

logger = logging.getLogger(__name__)

# Placeholder names for speakers in the yielded output
# (Can be defined here or passed during initialization if needed)
SPEAKER_SYSTEM = "System"
SPEAKER_ORCHESTRATOR = "Orchestrator V3"
SPEAKER_QUESTION_AGENT = "Question Agent"
SPEAKER_ANSWER_AGENT = "Answer Agent V3"
SPEAKER_SYNTHESIZER = "Synthesizer"

class OrchestratorV3:
    """
    Orchestrates the V3 multi-round debate workflow:
    1. Generates initial questions.
    2. Manages multiple debate rounds where AnswerAgentV3 instances respond 
       based on history and their documents.
    3. Synthesizes a final answer based on the full debate history.
    4. Yields interaction steps for UI display.
    5. Writes final Q/A pairs to an output file.
    """

    def __init__(
        self,
        question_agent: QuestionAgent,
        answer_agents: List[AnswerAgentV3], # Expecting V3 agents
        output_file_path: str,
        llm_interface: LLMInterface, # For the final synthesis step
        num_initial_questions: int = 5,
        max_debate_rounds: int = 2, # New parameter for V3
    ):
        """
        Initializes the OrchestratorV3.

        Args:
            question_agent: An instance of QuestionAgent.
            answer_agents: A list of initialized AnswerAgentV3 instances.
            output_file_path: Path to the markdown file for storing results.
            llm_interface: An instance of LLMInterface for the final synthesis call.
            num_initial_questions: The number of initial questions to generate.
            max_debate_rounds: The maximum number of debate rounds (after initial answers).
        """
        if not answer_agents:
            raise ValueError("At least one AnswerAgentV3 must be provided.")
        if max_debate_rounds < 0:
             raise ValueError("Maximum debate rounds cannot be negative.")

        self.question_agent = question_agent
        self.answer_agents = answer_agents
        self.output_file_path = output_file_path
        self.llm = llm_interface
        self.num_initial_questions = num_initial_questions
        self.max_debate_rounds = max_debate_rounds # Store the new parameter

        logger.info(f"OrchestratorV3 initialized with {len(self.answer_agents)} Answer Agents. Max debate rounds: {self.max_debate_rounds}")

    # --- Main interaction method (Generator) ---
    def run_full_debate(
        self, 
        question_doc_path: str, 
        answer_doc_paths: List[str]
    ) -> Iterator[Tuple[str, str]]:
        """
        Runs the full multi-round debate workflow as a generator.

        Yields tuples of (speaker: str, message: str) compatible with V2 UI.
        Writes final Q/A results to the output file.

        Args:
            question_doc_path: Path to the document for the QuestionAgent.
            answer_doc_paths: A list of paths for the AnswerAgents (must match agent list).

        Yields:
            Tuples of (speaker: str, message: str) representing each step.
        """
        
        # --- T6.5.1: Initial Checks --- 
        yield SPEAKER_SYSTEM, f"Starting V3 multi-round debate for document: {os.path.basename(question_doc_path)}"
        
        if len(self.answer_agents) != len(answer_doc_paths):
            err_msg = f"Error: The number of Answer Agents ({len(self.answer_agents)}) does not match the number of answer document paths ({len(answer_doc_paths)}).";
            logger.error(err_msg)
            yield SPEAKER_SYSTEM, err_msg
            return # Stop the generator
            
        # --- T6.5.2: Generate Initial Questions --- 
        yield SPEAKER_ORCHESTRATOR, f"Generating {self.num_initial_questions} initial questions from {os.path.basename(question_doc_path)}..."
        initial_questions = []
        try:
            # Assuming QuestionAgent has a generate_questions method similar to V2
            initial_questions = self.question_agent.generate_questions(
                question_doc_path, self.num_initial_questions
            )
            
            # Yield each question individually
            if initial_questions:
                yield SPEAKER_QUESTION_AGENT, f"Generated {len(initial_questions)} initial questions:"
                for q_idx, q in enumerate(initial_questions):
                    yield SPEAKER_QUESTION_AGENT, f"Question {q_idx+1}: {q}"
            else:
                 yield SPEAKER_QUESTION_AGENT, "Warning: No initial questions were generated."
                 logger.warning("Question Agent returned no initial questions.")
        except Exception as e:
            err_msg = f"Error generating initial questions: {e}"
            logger.error(err_msg, exc_info=True)
            yield SPEAKER_SYSTEM, err_msg
            return # Stop the generator if question generation fails

        # Exit if no questions were generated and we decide that's an error
        if not initial_questions:
             yield SPEAKER_SYSTEM, "No initial questions generated. Stopping workflow."
             return
             
        # --- T6.5.3: Initialize Output File ---
        try:
            # Use 'w' to overwrite/clear the file initially
            with open(self.output_file_path, "w", encoding="utf-8") as f:
                f.write(f"# Multi-Round Debate Log (V3) for {os.path.basename(question_doc_path)}\n")
                f.write(f"* Max Rounds: {self.max_debate_rounds}\n")
                f.write(f"* Answer Agents: {len(self.answer_agents)}\n\n")
            yield SPEAKER_SYSTEM, f"Initialized output log file: {self.output_file_path}"
        except IOError as e:
            err_msg = f"Error creating/accessing output file {self.output_file_path}: {e}. Cannot save results. Stopping workflow."
            logger.error(err_msg, exc_info=True)
            yield SPEAKER_SYSTEM, err_msg
            return # Stop the generator if output file fails
            
        # --- T6.5.4: Loop Through Initial Questions --- 
        final_results = [] # To potentially store final Q/A pairs if needed
        for i, question in enumerate(initial_questions):
            yield SPEAKER_ORCHESTRATOR, f"--- Processing Question {i+1}/{len(initial_questions)} ---"
            yield SPEAKER_QUESTION_AGENT, question # Yield the question itself
            
            # --- T6.5.5: Initialize Debate History --- 
            # History stores tuples of (agent_identifier, round_number, response_text)
            debate_history: List[Tuple[str, int, str]] = []
            
            # --- T6.5.6: Round 0 - Get Initial Answers --- 
            yield SPEAKER_ORCHESTRATOR, "--- Round 0: Gathering Initial Answers ---"
            initial_answers_current_q = [] # Temp storage for this question
            
            # Process each agent independently, yielding after each response
            for agent_idx, answer_agent in enumerate(self.answer_agents):
                agent_name = f"{SPEAKER_ANSWER_AGENT} {agent_idx + 1}" # e.g., "Answer Agent V3 1"
                doc_path = answer_doc_paths[agent_idx]
                doc_name = os.path.basename(doc_path)
                
                # Yield BEFORE getting answer
                yield SPEAKER_ORCHESTRATOR, f"Asking {agent_name} (using {doc_name})..."
                
                try:
                    # Use the ask_question method for the initial answer
                    answer = answer_agent.ask_question(question, doc_path)
                    initial_answers_current_q.append(answer) # Store raw answer
                    
                    # Add to history with round 0
                    history_entry = (agent_name, 0, answer)
                    debate_history.append(history_entry)
                    
                    # Yield formatted message for UI
                    yield agent_name, f"Initial Answer (R0): {answer}"
                except FileNotFoundError:
                    err_msg = f"Error for {agent_name}: Report file not found at {doc_path}"
                    logger.error(err_msg)
                    yield SPEAKER_SYSTEM, err_msg
                    debate_history.append((agent_name, 0, f"Error: File Not Found - {doc_name}"))
                except ContextLengthError as cle:
                    err_msg = f"Error for {agent_name} (R0): Context Length Error - {cle}"
                    logger.error(err_msg)
                    yield SPEAKER_SYSTEM, err_msg
                    debate_history.append((agent_name, 0, f"Error: Context Length Error - {doc_name}"))
                except Exception as e:
                    err_msg = f"Error getting initial answer from {agent_name}: {e}"
                    logger.error(err_msg, exc_info=True)
                    yield SPEAKER_SYSTEM, err_msg
                    debate_history.append((agent_name, 0, f"Error: Failed to generate initial answer - {doc_name}"))
            
            # --- T6.5.7: Debate Rounds Loop (1 to max_debate_rounds) --- 
            for round_num in range(1, self.max_debate_rounds + 1):
                yield SPEAKER_ORCHESTRATOR, f"--- Starting Debate Round {round_num}/{self.max_debate_rounds} ---"
                
                # Process each agent individually within the round
                for agent_idx, answer_agent in enumerate(self.answer_agents):
                    agent_name = f"{SPEAKER_ANSWER_AGENT} {agent_idx + 1}"
                    doc_path = answer_doc_paths[agent_idx]
                    doc_name = os.path.basename(doc_path)
                    
                    # Yield BEFORE getting response
                    yield SPEAKER_ORCHESTRATOR, f"Polling {agent_name} (using {doc_name}) for Round {round_num}..."
                    
                    # Need document content for participate_in_debate
                    try:
                        # Read document content for this agent - Caching could optimize this
                        with open(doc_path, 'r', encoding='utf-8') as f:
                            document_content = f.read()
                        if not document_content:
                             # Handle empty file, maybe skip agent for this round?
                             err_msg = f"Warning: Document file for {agent_name} ({doc_name}) is empty for round {round_num}. Skipping participation."
                             logger.warning(err_msg)
                             yield SPEAKER_SYSTEM, err_msg
                             debate_history.append((agent_name, round_num, "Error: Agent document was empty."))
                             continue # Skip to next agent
                             
                        # Call participate_in_debate
                        response = answer_agent.participate_in_debate(
                            question=question,
                            debate_history=debate_history, # Pass history accumulated so far
                            document_content=document_content,
                            current_round=round_num
                        )
                        
                        # Add response to history immediately
                        history_entry = (agent_name, round_num, response)
                        debate_history.append(history_entry)
                        
                        # Yield formatted message for UI
                        yield agent_name, f"Round {round_num}: {response}"
                        
                    except FileNotFoundError:
                        err_msg = f"Error for {agent_name}: Report file not found at {doc_path} during round {round_num}."
                        logger.error(err_msg)
                        yield SPEAKER_SYSTEM, err_msg
                        debate_history.append((agent_name, round_num, f"Error: File Not Found - {doc_name}"))
                    except ContextLengthError as cle:
                        err_msg = f"Error for {agent_name} (R{round_num}): Context Length Error - {cle}"
                        logger.error(err_msg)
                        yield SPEAKER_SYSTEM, err_msg
                        debate_history.append((agent_name, round_num, f"Error: Context Length Error - {doc_name}"))
                    except Exception as e:
                        err_msg = f"Error getting response from {agent_name} in round {round_num}: {e}"
                        logger.error(err_msg, exc_info=True)
                        yield SPEAKER_SYSTEM, err_msg
                        debate_history.append((agent_name, round_num, f"Error: Failed to generate response - {doc_name}"))
            
            # --- T6.5.8: Final Synthesis --- 
            yield SPEAKER_ORCHESTRATOR, f"--- Synthesizing Final Answer for Question {i+1} ---"
            
            final_answer_for_q = "Error: Failed to synthesize final answer." # Default error
            try:
                # Pass the full history to the synthesis method
                final_answer_for_q = self._synthesize_final_answer_v3(question, debate_history)
                yield SPEAKER_SYNTHESIZER, final_answer_for_q
                
                # Update the output file with this Q&A pair
                self._write_output(question, debate_history, final_answer_for_q)
                yield SPEAKER_SYSTEM, f"Results for Question {i+1} written to output file."
                
                # Add separator between questions
                if i < len(initial_questions) - 1:
                    yield SPEAKER_SYSTEM, "-------------------------------------------"
                
            except Exception as e:
                err_msg = f"Error during final synthesis or output writing: {e}"
                logger.error(err_msg, exc_info=True)
                yield SPEAKER_SYSTEM, err_msg
        
        # All questions processed
        yield SPEAKER_SYSTEM, f"Multi-round debate complete. Results saved to {self.output_file_path}"
        
    # --- Helper methods (e.g., for synthesis, output writing) will be added here --- 
    def _synthesize_final_answer_v3(self, question: str, debate_history: List[Tuple[str, int, str]]) -> str:
        """ Synthesizes a final answer using the full debate history. """
        logger.info(f"Synthesizing final answer for question: {question[:50]}...")

        # 1. Format History (reuse AnswerAgentV3's method temporarily, or duplicate)
        #    Ideally, this formatting logic could be in a shared utility.
        temp_agent = self.answer_agents[0] # Get an agent instance to access the method
        history_str = temp_agent._format_debate_history(debate_history) # Use existing formatter
        # Alternative: Duplicate formatting logic here
        # if not debate_history: history_str = "No debate history provided."
        # else: 
        #    formatted_history = ""
        #    for agent_name, round_num, response in debate_history:
        #        formatted_history += f"Round {round_num} - {agent_name}:\n{response}\n---\n"
        #    history_str = formatted_history.strip()

        # 2. Format Prompt
        prompt = FINAL_SYNTHESIS_PROMPT_TEMPLATE_V3.format(
            question=question,
            debate_history=history_str
        )

        # TODO: Add token check? Synthesis prompt could get very long.
        # estimated_tokens = estimate_token_count(prompt, model_name=self.llm.model_name)
        # if estimated_tokens > SOME_SYNTHESIS_LIMIT:
        #     logger.error("Synthesis prompt exceeds token limit.")
        #     raise ContextLengthError("Synthesis prompt exceeds token limit.")

        # 3. Call LLM
        try:
            logger.debug("Sending request to LLM for final synthesis...")
            final_answer = self.llm.generate_response(prompt=prompt)
            if not final_answer:
                logger.warning("LLM returned empty response for final synthesis.")
                return "Error: Failed to get synthesized answer from LLM."
            logger.info("Received synthesized final answer from LLM.")
            return final_answer.strip()
        except Exception as e:
            logger.error(f"Error during LLM call for final synthesis: {e}", exc_info=True)
            # Re-raise for the main loop to catch and yield error message
            raise RuntimeError(f"LLM final synthesis failed: {e}")
        
    def _write_output(self, question: str, debate_history: List[Tuple[str, int, str]], final_answer: str):
        """ Appends a question, its full debate history, and final answer to the output file. """
        # logger.debug(f"Writing output for question: {question[:50]}...")
        try:
            # Use 'a' mode to append
            with open(self.output_file_path, "a", encoding="utf-8") as f:
                f.write(f"## Question:\n{question}\n\n")
                
                # --- Write Debate History --- 
                f.write(f"### Debate History ({len(debate_history)} entries):\n\n")
                if not debate_history:
                    f.write("(No history recorded)\n\n")
                else:
                    # Group by round for better readability
                    rounds = {}
                    for agent_name, round_num, response in debate_history:
                        if round_num not in rounds:
                            rounds[round_num] = []
                        rounds[round_num].append((agent_name, response))
                        
                    for round_num in sorted(rounds.keys()):
                        f.write(f"\n#### Round {round_num}:\n\n")
                        for agent_name, response in rounds[round_num]:
                            f.write(f"> **{agent_name}:**\n\n")
                            # Indent response for clarity
                            indented_response = '\n'.join([f"> {line}" for line in response.split('\n')])
                            f.write(f"{indented_response}\n\n")
                            f.write(f">\n\n") # Add a small separator
                f.write("\n") # Space before final answer
                # --- End Debate History --- 
                
                f.write(f"### Final Answer (Synthesized V3):\n{final_answer}\n\n") # Added V3 marker
                f.write("---\n\n")
            # logger.debug(f"Successfully wrote V3 result to {self.output_file_path}")
        except IOError as e:
            # Log the error but allow the main loop to continue if possible
            logger.error(f"[OrchestratorV3 IO Error] Error writing to output file {self.output_file_path}: {e}")
            # Re-raise the error to be caught by the main loop's write handler
            raise 