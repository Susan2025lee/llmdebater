import re
import logging # Import logging
from .answer_agent import ReportQAAgent
from .question_agent import QuestionAgent
from .llm_interface import LLMInterface
from src.utils.file_handler import read_text_file
import os
import sys
# Import exception and constants used
from .answer_agent import ContextLengthError
# Import prompts
from .prompts import SATISFACTION_PROMPT_TEMPLATE, FOLLOW_UP_PROMPT_TEMPLATE
# We might need models later for structured input/output if we go beyond simple parsing
# from src.core.models import ...

# Setup logger for this module
logger = logging.getLogger(__name__)

class Orchestrator:
    """
    Manages the interactive workflow between the Question Agent and Answer Agent,
    handles satisfaction checks, and generates follow-up questions.
    """

    def __init__(self, question_agent: QuestionAgent, answer_agent: ReportQAAgent, llm_interface: LLMInterface, max_follow_ups: int = 2):
        """
        Initializes the Orchestrator with state for interactive processing.
        """
        self.question_agent = question_agent
        self.answer_agent = answer_agent
        self.llm_interface = llm_interface
        self.max_follow_ups = max_follow_ups
        
        # State variables
        self.initial_questions: list | None = None
        self.current_q_index: int = -1
        self.question_doc_path: str | None = None
        self.answer_doc_content: str | None = None # Pre-load answer content
        self.num_initial_questions_req: int = 0

        # Removed prompt definitions

    def load_answer_doc(self, answer_doc_path: str):
        """Loads and stores the answer document content. Public method."""
        try:
            self.answer_doc_content = read_text_file(answer_doc_path)
            if not self.answer_doc_content:
                 raise ValueError(f"Answer document is empty: {answer_doc_path}")
            logger.info(f"Successfully loaded answer document: {answer_doc_path}")
        except Exception as e:
            logger.error(f"Failed to load answer document {answer_doc_path}: {e}", exc_info=True)
            raise # Re-raise for the caller to handle

    def generate_initial_questions(self, question_doc_path: str, num_questions: int) -> list[str]:
        """Generates and returns initial questions. Public method."""
        self.question_doc_path = question_doc_path
        self.num_initial_questions_req = num_questions
        if not self.question_doc_path:
             raise ValueError("Question document path not set before generating questions.")
        try:
            logger.info(f"Generating {self.num_initial_questions_req} initial questions from {self.question_doc_path}...")
            question_doc_content = read_text_file(self.question_doc_path)
            if not question_doc_content:
                raise ValueError(f"Question document is empty: {self.question_doc_path}")

            self.initial_questions = self.question_agent.generate_questions_from_content(
                question_doc_content, num_questions=self.num_initial_questions_req
            )
            self.current_q_index = -1 # Reset index after generation
            if not self.initial_questions:
                logger.warning("Question Agent returned no initial questions.")
                self.initial_questions = [] # Ensure it's an empty list, not None
            else:
                logger.info(f"Generated {len(self.initial_questions)} initial questions.")
            return self.initial_questions # Return the list

        except Exception as e:
            logger.error(f"Failed to generate initial questions: {e}", exc_info=True)
            self.initial_questions = [] # Set to empty on error
            raise # Re-raise for the caller to handle

    def check_satisfaction(self, question: str, answer: str) -> tuple[bool, str | None]:
        """
        Checks if the answer satisfies the question using the LLM.

        Args:
            question: The question asked.
            answer: The answer received.

        Returns:
            A tuple containing:
            - is_satisfied (bool): True if the answer is satisfactory, False otherwise.
            - reason (str | None): The explanation provided by the LLM, or None if parsing fails.
        """
        # logger.debug(f"Checking satisfaction for Q: {question} A: {answer[:100]}...")
        prompt = SATISFACTION_PROMPT_TEMPLATE.format(question=question, answer=answer)
        try:
            # Use a simple generation call, assuming the model can follow the format
            response = self.llm_interface.generate_response(prompt)
            # logger.debug(f"Satisfaction LLM Raw Response: {response}")

            # Basic parsing (Consider more robust parsing, e.g., regex or Pydantic)
            assessment_match = re.search(r"Assessment:\s*(Satisfied|Unsatisfied)", response, re.IGNORECASE)
            reason_match = re.search(r"Reason:\s*(.*)", response, re.DOTALL)

            is_satisfied = False
            if assessment_match and assessment_match.group(1).lower() == "satisfied":
                is_satisfied = True

            reason = reason_match.group(1).strip() if reason_match else None

            # logger.info(f"Satisfaction Check Result: {is_satisfied}, Reason: {reason}")
            return is_satisfied, reason

        except Exception as e:
            logger.error(f"Error during satisfaction check LLM call or parsing: {e}", exc_info=True)
            return False, f"Error during satisfaction check: {e}" # Return False and error message as reason

    def generate_follow_up(self, question: str, answer: str) -> str | None:
        """
        Generates a follow-up question if the answer is unsatisfactory.

        Args:
            question: The original question.
            answer: The unsatisfactory answer.

        Returns:
            The generated follow-up question (str), or None if generation fails.
        """
        # logger.debug(f"Generating follow-up for Q: {question} A: {answer[:100]}...")
        prompt = FOLLOW_UP_PROMPT_TEMPLATE.format(question=question, answer=answer)
        try:
            response = self.llm_interface.generate_response(prompt)
            # logger.debug(f"Follow-up LLM Raw Response: {response}")

            # Basic parsing: Assume the follow-up question is the main part of the response
            # Find "Follow-up Question:" and take the text after it.
            match = re.search(r"Follow-up Question:\s*(.*)", response, re.DOTALL | re.IGNORECASE)
            follow_up_question = match.group(1).strip() if match else response.strip() # Fallback to whole response

            if not follow_up_question:
                 logger.warning("Follow-up generation returned an empty response.")
                 return None
            
            # logger.info(f"Generated Follow-up: {follow_up_question}")
            return follow_up_question
        except Exception as e:
            logger.error(f"Error during follow-up question generation LLM call: {e}", exc_info=True)
            return None # Indicate failure 

    def run_interaction(self, question_doc_path: str, answer_doc_path: str, num_initial_questions: int):
        """
        Runs the full orchestrated interaction loop: load docs, get initial questions,
        process each question with potential follow-ups, and interact with the user.
        """
        try:
            # 1. Load documents
            print("Loading documents...")
            self.load_answer_doc(answer_doc_path)
            # Question doc is loaded inside generate_initial_questions
            print("Documents loaded.")

            # 2. Generate Initial Questions
            print(f"Generating {num_initial_questions} initial questions from {os.path.basename(question_doc_path)}...")
            initial_questions = self.question_agent.generate_questions(question_doc_path, num_initial_questions)
            if not initial_questions:
                print("No initial questions were generated. Exiting.")
                return
            print(f"Generated {len(initial_questions)} initial questions.")

            # 3. Main Loop - Iterate through initial questions
            for i, initial_q in enumerate(initial_questions):
                print("\n" + "="*40)
                print(f"Processing Initial Question {i+1}/{len(initial_questions)}: {initial_q}")
                print("="*40)

                current_question = initial_q
                follow_up_count = 0
                is_satisfied = False

                # Inner loop: Ask -> Check -> Follow-up
                while follow_up_count <= self.max_follow_ups:
                    print(f"\nAttempt {follow_up_count + 1} (Max: {self.max_follow_ups + 1})")
                    
                    # Ask the current question (initial or follow-up)
                    print(f"  Asking: {current_question}")
                    answer = self.answer_agent.ask_with_content(current_question, self.answer_doc_content)
                    print(f"  Received Answer: {answer}")

                    # Check satisfaction
                    print("  Checking answer satisfaction...")
                    # Use the public method name found in the code
                    is_satisfied, reason = self.check_satisfaction(current_question, answer)
                    print(f"  Satisfaction: {'Satisfied' if is_satisfied else 'Unsatisfied'}")
                    if reason:
                        print(f"  Reason: {reason}")

                    if is_satisfied:
                        print("\nAnswer deemed satisfactory.")
                        break # Exit inner loop for this initial question

                    # If not satisfied and follow-ups remain
                    if follow_up_count < self.max_follow_ups:
                        follow_up_count += 1
                        print(f"  Generating follow-up question (Attempt {follow_up_count}/{self.max_follow_ups})...")
                        # Use the public method name found in the code
                        follow_up_question = self.generate_follow_up(initial_q, answer) # Follow up based on original Q and last answer
                        
                        if follow_up_question:
                            print(f"  Generated Follow-up: {follow_up_question}")
                            current_question = follow_up_question # Set for next iteration
                        else:
                            print("  Failed to generate a follow-up question. Stopping follow-ups for this initial question.")
                            break # Exit inner loop
                    else:
                        print(f"\nMaximum follow-up attempts ({self.max_follow_ups}) reached. Moving to next initial question.")
                        break # Exit inner loop

                # 4. User Interaction - Ask to continue after each initial question cycle
                if i < len(initial_questions) - 1: # Don't ask after the last question
                    while True:
                        try:
                            user_input = input("\nContinue with the next initial question? (y/n): ").lower().strip()
                            if user_input == 'y':
                                break
                            elif user_input == 'n':
                                print("Exiting interaction loop.")
                                return # Exit the entire run_interaction method
                            else:
                                print("Invalid input. Please enter 'y' or 'n'.")
                        except EOFError:
                             print("\nDetected EOF. Exiting interaction loop.")
                             return
        
        except FileNotFoundError as e:
             print(f"Error: Input file not found. {e}", file=sys.stderr)
             # Consider re-raising or handling more gracefully depending on CLI/UI needs
        except IOError as e:
             print(f"Error: Could not read input file. {e}", file=sys.stderr)
        except ContextLengthError as e:
             print(f"Error: Document content too long for processing. {e}", file=sys.stderr)
        except ValueError as e: # Catch potential ValueErrors from agents/utils
             print(f"Error: Invalid value or configuration. {e}", file=sys.stderr)
        except RuntimeError as e: # Catch potential RuntimeErrors from agents
             print(f"Error: Runtime issue during processing. {e}", file=sys.stderr)
        except Exception as e:
            # Catch-all for unexpected errors
            print(f"An unexpected error occurred: {e}", file=sys.stderr)
            logger.error("Unexpected error in run_interaction", exc_info=True)
        finally:
            print("\nInteraction loop finished.")

# --- End of Class --- 