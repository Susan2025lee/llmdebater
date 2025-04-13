import logging
import os
from typing import Optional, Dict, Any

from .llm_interface import LLMInterface
from .prompts import ANSWER_PROMPT_TEMPLATE
from src.utils.token_utils import estimate_token_count
from src.utils.file_handler import read_text_file # Assuming this function exists

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# --- Constants --- # 
MODEL_NAME = "gpt-o3-mini"
# Assuming 128k token limit for gpt-o3-mini (input + output)
CONTEXT_LIMIT = 128 * 1024
# Reserve tokens for the answer to prevent exceeding limit on output
ANSWER_BUFFER = 4 * 1024
MAX_INPUT_TOKENS = CONTEXT_LIMIT - ANSWER_BUFFER

# --- Custom Error --- #
class ContextLengthError(ValueError):
    "Custom exception for cases where the prompt exceeds the context limit."
    pass

# --- Core Agent Logic --- #
class ReportQAAgent:
    def __init__(self, llm_config: Optional[Dict[str, Any]] = None):
        """
        Initializes the ReportQAAgent.

        Args:
            llm_config: **Deprecated/Ignored**. Configuration is handled by LLMInterface itself.
                        Kept for potential future use but currently ignored.
        """
        # Initialize the LLM interface, specifying the model key.
        # LLMInterface is expected to handle loading config (API keys, proxy) internally.
        try:
            self.llm_interface = LLMInterface(model_key=MODEL_NAME)
            logger.info(f"ReportQAAgent initialized for model: {MODEL_NAME}")
        except Exception as e:
             logger.error(f"Failed to initialize LLMInterface for model {MODEL_NAME}: {e}", exc_info=True)
             # Decide how to handle initialization failure: re-raise, exit, or set a failed state.
             raise RuntimeError(f"Could not initialize LLMInterface: {e}")

    def _process_query_with_content(
        self, query: str, report_content: str
    ) -> str:
        """
        Internal helper: format prompt, check tokens, call LLM.
        Raises ContextLengthError, RuntimeError.
        """
        # 1. Format the Prompt
        prompt = ANSWER_PROMPT_TEMPLATE.format(report_content=report_content, user_query=query)

        # 2. Estimate Token Count and Check Limit
        estimated_tokens = estimate_token_count(prompt, model_name=MODEL_NAME)
        if estimated_tokens == -1:
            # This indicates an error in the estimation function itself
            logger.error("Token estimation failed. Cannot proceed.")
            raise ValueError("Token estimation failed.") # Raise error, don't return string
        
        logger.info(f"Estimated prompt token count for query: {estimated_tokens}")
        if estimated_tokens > MAX_INPUT_TOKENS:
            error_msg = (
                f"Input (report + query) exceeds the maximum allowed tokens "
                f"({estimated_tokens} > {MAX_INPUT_TOKENS}). This query cannot be processed."
            )
            logger.error(error_msg)
            raise ContextLengthError(error_msg)

        # 3. Call LLM via Interface
        try:
            logger.info("Sending request to LLM...")
            messages = [{"role": "user", "content": prompt}]
            llm_response = self.llm_interface.generate_chat_response(messages)
            
            if not llm_response or not isinstance(llm_response, str):
                 logger.error(f"Received invalid response from LLM: {llm_response}")
                 # Raise an error instead of returning string for better handling
                 raise ValueError("Received invalid response from the language model.")

            logger.info("Received response from LLM.")
            return llm_response.strip()
        
        except Exception as e:
            # Catch LLMInterface errors or other issues during the call
            logger.error(f"Error during LLM communication: {e}", exc_info=True)
            # Re-raise as a runtime error for the caller
            raise RuntimeError(f"Error getting response from language model: {e}")

    def ask_with_content(self, query: str, report_content: str) -> str:
        """
        Asks a question using pre-loaded report content.
        Handles exceptions from _process_query_with_content and returns error strings.

        Args:
            query: The user's question.
            report_content: The full text content of the report.

        Returns:
            The answer string from the LLM or a user-friendly error message.
        """
        if not report_content:
            return "Error: Report content is empty."
        if not query:
            return "Error: Query cannot be empty."
            
        try:
            # Call the internal processing method
            return self._process_query_with_content(query, report_content)
        except ContextLengthError as e:
            # Return the specific context error message
            return str(e) 
        except (RuntimeError, ValueError) as e:
            # Return other processing/LLM errors as strings
            return str(e)
        except Exception as e:
            # Catch any other unexpected errors
            logger.error(f"Unexpected error in ask_with_content: {e}", exc_info=True)
            return f"Error: An unexpected error occurred processing the query: {e}"

    def ask_question(self, query: str, report_path: str) -> str:
        """
        Reads a report file and asks a question using its content.
        Propagates exceptions from file reading.

        Args:
            query: The user's question.
            report_path: The path to the report file (.txt, .md).

        Returns:
            The answer string from the LLM or a user-friendly error message.

        Raises:
            FileNotFoundError: If the report_path does not exist.
            IOError: If there's an error reading the file.
            ValueError: If the report file is empty.
        """
        logger.info(f"Processing query for report file: {report_path}")
        report_content = ""
        try:
            report_content = read_text_file(report_path)
            if not report_content:
                logger.error(f"Report file is empty: {report_path}")
                raise ValueError(f"Report file is empty: {report_path}")
        except FileNotFoundError:
            logger.error(f"Report file not found: {report_path}")
            raise # Propagate file not found
        except Exception as e:
            logger.error(f"Error reading report file {report_path}: {e}", exc_info=True)
            # Raise IOError for file read issues
            raise IOError(f"Could not read report file {report_path}: {e}")

        # Delegate to the method that uses content.
        # ask_with_content handles its own errors (ContextLength, LLM) 
        # and returns strings for them.
        return self.ask_with_content(query, report_content)

# --- Example Usage --- #
if __name__ == '__main__':
    # This is a placeholder for basic testing.
    # Replace with actual paths and potentially load config from elsewhere.
    
    # Create a dummy report file for testing
    DUMMY_REPORT_PATH = "dummy_report.txt"
    try:
        with open(DUMMY_REPORT_PATH, "w") as f:
            f.write("This is the financial report for ACME Corp Q1 2024.\n")
            f.write("Revenue was $10M, showing a 5% increase year-over-year.\n")
            f.write("Net income was $1M.\n")
            f.write("The main risk identified is supply chain disruption.")
        
        print(f"Created dummy report: {DUMMY_REPORT_PATH}")
        
        # Initialize the agent (assuming LLMInterface handles config internally or via env vars)
        agent = ReportQAAgent()
        
        # --- Test Case 1: Valid query ---
        query1 = "What was the revenue?"
        print(f"\nAsking: {query1}")
        try:
            answer1 = agent.ask_question(query1, DUMMY_REPORT_PATH)
            print(f"Answer: {answer1}")
        except Exception as e:
            print(f"Error: {e}")

        # --- Test Case 2: Query about info not in report ---
        query2 = "What is the CEO's name?"
        print(f"\nAsking: {query2}")
        try:
            answer2 = agent.ask_question(query2, DUMMY_REPORT_PATH)
            print(f"Answer: {answer2}")
        except Exception as e:
            print(f"Error: {e}")
            
        # --- Test Case 3: Non-existent file ---
        query3 = "Any question?"
        print(f"\nAsking about non-existent file:")
        try:
            answer3 = agent.ask_question(query3, "non_existent_report.txt")
            print(f"Answer: {answer3}")
        except FileNotFoundError as e:
            print(f"Caught expected error: {e}")
        except Exception as e:
            print(f"Caught unexpected error: {e}")

        # --- Test Case 4: (Simulated) Context Length Error ---
        # To properly test this, you'd need a large file and potentially adjust MAX_INPUT_TOKENS
        # Or mock estimate_token_count
        print(f"\nSimulating context length check (requires large file or mocking to fail):")
        # Assuming the dummy report is very small, this won't fail unless limit is tiny
        try:
            # To force a failure for demo, temporarily set a low limit for the check:
            original_max = MAX_INPUT_TOKENS
            MAX_INPUT_TOKENS = 10 # Temporarily set very low limit
            print(f"Temporarily setting MAX_INPUT_TOKENS to {MAX_INPUT_TOKENS} for test")
            agent.ask_question("Any question?", DUMMY_REPORT_PATH)
            MAX_INPUT_TOKENS = original_max # Restore original limit
        except ContextLengthError as e:
            print(f"Caught expected ContextLengthError: {e}")
            MAX_INPUT_TOKENS = original_max # Restore original limit
        except Exception as e:
            print(f"Caught unexpected error: {e}")
            MAX_INPUT_TOKENS = original_max # Restore original limit
            
    finally:
        # Clean up dummy file
        if os.path.exists(DUMMY_REPORT_PATH):
            os.remove(DUMMY_REPORT_PATH)
            print(f"\nRemoved dummy report: {DUMMY_REPORT_PATH}") 