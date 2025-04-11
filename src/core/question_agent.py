# Placeholder for QuestionAgent implementation

import logging
import os
from typing import List, Optional
import re # Import regex for better parsing

# Assuming utils and LLMInterface are accessible
from .llm_interface import LLMInterface
from src.utils.token_utils import estimate_token_count
from src.utils.file_handler import read_text_file
from .answer_agent import ContextLengthError, MAX_INPUT_TOKENS, MODEL_NAME # Reusing constants

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

QUESTION_PROMPT_TEMPLATE = """
You are an insightful analyst tasked with generating probing questions about the provided document. Analyze the following text content carefully. Based *only* on the information presented in this document, generate a list of {num_questions} specific and relevant questions that explore the key topics, data points, claims, or potential ambiguities within the text. The questions should encourage deeper understanding or critical evaluation of the document's content.

Avoid generic questions. Focus on questions that can, in principle, be answered using the information *within* the document itself (even if the answer isn't explicitly stated, the question should pertain directly to the document's content).

Format the output as a numbered list of questions, each on a new line.

--- BEGIN DOCUMENT CONTENT ---

{document_content}

--- END DOCUMENT CONTENT ---

Generated Questions:
1.
"""

class QuestionAgent:
    """Generates relevant questions about a given document content."""

    def __init__(self):
        """Initializes the QuestionAgent, setting up LLM access."""
        try:
            # Using the same model as AnswerAgent for now
            self.llm_interface = LLMInterface(model_key=MODEL_NAME) 
            logger.info(f"QuestionAgent initialized for model: {MODEL_NAME}")
        except Exception as e:
            logger.error(f"Failed to initialize LLMInterface for QuestionAgent: {e}", exc_info=True)
            raise RuntimeError(f"Could not initialize LLMInterface for QuestionAgent: {e}")
            
    def _generate_questions_from_llm(self, prompt: str) -> str:
        """Internal helper to call the LLM and get the raw response."""
        try:
            logger.info("Sending request to LLM for question generation...")
            messages = [{"role": "user", "content": prompt}]
            # Use default temperature, potentially adjust later if needed for question quality
            llm_response = self.llm_interface.generate_chat_response(messages)
            
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
        estimated_tokens = estimate_token_count(prompt, model_name=MODEL_NAME)
        if estimated_tokens == -1:
            logger.error("Token estimation failed for question generation prompt.")
            raise ValueError("Token estimation failed.")

        logger.info(f"Estimated prompt token count for question generation: {estimated_tokens}")
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