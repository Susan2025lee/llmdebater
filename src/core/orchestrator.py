import re
import logging # Import logging
from src.core.answer_agent import ReportQAAgent
from src.core.question_agent import QuestionAgent
from src.core.llm_interface import LLMInterface
from src.utils.file_handler import read_text_file
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
        Initializes the Orchestrator.

        Args:
            question_agent: An instance of the QuestionAgent.
            answer_agent: An instance of the ReportQAAgent.
            llm_interface: An instance of the LLMInterface for Orchestrator's own calls.
            max_follow_ups: Maximum number of follow-up attempts per initial question.
        """
        self.question_agent = question_agent
        self.answer_agent = answer_agent
        self.llm_interface = llm_interface
        self.max_follow_ups = max_follow_ups
        # Updated satisfaction prompt to always ask for a reason
        self.satisfaction_prompt_template = """
You are an evaluation agent. Your task is to assess if the provided 'Answer' adequately and completely addresses the 'Original Question'. Do not use external knowledge. Base your assessment *only* on the text provided in the 'Answer'.

Original Question:
{question}

Answer:
{answer}

Is the Answer satisfactory in addressing the Original Question?
Respond with either "Satisfied" or "Unsatisfied".
Briefly explain the reason for your assessment (why it is satisfied or unsatisfied) based *only* on the question and answer text.

Assessment: [Satisfied/Unsatisfied]
Reason: [Brief explanation]
"""
        # TODO T2.2: Finalize follow-up prompt - this is V1
        self.follow_up_prompt_template = """
You are a question refinement agent. You received an 'Original Question' and an 'Unsatisfactory Answer' that failed to fully address the question.
Your task is to generate a *single, specific* follow-up question that directly targets the missing information or inadequacy in the 'Unsatisfactory Answer'. The goal is to guide the next response towards fully answering the 'Original Question'.

Original Question:
{question}

Unsatisfactory Answer:
{answer}

Generate a follow-up question to elicit the missing information needed to satisfy the Original Question.

Follow-up Question:
"""

    def run_interaction(self, question_doc_path: str, answer_doc_path: str, num_initial_questions: int = 5) -> list:
        """
        Runs the main interaction loop for all questions and returns the results.
        Each result includes the final satisfaction status and reason.
        
        Returns:
            A list of dictionaries, where each dictionary contains:
            {'initial_question': str, 'final_answer': str, 'history': list, 
             'satisfaction_status': str, 'satisfaction_reason': str | None}
        """
        all_results = [] # Restore results list

        try:
            question_doc_content = read_text_file(question_doc_path)
            initial_questions = self.question_agent.generate_questions_from_content(question_doc_content, num_questions=num_initial_questions)
            if not initial_questions:
                return [] # Return empty list

            answer_doc_content = read_text_file(answer_doc_path)

        except FileNotFoundError as e:
            logger.error(f"File not found during setup: {e}") # Log instead of print
            raise e 
        except Exception as e:
            logger.error(f"An unexpected error occurred during setup: {e}", exc_info=True) # Log
            raise e # Re-raise for Streamlit

        for i, question in enumerate(initial_questions):
            try:
                final_answer, conversation_history, satisfaction_status, satisfaction_reason = self._process_single_question(question, answer_doc_content)

                all_results.append({
                    'initial_question': question,
                    'final_answer': final_answer,
                    'history': conversation_history,
                    'satisfaction_status': satisfaction_status,
                    'satisfaction_reason': satisfaction_reason
                })

            except Exception as e:
                logger.error(f"Error processing question {i+1} (\"{question}\"): {e}", exc_info=True)
                all_results.append({
                    'initial_question': question,
                    'final_answer': f"ERROR processing this question: {e}",
                    'history': [],
                    'satisfaction_status': 'Error',
                    'satisfaction_reason': str(e)
                })
                continue 

        return all_results # Return the collected results

    def _process_single_question(self, initial_question: str, answer_doc_content: str) -> tuple[str, list, str, str | None]:
        """
        Handles the cycle of getting an answer, checking satisfaction, and potentially following up.
        Returns the final answer, history, satisfaction status (str), and reason (str|None).
        """
        current_question = initial_question
        conversation_history = []
        final_answer = "No satisfactory answer found within follow-up limits."
        final_satisfaction_status = "Unknown"
        final_satisfaction_reason = None

        for attempt in range(self.max_follow_ups + 1):
            answer = self.answer_agent.ask_with_content(current_question, answer_doc_content)

            conversation_history.append({"question": current_question, "answer": answer})

            is_satisfied, reason = self._check_satisfaction(current_question, answer)
            final_satisfaction_status = "Satisfied" if is_satisfied else "Unsatisfied"
            final_satisfaction_reason = reason # Store the reason

            if is_satisfied:
                final_answer = answer
                break

            if attempt < self.max_follow_ups:
                follow_up_question = self._generate_follow_up(current_question, answer)
                if not follow_up_question:
                    break
                current_question = follow_up_question
            else:
                pass # Just finish the loop

        return final_answer, conversation_history, final_satisfaction_status, final_satisfaction_reason

    def _check_satisfaction(self, question: str, answer: str) -> tuple[bool, str | None]:
        """
        Uses the LLMInterface to check if the answer satisfies the question.
        Assumes the prompt now always asks for a reason.
        """
        prompt = self.satisfaction_prompt_template.format(question=question, answer=answer)
        try:
            response_text = self.llm_interface.generate_response(prompt)
            logger.info(f"[_check_satisfaction] Raw LLM Response: {response_text[:200]}...")
        except Exception as e:
            logger.error(f"Error calling LLM for satisfaction check: {e}", exc_info=True)
            return False, f"LLM call failed during satisfaction check: {e}"

        try:
            assessment_match = re.search(r"Assessment:\s*(Satisfied|Unsatisfied)", response_text, re.IGNORECASE)
            if not assessment_match:
                logger.warning(f"Could not parse Assessment from satisfaction response: {response_text}")
                return False, "Could not parse Assessment from LLM response."
                
            is_satisfied = assessment_match.group(1).lower() == "satisfied"

            reason = None
            # Always try to parse the reason now
            reason_match = re.search(r"Reason:\s*(.*)", response_text, re.IGNORECASE | re.DOTALL)
            if reason_match:
                reason = reason_match.group(1).strip()
            else:
                logger.warning(f"Could not parse Reason from response: {response_text}")
                reason = "Could not parse Reason from LLM response."
                
            return is_satisfied, reason
        except Exception as e:
            logger.error(f"Error parsing satisfaction response: {e}. Raw response: {response_text}", exc_info=True)
            return False, f"Error parsing satisfaction LLM response: {e}"

    def _generate_follow_up(self, question: str, answer: str) -> str | None:
        """
        Uses the LLMInterface to generate a follow-up question.

        Args:
            question: The original question (or previous follow-up).
            answer: The unsatisfactory answer.

        Returns:
            The generated follow-up question as a string, or None if generation fails.
        """
        prompt = self.follow_up_prompt_template.format(question=question, answer=answer)
        # T2.8: Implement LLM call (Uncommented)
        try:
            response_text = self.llm_interface.generate_response(prompt)
            logger.info(f"[_generate_follow_up] Raw LLM Response: {response_text[:200]}...") # Log truncated response
        except Exception as e:
             logger.error(f"Error calling LLM for follow-up generation: {e}", exc_info=True)
             return None # Return None if LLM call fails

        # T2.8: Implement robust parsing
        try:
            # Simple parsing assuming the question follows "Follow-up Question:"
            match = re.search(r"Follow-up Question:\s*(.*)", response_text, re.IGNORECASE | re.DOTALL)
            if match:
                follow_up = match.group(1).strip()
                # Basic validation: ensure it's not empty and maybe not identical to the input question?
                if follow_up and follow_up.lower() != question.lower():
                    return follow_up
                else:
                    logger.warning(f"Parsed empty follow-up or identical to original question. Raw: {response_text}")
                    return None # Treat empty or identical follow-up as failure
            else:
                logger.warning(f"Could not parse valid follow-up question from: {response_text}")
                return None
        except Exception as e:
            logger.error(f"Error parsing follow-up response: {e}. Raw response: {response_text}", exc_info=True)
            return None 