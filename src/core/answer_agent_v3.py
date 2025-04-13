import logging
import os # Added for ask_question
from typing import List, Tuple, Optional, Dict, Any

# Assuming these are needed and accessible
from .llm_interface import LLMInterface
# Import both V3 and V2 templates
from .prompts import DEBATE_PARTICIPATION_PROMPT_TEMPLATE, ANSWER_PROMPT_TEMPLATE 
from src.utils.token_utils import estimate_token_count
from src.utils.file_handler import read_text_file # Added for ask_question
# Import constants/errors - potentially define V3 specific ones later
from .answer_agent import ContextLengthError, MAX_INPUT_TOKENS, MODEL_NAME 

logger = logging.getLogger(__name__)
# Basic config if running standalone, but relies on main app config
# logging.basicConfig(level=logging.INFO) 

# TODO: Define V3 specific context limits if different from V2/answer_agent
MAX_INPUT_TOKENS_V3 = MAX_INPUT_TOKENS 

class AnswerAgentV3:
    """
    Answer Agent capable of participating in multi-round debates (V3).
    Uses debate history and its own document context to formulate responses.
    """

    def __init__(self, llm_interface: LLMInterface):
        """
        Initializes the AnswerAgentV3 with a shared LLMInterface.
        """
        try:
            self.llm = llm_interface
            # Log the model name from the passed interface
            logger.info(f"AnswerAgentV3 initialized using shared LLMInterface for model: {self.llm.model_name}")
        except Exception as e:
            logger.error(f"Error during AnswerAgentV3 initialization with LLMInterface: {e}", exc_info=True)
            raise RuntimeError(f"Could not initialize AnswerAgentV3: {e}")

    def _format_debate_history(self, debate_history: List[Tuple[str, int, str]]) -> str:
        """Formats the debate history list into a string for the prompt."""
        if not debate_history:
            return "No debate history yet."
        
        formatted_history = ""
        for agent_name, round_num, response in debate_history:
            formatted_history += f"Round {round_num} - {agent_name}:\n{response}\n---\n"
        return formatted_history.strip()

    def participate_in_debate(
        self, 
        question: str, 
        debate_history: List[Tuple[str, int, str]], 
        document_content: str,
        current_round: int
    ) -> str:
        """
        Generates a response for the current debate round based on the question,
        history, and the agent's document context.

        Args:
            question: The original question being debated.
            debate_history: List of (agent_name, round_number, response_text) tuples.
            document_content: The content of the document assigned to this agent.
            current_round: The current debate round number (e.g., 1, 2...).

        Returns:
            The agent's response for the current round.

        Raises:
            ContextLengthError: If the combined prompt exceeds token limits.
            ValueError: For invalid inputs or token estimation failures.
            RuntimeError: For LLM communication errors.
        """
        logger.info(f"Agent participating in debate round {current_round} for question: {question[:50]}...")
        
        if not document_content:
             logger.error("Document content cannot be empty for debate participation.")
             raise ValueError("Document content cannot be empty.")
        if not question:
             logger.error("Original question cannot be empty.")
             raise ValueError("Original question cannot be empty.")

        # 1. Format History
        history_str = self._format_debate_history(debate_history)

        # 2. Format Prompt
        prompt = DEBATE_PARTICIPATION_PROMPT_TEMPLATE.format(
            question=question,
            document_context=document_content, # Ensure this is passed correctly
            debate_history=history_str,
            current_round=current_round
        )

        # 3. Estimate Tokens & Check Limit (using V3 constant)
        estimated_tokens = estimate_token_count(prompt, model_name=self.llm.model_name)
        if estimated_tokens == -1:
            logger.error("Token estimation failed for debate participation prompt.")
            raise ValueError("Token estimation failed.")

        logger.info(f"Estimated prompt token count for debate round {current_round}: {estimated_tokens}")
        
        if estimated_tokens > MAX_INPUT_TOKENS_V3:
            error_msg = (
                f"Input context ({estimated_tokens} tokens) exceeds the maximum allowed tokens "
                f"({MAX_INPUT_TOKENS_V3}) for debate round {current_round}. Cannot proceed."
            )
            logger.error(error_msg)
            raise ContextLengthError(error_msg)

        # 4. Call LLM
        try:
            logger.debug("Sending request to LLM for debate participation...")
            # Using generate_response as it's a single completion based on the prompt
            # If chat format is preferred, structure messages appropriately
            llm_response = self.llm.generate_response(prompt=prompt)

            if not llm_response or not isinstance(llm_response, str):
                 logger.error(f"Received invalid response from LLM during debate: {llm_response}")
                 raise ValueError("Received invalid response from the language model.")

            logger.info(f"Received debate participation response from LLM for round {current_round}.")
            return llm_response.strip()
        
        except Exception as e:
            logger.error(f"Error during LLM communication for debate participation (Round {current_round}): {e}", exc_info=True)
            raise RuntimeError(f"Error generating debate response via LLM: {e}")

    # --- Initial Question Answering Methods (Copied from ReportQAAgent for Round 0) ---
    def _process_query_with_content(
        self, query: str, report_content: str
    ) -> str:
        """
        Internal helper: format prompt, check tokens, call LLM (for initial answer).
        Raises ContextLengthError, RuntimeError.
        """
        # 1. Format the Prompt (Use V2/Standard Answer Prompt)
        prompt = ANSWER_PROMPT_TEMPLATE.format(report_content=report_content, user_query=query)

        # 2. Estimate Token Count and Check Limit (Use standard limits for initial answer)
        estimated_tokens = estimate_token_count(prompt, model_name=self.llm.model_name)
        if estimated_tokens == -1:
            logger.error("Token estimation failed for initial query. Cannot proceed.")
            raise ValueError("Token estimation failed.")
        
        logger.info(f"Estimated prompt token count for initial query: {estimated_tokens}")
        if estimated_tokens > MAX_INPUT_TOKENS:
            error_msg = (
                f"Input (report + query) exceeds the maximum allowed tokens "
                f"({estimated_tokens} > {MAX_INPUT_TOKENS}). Initial query cannot be processed."
            )
            logger.error(error_msg)
            raise ContextLengthError(error_msg)

        # 3. Call LLM via Interface
        try:
            logger.info("Sending request to LLM for initial answer...")
            # Assuming chat response is appropriate based on original agent
            messages = [{"role": "user", "content": prompt}]
            llm_response = self.llm.generate_chat_response(messages)
            
            if not llm_response or not isinstance(llm_response, str):
                 logger.error(f"Received invalid initial response from LLM: {llm_response}")
                 raise ValueError("Received invalid response from the language model.")

            logger.info("Received initial response from LLM.")
            return llm_response.strip()
        
        except Exception as e:
            logger.error(f"Error during LLM communication for initial answer: {e}", exc_info=True)
            raise RuntimeError(f"Error getting initial response from language model: {e}")

    def ask_with_content(self, query: str, report_content: str) -> str:
        """
        Asks a question using pre-loaded report content (for initial answer).
        Handles exceptions from _process_query_with_content and returns error strings.
        (Copied from ReportQAAgent)
        """
        if not report_content:
             logger.warning("Attempted to ask initial question with empty report content.")
             # Return error string consistent with original implementation
             return "Error: Report content is empty."
        if not query:
             logger.warning("Attempted to ask initial question with empty query.")
             return "Error: Query cannot be empty."
            
        try:
            # Call the internal processing method
            return self._process_query_with_content(query, report_content)
        except ContextLengthError as e:
            logger.warning(f"Context length error during initial answer generation: {e}")
            return str(e) # Return the specific context error message
        except (RuntimeError, ValueError) as e:
            logger.error(f"Runtime/Value error during initial answer generation: {e}")
            return str(e) # Return other processing/LLM errors as strings
        except Exception as e:
            logger.error(f"Unexpected error in ask_with_content: {e}", exc_info=True)
            return f"Error: An unexpected error occurred processing the initial query: {e}"

    def ask_question(self, query: str, report_path: str) -> str:
        """
        Reads a report file and asks a question using its content (for initial answer).
        Propagates exceptions from file reading.
        (Copied from ReportQAAgent)
        """
        logger.info(f"Processing initial query for report file: {report_path}")
        report_content = ""
        try:
            report_content = read_text_file(report_path)
            if not report_content:
                logger.error(f"Report file for initial answer is empty: {report_path}")
                # Raise error consistent with original implementation
                raise ValueError(f"Report file is empty: {report_path}")
        except FileNotFoundError:
            logger.error(f"Report file not found: {report_path}")
            raise # Propagate file not found
        except Exception as e:
            logger.error(f"Error reading report file {report_path}: {e}", exc_info=True)
            raise IOError(f"Could not read report file {report_path}: {e}")

        # Delegate to the method that uses content.
        return self.ask_with_content(query, report_content)

# Removed the TODO comment about ask_question

# TODO: Add ask_question method (for Round 0) - either by inheritance 
# from ReportQAAgent or by copying/adapting its implementation here.
# For now, OrchestratorV3 will need to handle Round 0 separately if 
# this agent doesn't inherit or implement ask_question. 