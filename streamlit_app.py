import streamlit as st
import os
import tempfile
import logging
import sys

# Add src directory to path (consider a better packaging approach later)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# Import core components
from core.answer_agent import ReportQAAgent as AnswerAgent
from core.question_agent import QuestionAgent
from core.orchestrator import Orchestrator
from core.llm_interface import LLMInterface
from core.answer_agent import MODEL_NAME, ContextLengthError

# Setup logging (optional for Streamlit, but can be helpful)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Streamlit App --- #
st.set_page_config(layout="wide")
st.title("Interactive Question/Answer Orchestration System")

st.sidebar.header("Configuration")

# --- Session State Initialization ---
if 'processing_done' not in st.session_state:
    st.session_state.processing_done = False
if 'results' not in st.session_state:
    st.session_state.results = []
if 'current_display_index' not in st.session_state:
    st.session_state.current_display_index = 0

# File Uploaders
st.sidebar.subheader("Input Documents")
# Add keys to allow resetting them potentially, though not strictly needed for this flow
question_doc_file = st.sidebar.file_uploader("Upload Document for Question Generation (.txt, .md)", type=["txt", "md"], key="q_uploader")
answer_doc_file = st.sidebar.file_uploader("Upload Document for Answering (.txt, .md)", type=["txt", "md"], key="a_uploader")

# Parameters
st.sidebar.subheader("Parameters")
num_initial_questions = st.sidebar.number_input("Number of Initial Questions to Generate", min_value=1, max_value=20, value=3, step=1)
max_follow_ups = st.sidebar.number_input("Max Follow-up Attempts per Question", min_value=0, max_value=5, value=1, step=1)

# --- Workflow Control Buttons --- #
col1, col2 = st.sidebar.columns(2)
with col1:
    # Disable button if processing has already been done (user should reset)
    run_button = st.sidebar.button("Run Orchestration", disabled=st.session_state.processing_done)
with col2:
    # Enable reset only if processing has been done or started implicitly
    reset_button = st.sidebar.button("Reset", disabled=not st.session_state.processing_done and not st.session_state.results)

# --- Initialization Functions (cached for efficiency) ---
# Cache instances to avoid re-initializing on every interaction
@st.cache_resource
def initialize_agents():
    """Initializes and caches the agents and LLM interface."""
    try:
        question_agent = QuestionAgent()
        answer_agent = AnswerAgent()
        llm_interface = LLMInterface(model_key=MODEL_NAME)
        return question_agent, answer_agent, llm_interface
    except Exception as e:
        st.error(f"Error initializing agents: {e}")
        logger.error(f"Agent initialization failed: {e}", exc_info=True)
        return None, None, None

# --- Helper Function --- #
def reset_state():
    st.session_state.processing_done = False
    st.session_state.results = []
    st.session_state.current_display_index = 0
    # Potentially reset file uploaders if needed, st.experimental_rerun might be simpler
    st.rerun()

if reset_button:
    reset_state()

# --- Main Logic --- #
if run_button and not st.session_state.processing_done:
    if question_doc_file is not None and answer_doc_file is not None:
        st.info("Initializing agents...")
        question_agent, answer_agent, llm_interface = initialize_agents()

        if question_agent and answer_agent and llm_interface:
            q_temp_path = None
            a_temp_path = None
            try:
                # Create temp files
                with tempfile.NamedTemporaryFile(delete=False, suffix=".md", mode='wb') as q_temp:
                    q_temp.write(question_doc_file.getvalue())
                    q_temp_path = q_temp.name
                with tempfile.NamedTemporaryFile(delete=False, suffix=".md", mode='wb') as a_temp:
                    a_temp.write(answer_doc_file.getvalue())
                    a_temp_path = a_temp.name

                st.info(f"Processing started... This might take a while.")
                orchestrator = Orchestrator(
                    question_agent=question_agent,
                    answer_agent=answer_agent,
                    llm_interface=llm_interface,
                    max_follow_ups=max_follow_ups
                )

                # Run the *entire* interaction once
                with st.spinner("Agents are processing all questions..."):
                    all_results = orchestrator.run_interaction(
                        question_doc_path=q_temp_path,
                        answer_doc_path=a_temp_path,
                        num_initial_questions=num_initial_questions
                    )
                
                # Store results and set flags
                st.session_state.results = all_results
                st.session_state.processing_done = True
                st.session_state.current_display_index = 0 
                st.success("Processing Complete! Displaying first result.")
                # Rerun to update display with the first result
                st.rerun()

            except ContextLengthError as e:
                 st.error(f"Context Length Error: {e}")
                 st.session_state.processing_done = False # Allow retry after fixing
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")
                logger.error(f"Orchestration failed: {e}", exc_info=True)
                st.session_state.processing_done = False # Allow retry
            finally:
                # Clean up temporary files
                if q_temp_path and os.path.exists(q_temp_path):
                    try: os.unlink(q_temp_path)
                    except Exception as e: logger.error(f"Error deleting temp q file: {e}")
                if a_temp_path and os.path.exists(a_temp_path):
                    try: os.unlink(a_temp_path)
                    except Exception as e: logger.error(f"Error deleting temp a file: {e}")
        else:
            st.error("Agent initialization failed. Cannot proceed.")
    else:
        st.warning("Please upload both documents before running.")

# --- Display Logic --- #
if st.session_state.processing_done and st.session_state.results:
    current_index = st.session_state.current_display_index
    results = st.session_state.results
    
    if 0 <= current_index < len(results):
        result = results[current_index]
        st.header(f"Result for Initial Question {current_index + 1}/{len(results)}")
        st.subheader(f"Q: {result['initial_question']}")
        
        # Display Satisfaction Info
        status = result.get('satisfaction_status', 'Unknown')
        reason = result.get('satisfaction_reason', 'N/A')
        if status == "Satisfied":
            st.success(f"Satisfaction Status: {status}")
        elif status == "Unsatisfied":
            st.warning(f"Satisfaction Status: {status}")
        else:
            st.error(f"Status: {status}") # Handle Error case
        st.caption(f"Reason: {reason}")
        
        with st.expander("Show Conversation Thread", expanded=False):
            if result['history']:
                for turn_index, turn in enumerate(result['history']):
                    st.markdown(f"**Q:** {turn['question']}")
                    st.markdown("**A:**") 
                    st.markdown(f"> {turn['answer'].replace('\n', '\n> ')}") 
                    st.divider()
            else:
                st.write("No conversation history available.")
        
        st.markdown("**Final Answer:**")
        st.markdown(f"> {result['final_answer'].replace('\n', '\n> ')}")
        st.divider()

        # Navigation Button
        if current_index < len(results) - 1:
            if st.button("Next Question", key=f"next_{current_index}"):
                st.session_state.current_display_index += 1
                st.rerun()
        else:
            st.success("Workflow Complete! All results shown.")
    else:
        # Should not happen if logic is correct, but handle index out of bounds
        st.error("Error displaying results: Invalid index.")
        reset_state()

elif not st.session_state.processing_done:
     st.markdown("### Please upload documents and click 'Run Orchestration' in the sidebar to begin.")
