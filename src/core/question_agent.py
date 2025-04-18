# Placeholder for QuestionAgent implementation

import logging
import os
from typing import List, Optional
import re # Import regex for better parsing

# Assuming utils and LLMInterface are accessible
from .llm_interface import LLMInterface
# Import the prompt from the new module
from .prompts import QUESTION_PROMPT_TEMPLATE
from src.utils.token_utils import estimate_token_count
from src.utils.file_handler import read_text_file
from .answer_agent import ContextLengthError, MAX_INPUT_TOKENS, MODEL_NAME # Reusing constants

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class QuestionAgent:
    """Generates relevant questions about a given document content."""

    def __init__(self, llm_interface: LLMInterface):
        """Initializes the QuestionAgent with a shared LLMInterface."""
        try:
            # Store the passed LLMInterface
            self.llm = llm_interface
            # Log the model name from the passed interface (use .model_name)
            logger.info(f"QuestionAgent initialized using shared LLMInterface for model: {self.llm.model_name}")
        except Exception as e:
            # This error is less likely now as init is simpler, but keep for safety
            logger.error(f"Error during QuestionAgent initialization with LLMInterface: {e}", exc_info=True)
            raise RuntimeError(f"Could not initialize QuestionAgent: {e}")

    def _generate_questions_from_llm(self, prompt: str) -> str:
        """Internal helper to call the LLM and get the raw response."""
        try:
            logger.info("Sending request to LLM for question generation...")
            messages = [{"role": "user", "content": prompt}]
            # Use the shared self.llm interface
            llm_response = self.llm.generate_chat_response(messages)

            if not llm_response or not isinstance(llm_response, str):
                 logger.error(f"Received invalid response from LLM: {llm_response}")
                 raise ValueError("Received invalid response from the language model.")

            logger.info("Received question generation response from LLM.")
            return llm_response.strip()
        
        except Exception as e:
            logger.error(f"Error during LLM communication for question generation: {e}", exc_info=True)
            raise RuntimeError(f"Error generating questions via LLM: {e}")

    def _parse_questions(self, raw_output: str) -> List[str]:
        """Parses the raw LLM output string into a list of questions."""
        questions = []
        # Split by newline
        lines = raw_output.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Try to remove potential numbering (e.g., "1. ", "1) ", "- ")
            # Regex to match common list markers at the start of the string
            cleaned_line = re.sub(r"^\s*\d+[\.\)]\s*|^\s*[-*+]\s*", "", line).strip()
            if cleaned_line:
                questions.append(cleaned_line)
        
        if not questions and raw_output: # Handle case where parsing fails but got output
             logger.warning(f"Could not parse questions from LLM output. Output was: {raw_output}")
             # Fallback: return the raw output as a single question element
             return [raw_output]
        elif not questions:
             logger.warning("LLM output was empty or parsing resulted in no questions.")
        
        return questions

    def generate_questions_from_content(
        self, document_content: str, num_questions: int = 5
    ) -> List[str]: # Return type will be list after parsing (T2.7)
        """
        Generates questions based on the provided document content.

        Args:
            document_content: The full text content of the document.
            num_questions: The desired number of questions to generate.

        Returns:
            A list of generated questions (or potentially raw string before parsing).
            Returns an empty list or raises error on failure.

        Raises:
            ContextLengthError: If the document content and prompt exceed context limit.
            ValueError: If document content is empty or token estimation fails.
            RuntimeError: If LLM communication fails.
        """
        if not document_content:
            logger.error("Document content cannot be empty.")
            raise ValueError("Document content cannot be empty.")

        # 1. Format Prompt
        prompt = QUESTION_PROMPT_TEMPLATE.format(
            num_questions=num_questions,
            document_content=document_content
        )

        # 2. Estimate Tokens & Check Limit
        # Use the model name from the LLM interface
        estimated_tokens = estimate_token_count(prompt, model_name=self.llm.model_name)
        if estimated_tokens == -1:
            logger.error("Token estimation failed for question generation prompt.")
            raise ValueError("Token estimation failed.")

        logger.info(f"Estimated prompt token count for question generation: {estimated_tokens}")
        # Use MAX_INPUT_TOKENS from the interface/config if available, otherwise use imported constant
        # Assuming MAX_INPUT_TOKENS constant is okay for now, but ideally read from config
        if estimated_tokens > MAX_INPUT_TOKENS:
            error_msg = (
                f"Input document ({estimated_tokens} tokens) exceeds the maximum allowed tokens "
                f"({MAX_INPUT_TOKENS}) for question generation."
            )
            logger.error(error_msg)
            raise ContextLengthError(error_msg)

        # 3. Call LLM (Internal Helper)
        try:
            raw_llm_output = self._generate_questions_from_llm(prompt)
        except (RuntimeError, ValueError) as e:
            # Handle errors from LLM call
            logger.error(f"Failed to generate questions from LLM: {e}")
            # Return empty list or re-raise depending on desired handling
            return [] # Return empty list on LLM error for now
        except Exception as e:
             logger.error(f"Unexpected error calling LLM: {e}", exc_info=True)
             return []

        # 4. Parse LLM Output
        try:
            questions = self._parse_questions(raw_llm_output)
            logger.info(f"Successfully parsed {len(questions)} questions.")
            return questions
        except Exception as e:
            logger.error(f"Failed to parse questions from LLM output: {e}", exc_info=True)
            # Optionally return raw output or empty list on parsing error
            return [f"Error: Failed to parse LLM output. Raw: {raw_llm_output}"]

    def generate_questions(self, document_path: str, num_questions: int = 5) -> List[str]:
        """
        Reads a document file and generates questions based on its content.

        Args:
            document_path: Path to the input document (.txt, .md).
            num_questions: Desired number of questions.

        Returns:
            List of generated questions or empty list on error.
        
        Raises:
            FileNotFoundError, IOError, ValueError (from file reading or content processing)
            ContextLengthError, RuntimeError (from generation process)
        """
        logger.info(f"Generating questions for document: {document_path}")
        content = ""
        try:
            content = read_text_file(document_path)
            if not content:
                 logger.error(f"Document file is empty: {document_path}")
                 raise ValueError(f"Document file is empty: {document_path}")
        except FileNotFoundError:
            logger.error(f"Document file not found: {document_path}")
            raise
        except Exception as e:
            logger.error(f"Error reading document file {document_path}: {e}", exc_info=True)
            raise IOError(f"Could not read document file {document_path}: {e}")
        
        # Delegate to content-based method
        return self.generate_questions_from_content(content, num_questions) 