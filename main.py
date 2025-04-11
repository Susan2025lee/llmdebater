import logging
import sys
import os
from typing import Optional, Annotated

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

import typer

from core.answer_agent import ReportQAAgent as AnswerAgent # Alias for clarity
from core.question_agent import QuestionAgent # Import QuestionAgent
from core.orchestrator import Orchestrator # Import Orchestrator
from core.llm_interface import LLMInterface # Import LLMInterface for Orchestrator
from utils.file_handler import read_text_file
from utils.token_utils import estimate_token_count
from core.answer_agent import MAX_INPUT_TOKENS, MODEL_NAME, PROMPT_TEMPLATE, ContextLengthError

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create a Typer app
app = typer.Typer(help="CLI for the Question/Answer Orchestration System.")

# --- Helper Functions (Minor changes for Typer context) ---
def _handle_error(message: str, exit_code: int = 1):
    """Prints error message to stderr and exits."""
    print(f"Error: {message}", file=sys.stderr)
    raise typer.Exit(code=exit_code)

def _initialize_answer_agent() -> AnswerAgent:
    """Initializes and returns the Answer Agent."""
    try:
        return AnswerAgent()
    except Exception as e:
        _handle_error(f"Initializing Answer Agent failed: {e}")

def _initialize_question_agent() -> QuestionAgent:
    """Initializes and returns the Question Agent."""
    try:
        return QuestionAgent()
    except Exception as e:
        _handle_error(f"Initializing Question Agent failed: {e}")

def _initialize_llm_interface() -> LLMInterface:
    """Initializes and returns the LLM Interface for the orchestrator."""
    try:
        # Assuming orchestrator uses the same primary model for its own checks
        return LLMInterface(model_key=MODEL_NAME)
    except Exception as e:
        _handle_error(f"Initializing LLM Interface failed: {e}")

# --- Typer Commands --- #
@app.command("chat", help="Run interactive chat with the Answer Agent based on a report.")
def run_interactive_chat(
    report_path: Annotated[str, typer.Argument(help="Path to the report file for the Answer Agent.", exists=True, file_okay=True, dir_okay=False, readable=True)]
):
    """Loads a report and runs the interactive Q&A loop."""
    # logger.info(f"Starting interactive session for report: '{report_path}'") # Use logger if needed
    
    # --- 1. Load Report and Initial Checks --- 
    try:
        # print(f"Loading report: '{report_path}'...") # Removed status print
        report_content = read_text_file(report_path)
        if not report_content:
            _handle_error(f"Report file is empty: '{report_path}'.")
        # print("Report loaded successfully.") # Removed status print
    except Exception as e:
        logger.error(f"Error reading report file {report_path}: {e}", exc_info=True)
        _handle_error(f"Reading report file failed: {e}")

    # Estimate base tokens - using the function from answer_agent for consistency?
    # Or keep the local helper? Let's keep it simple for now.
    base_prompt = PROMPT_TEMPLATE.format(report_content=report_content, user_query="")
    base_tokens = estimate_token_count(base_prompt, model_name=MODEL_NAME)
    if base_tokens == -1:
        _handle_error("Could not estimate base token count for the report.")
    elif base_tokens > MAX_INPUT_TOKENS:
        # Keep this warning as it's important user feedback
        print(
            f"Warning: The report content itself ({base_tokens} tokens) already exceeds the estimated maximum input tokens ({MAX_INPUT_TOKENS}). Queries may fail.",
            file=sys.stderr
        )

    # --- 2. Initialize Agent --- 
    agent = _initialize_answer_agent()

    # --- 3. Interactive Loop --- 
    print(f"\nEnter your questions about the report '{os.path.basename(report_path)}'. Type 'exit' or 'quit' to end.") # Keep instructions
    while True:
        try:
            query = input("\nYour question ('exit' to quit): ") # Keep prompt
        except EOFError: # Handle Ctrl+D
            print("\nExiting chat session.") # Keep exit message
            break

        if query.lower().strip() in ["exit", "quit"]:
            print("Exiting chat session.") # Keep exit message
            break
            
        if not query.strip():
            continue
            
        # print("Processing your question...") # Removed status print
        try:
            answer = agent.ask_with_content(query, report_content)
            
            # Keep answer output
            print("\n" + "-"*10 + " Answer " + "-"*10)
            if answer.startswith("Error:") or answer.startswith("Input (report + query) exceeds"):
                print(f"{answer}")
            else:
                print(answer)
            print("-"*28)
        except Exception as e:
            # Keep unexpected error message for user
            logger.error(f"Unexpected error during agent query processing: {e}", exc_info=True)
            print(f"An unexpected error occurred: {e}", file=sys.stderr)
            # Decide whether to continue or exit? Let's continue for interactive mode.

@app.command("generate-questions", help="Generate questions based on a document using the Question Agent.")
def run_generate_questions(
    document_path: Annotated[str, typer.Argument(help="Path to the document for the Question Agent.", exists=True, file_okay=True, dir_okay=False, readable=True)],
    num_questions: Annotated[int, typer.Option(help="Number of questions to generate.", min=1)] = 5
):
    """Loads a document and runs the Question Agent to generate questions."""
    # logger.info(f"Generating {num_questions} questions for document: '{document_path}'") # Use logger if needed
    
    try:
        question_agent = _initialize_question_agent()
        # print(f"Loading document and generating {num_questions} questions...") # Removed status print
        # print("(This might take a moment...)") # Removed status print
        
        questions = question_agent.generate_questions(document_path, num_questions)
        
        # Keep final output
        print("\n" + "="*10 + " Generated Questions " + "="*10)
        if questions:
            for i, q in enumerate(questions):
                print(f"{i+1}. {q}")
        else:
            print("No questions were generated. The document might be too short or an issue occurred.")
        print("="*39)

    except ContextLengthError as e:
        _handle_error(f"The document content is too long for the model's context window. Details: {e}")
    except (IOError, ValueError, FileNotFoundError) as e:
        # Catch file read errors or empty file errors from generate_questions
        _handle_error(f"Processing document file failed: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during question generation: {e}", exc_info=True)
        _handle_error(f"An unexpected error occurred during question generation: {e}")

# T3.1: Add orchestrate command
@app.command("orchestrate", help="Run the full orchestrated workflow (Question -> Answer -> Satisfaction -> Follow-up).")
def run_orchestration(
    question_doc_path: Annotated[str, typer.Argument(help="Path to the document for the Question Agent.", exists=True, file_okay=True, dir_okay=False, readable=True)],
    answer_doc_path: Annotated[str, typer.Argument(help="Path to the report/document for the Answer Agent.", exists=True, file_okay=True, dir_okay=False, readable=True)],
    num_initial_questions: Annotated[int, typer.Option(help="Number of initial questions to generate.", min=1)] = 5,
    max_follow_ups: Annotated[int, typer.Option(help="Maximum number of follow-up attempts per question.", min=0)] = 2
):
    """Instantiates agents and runs the Orchestrator interaction loop."""
    # logger.info("Starting orchestrated workflow.") # Use logger if needed
    # logger.info(f"Question generation document: {question_doc_path}")
    # logger.info(f"Answering document: {answer_doc_path}")
    # logger.info(f"Number of initial questions: {num_initial_questions}")
    # logger.info(f"Max follow-ups per question: {max_follow_ups}")
    
    # T3.2: Instantiate agents and orchestrator
    try:
        # print("Initializing agents...") # Removed status print
        question_agent = _initialize_question_agent()
        answer_agent = _initialize_answer_agent()
        llm_interface = _initialize_llm_interface() # For Orchestrator's own calls
        
        orchestrator = Orchestrator(
            question_agent=question_agent,
            answer_agent=answer_agent,
            llm_interface=llm_interface,
            max_follow_ups=max_follow_ups
        )
        # print("Initialization complete.") # Removed status print
    except typer.Exit: # Propagate exits from helper functions
        raise
    except Exception as e:
        logger.error(f"Failed to initialize agents or orchestrator: {e}", exc_info=True)
        _handle_error(f"Initialization failed: {e}")
       
    # T3.3: Call the Orchestrator's run_interaction method
    try:
        orchestrator.run_interaction(
            question_doc_path=question_doc_path,
            answer_doc_path=answer_doc_path,
            num_initial_questions=num_initial_questions
        )
    except ContextLengthError as e:
        # Catch context errors specifically from agents if they propagate
        _handle_error(f"A context length error occurred during processing: {e}")
    except Exception as e:
        # Catch any other unexpected error from the interaction loop
        logger.error(f"An unexpected error occurred during the orchestrated interaction: {e}", exc_info=True)
        _handle_error(f"Interaction failed unexpectedly: {e}")
       

if __name__ == "__main__":
    # Run the Typer app
    app() 