# <CURSOR_TASK_START>
import streamlit as st
import os
import tempfile
import logging
import sys
import time
from typing import List, Dict, Callable, Iterator, Tuple # Add Iterator, Tuple

# Add src directory to path (consider a better packaging approach later)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# Import core components
from core.answer_agent_v3 import AnswerAgentV3, ContextLengthError # V3 Agent
from core.question_agent import QuestionAgent
from core.orchestrator_v3 import OrchestratorV3 # V3 Orchestrator
from core.llm_interface import LLMInterface
from core.answer_agent import MODEL_NAME

# Setup logging (optional for Streamlit, but can be helpful)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Constants for Agent Names ---
ORCHESTRATOR_NAME = "Orchestrator V3"
ANSWER_AGENT_NAME = "Answer Agent V3"
QUESTION_AGENT_NAME = "Question Agent"
SYSTEM_NAME = "System"
SYNTHESIZER_NAME = "Synthesizer"

# Define colors for different roles
AGENT_COLORS = {
    SYSTEM_NAME: "#D0D0D0", # Medium Gray
    QUESTION_AGENT_NAME: "#A0D2E7", # Medium Blue
    ANSWER_AGENT_NAME: "#E8F5E9", # Light green
    ORCHESTRATOR_NAME: "#FFE08C", # Medium Yellow
    SYNTHESIZER_NAME: "#FFF0E1", # Light orange
    "DEFAULT": "#FFFFFF" # White or default
}


# --- Auto-scroll JavaScript for Chat Container (Revised Selector & Retries) ---
# Targeting the scrollable div within the fixed-height container
auto_scroll_js = """
<script>
function tryScroll() {
    // Primary target: Find the container with the fixed height style
    const primaryTarget = window.parent.document.querySelector('div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"] div[style*="height: 600px"]');
    // Secondary target: Within that, find the immediate child div that actually scrolls (often the first one)
    const scrollableDiv = primaryTarget ? primaryTarget.querySelector(':scope > div:nth-child(1)') : null;

    const targetContainer = scrollableDiv || primaryTarget; // Use scrollableDiv if found, otherwise primaryTarget

    if (targetContainer) {
        targetContainer.scrollTop = targetContainer.scrollHeight;
        // console.log('Auto-scroll attempted on:', targetContainer);
    } else {
        // console.warn('Auto-scroll target container not found.');
    }
}
// Execute with multiple delays to catch updates
tryScroll(); // Initial try
setTimeout(tryScroll, 150); // After short delay
setTimeout(tryScroll, 400); // After medium delay
setTimeout(tryScroll, 700); // After longer delay
</script>
"""

# --- Streamlit App --- #
st.set_page_config(layout="wide")
# Use subheader for title like V1
st.subheader("Automated Q&A Orchestration Chat (V3 - Multi-Round Debate)")

st.sidebar.header("Configuration")

# --- Session State Initialization for V3 ---
def initialize_session_state(force_reset=False):
    """Initialize or reset session state variables for V3."""
    defaults = {
        'workflow_started': False,
        'setup_done': False,
        'is_running': False,
        'current_step': 'idle', # idle, setup, running_generator, finished, error
        'orchestrator_v3': None,
        'question_agent': None,
        'answer_agents_v3': [],
        'chat_history': [],
        'error_message': None,
        'q_temp_path': None,
        'a_temp_paths': [],
        'output_file_path_config': "debate_results_v3.md",
        'results_log': [], # Keep for potential summary
        'workflow_generator': None # State for the generator object
    }
     # Add default system message if chat history is empty or reset
    if force_reset or 'chat_history' not in st.session_state or not st.session_state.chat_history:
        st.session_state.chat_history = [{"role": SYSTEM_NAME, "content": "Welcome! Upload documents and configure parameters to start the V3 multi-round debate workflow."}]

    for key, default_value in defaults.items():
        if force_reset or key not in st.session_state:
             # Special handling for chat history reset
            if key == 'chat_history' and not force_reset:
                 continue # Don't overwrite existing history unless forced
            st.session_state[key] = default_value

# Initial initialization
initialize_session_state()

# --- Sidebar UI Elements --- #
st.sidebar.subheader("Input Documents")
question_doc_file = st.sidebar.file_uploader(
    "Upload Document for Question Generation (.txt, .md)",
    type=["txt", "md"],
    key="q_uploader_v3",
    disabled=st.session_state.is_running # Disable during run
)
answer_doc_files: List[st.runtime.uploaded_file_manager.UploadedFile] | None = st.sidebar.file_uploader(
    "Upload Answer Documents for Debate (.txt, .md)",
    type=["txt", "md"],
    accept_multiple_files=True,
    key="a_uploader_v3",
    disabled=st.session_state.is_running # Disable during run
)
st.sidebar.subheader("Parameters")
num_initial_questions = st.sidebar.number_input(
    "Number of Initial Questions",
    min_value=1, max_value=20, value=3, step=1,
    key="num_q_v3",
    disabled=st.session_state.is_running # Disable during run
)
max_debate_rounds = st.sidebar.number_input(
    "Max Debate Rounds (after initial)",
    min_value=0, max_value=10, value=2, step=1,
    key="max_rounds_v3",
    help="Number of debate rounds after initial answers (0 means only initial answers + synthesis).",
    disabled=st.session_state.is_running
)
st.session_state.output_file_path_config = st.sidebar.text_input(
    "Output Filename (.md)",
    value=st.session_state.output_file_path_config,
    key="output_fname_v3",
    disabled=st.session_state.is_running # Disable during run
)
st.sidebar.subheader("Workflow Control")
col1, col2 = st.sidebar.columns(2)
with col1:
    start_button = st.button("Start V3 Debate",
                             disabled=st.session_state.is_running,
                             key="start_button_v3",
                             use_container_width=True)
with col2:
    reset_button = st.button("Reset",
                             disabled=st.session_state.is_running,
                             key="reset_button_v3",
                             use_container_width=True)


# --- Initialization Functions --- #
def initialize_llm_interface():
    """Initializes only the LLM Interface."""
    try:
        llm_interface = LLMInterface(model_key=MODEL_NAME)
        return llm_interface
    except Exception as e:
        st.error(f"Fatal Error initializing LLM Interface: {e}")
        logger.error(f"LLM Interface initialization failed: {e}", exc_info=True)
        return None

# --- Helper Functions --- #
def cleanup_temp_files():
    """Cleans up temporary files stored in session state."""
    q_path = st.session_state.get('q_temp_path')
    a_paths = st.session_state.get('a_temp_paths', [])

    if q_path and os.path.exists(q_path):
        try:
            os.unlink(q_path)
            logger.info(f"Deleted temp question file: {q_path}")
            st.session_state.q_temp_path = None
        except Exception as e:
            logger.error(f"Error deleting temp file {q_path}: {e}")

    if a_paths:
        new_a_paths = []
        for path in a_paths:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                    logger.info(f"Deleted temp answer file: {path}")
                except Exception as e:
                    logger.error(f"Error deleting temp file {path}: {e}")
                    new_a_paths.append(path)
            else:
                pass
        st.session_state.a_temp_paths = new_a_paths

def add_chat_message(role: str, content: str):
    """Appends a message to the chat history and triggers auto-scroll."""
    st.session_state.chat_history.append({"role": role, "content": content})
    # Inject scroll JS
    st.components.v1.html(auto_scroll_js, height=0, width=0)

def reset_state():
    """Resets the application state and cleans up resources."""
    add_chat_message(SYSTEM_NAME, "Resetting workflow state...")
    try:
        cleanup_temp_files()
        if 'workflow_generator' in st.session_state:
            st.session_state.workflow_generator = None
        initialize_session_state(force_reset=True)
        logger.info("Application state has been fully reset")
        # Don't add message here, let the initial state handle it
    except Exception as e:
        logger.error(f"Error during reset: {e}")
        # Add error directly to state?
        initialize_session_state(force_reset=True) # Reset state even on error
        st.session_state.chat_history.append({"role": SYSTEM_NAME, "content": f"Error during reset: {e}"})
    st.rerun()

if reset_button:
    reset_state()


# --- Core Workflow Setup Function --- #
def run_v3_workflow_setup():
    """Handles the setup and prepares the generator for the V3 workflow."""
    st.session_state.error_message = None
    st.session_state.is_running = False
    st.session_state.current_step = 'setup'
    st.session_state.workflow_generator = None
    st.session_state.results_log = []
    st.session_state.setup_done = False
    cleanup_temp_files() # Clean up previous run's files

    add_chat_message(SYSTEM_NAME, "Starting V3 workflow... Validating inputs.")

    # --- 1. Validate Inputs --- #
    if not question_doc_file:
        st.error("Please upload the Question Generation document.")
        st.session_state.error_message = "Missing Question document."
    if not answer_doc_files:
        st.error("Please upload at least one Answer document for the debate.")
        st.session_state.error_message = "Missing Answer document(s)."
    if not st.session_state.output_file_path_config or not st.session_state.output_file_path_config.endswith('.md'):
        st.error("Please provide a valid Output Filename ending in .md")
        st.session_state.error_message = "Invalid Output Filename."

    if st.session_state.error_message:
        st.session_state.current_step = 'idle'
        add_chat_message(SYSTEM_NAME, f"Workflow setup failed: {st.session_state.error_message}")
        st.rerun()
        return

    # --- 2. Save Temp Files --- #
    add_chat_message(SYSTEM_NAME, "Saving uploaded files temporarily...")
    temp_files_ok = True
    temp_answer_paths = []
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(question_doc_file.name)[1]) as tmp_q:
            tmp_q.write(question_doc_file.getvalue())
            st.session_state.q_temp_path = tmp_q.name
            add_chat_message(SYSTEM_NAME, f"Saved question doc to temp file: {os.path.basename(st.session_state.q_temp_path)}")
    except Exception as e:
        st.error(f"Error saving question document: {e}")
        st.session_state.error_message = "Error saving question document."
        temp_files_ok = False

    if temp_files_ok and answer_doc_files:
        st.session_state.a_temp_paths = []
        for i, file in enumerate(answer_doc_files):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp_a:
                    tmp_a.write(file.getvalue())
                    st.session_state.a_temp_paths.append(tmp_a.name)
                    temp_answer_paths.append(tmp_a.name) # Use local var for immediate init
                    add_chat_message(SYSTEM_NAME, f"Saved answer doc {i+1} to temp file: {os.path.basename(tmp_a.name)}")
            except Exception as e:
                st.error(f"Error saving answer document {i+1} ('{file.name}'): {e}")
                st.session_state.error_message = f"Error saving answer document {i+1}."
                temp_files_ok = False
                break # Stop saving more files if one fails

    if not temp_files_ok:
        st.session_state.current_step = 'idle'
        add_chat_message(SYSTEM_NAME, f"Workflow setup failed: {st.session_state.error_message}")
        cleanup_temp_files() # Clean up any partially saved files
        st.rerun()
        return

    # --- 3. Initialize Agents & Orchestrator --- #
    add_chat_message(SYSTEM_NAME, "Initializing V3 agents and orchestrator...")
    try:
        # Initialize shared LLM Interface
        llm_interface_shared = initialize_llm_interface()
        if not llm_interface_shared:
            # Error handled within initialize_llm_interface
            raise ValueError("LLM Interface initialization failed.")

        # Initialize Question Agent
        st.session_state.question_agent = QuestionAgent(llm_interface=llm_interface_shared)
        add_chat_message(SYSTEM_NAME, "Question Agent initialized.")

        # Initialize Answer Agents
        st.session_state.answer_agents_v3 = []
        for i, path in enumerate(temp_answer_paths): # Use paths saved in this run
            # ReportQAAgent currently initializes its own LLM interface
            agent = AnswerAgentV3(llm_interface=llm_interface_shared)
            st.session_state.answer_agents_v3.append(agent)
            add_chat_message(SYSTEM_NAME, f"Answer Agent V3 {i+1} initialized.")

        # Initialize OrchestratorV3
        output_dir = os.path.join("data", "output")
        os.makedirs(output_dir, exist_ok=True)
        final_output_path = os.path.join(output_dir, st.session_state.output_file_path_config)

        st.session_state.orchestrator_v3 = OrchestratorV3(
            question_agent=st.session_state.question_agent,
            answer_agents=st.session_state.answer_agents_v3,
            output_file_path=final_output_path,
            llm_interface=llm_interface_shared,
            num_initial_questions=num_initial_questions,
            max_debate_rounds=max_debate_rounds # Pass widget value
        )
        add_chat_message(SYSTEM_NAME, "Orchestrator V3 initialized.")

        st.session_state.setup_done = True
        st.session_state.is_running = True # Mark as running immediately after setup
        st.session_state.current_step = 'running_generator'
        add_chat_message(SYSTEM_NAME, "Setup complete. Starting V3 debate interaction...")

        # --- 4. Prepare Generator --- #
        st.session_state.workflow_generator = st.session_state.orchestrator_v3.run_full_debate(
            question_doc_path=st.session_state.q_temp_path,
            answer_doc_paths=st.session_state.a_temp_paths
        )

    except Exception as e:
        logger.error(f"Error during workflow setup/initialization: {e}", exc_info=True)
        st.error(f"Setup Failed: {e}")
        st.session_state.error_message = f"Setup failed: {e}"
        st.session_state.current_step = 'error'
        st.session_state.is_running = False # Stop running on setup error
        cleanup_temp_files()
        st.rerun()
        return

# --- Workflow Execution Logic --- #

if start_button and not st.session_state.is_running:
    run_v3_workflow_setup()
    # Rerun to start processing the generator if setup was successful
    if st.session_state.current_step == 'running_generator':
        st.rerun()

# --- Main Chat Display Area --- #
chat_container = st.container()
# Define placeholders OUTSIDE the markdown div, but inside the container
progress_bar_placeholder = st.empty()
results_placeholder = st.empty()

with chat_container:
    # Create the scrollable div using markdown
    st.markdown("<div style=\"height: 600px; overflow-y: scroll; border: 1px solid #e0e0e0; padding: 10px; border-radius: 5px;\">", unsafe_allow_html=True)
    
    # Display existing chat history INSIDE the div
    for message in st.session_state.chat_history:
        role = message["role"]
        content = message["content"]
        bgcolor = AGENT_COLORS.get(role, AGENT_COLORS["DEFAULT"])
        
        # Use markdown with inline CSS for background color
        st.markdown(
            f'<div style="background-color: {bgcolor}; padding: 10px; border-radius: 5px; margin-bottom: 10px;">'
            f'<b>{role}:</b><br>' # Use <br> for line break after role
            f'{content.replace("\n", "<br>")}' # Replace newlines with <br>
            f'</div>',
            unsafe_allow_html=True
        )

    # Placeholders are already defined outside this specific markdown block
    # We might use them later, but don't redefine them here.

    # Close the div
    st.markdown("</div>", unsafe_allow_html=True)

# --- Generator Processing --- #
if st.session_state.current_step == 'running_generator' and st.session_state.workflow_generator:
    try:
        # Process one step from the generator
        speaker, message = next(st.session_state.workflow_generator)
        add_chat_message(speaker, message)
        st.rerun() # Rerun to display the new message

    except StopIteration:
        add_chat_message(SYSTEM_NAME, "Workflow finished successfully.")
        st.session_state.is_running = False
        st.session_state.current_step = 'finished'
        st.session_state.workflow_generator = None
        cleanup_temp_files()
        st.rerun()

    except Exception as e:
        logger.error(f"Error during workflow execution: {e}", exc_info=True)
        error_message = f"Runtime Error: {e}"
        add_chat_message(SYSTEM_NAME, error_message)
        st.error(error_message)
        st.session_state.is_running = False
        st.session_state.current_step = 'error'
        st.session_state.workflow_generator = None
        cleanup_temp_files()
        st.rerun()

# --- Final State Display --- #
if st.session_state.current_step == 'finished':
    st.success("Workflow completed successfully!")
    # Optionally display a summary or link to the output file
    output_file = os.path.join("data", "output", st.session_state.output_file_path_config)
    if os.path.exists(output_file):
        results_placeholder.info(f"Final results saved to: {output_file}")

elif st.session_state.current_step == 'error':
    st.error(f"Workflow stopped due to an error: {st.session_state.error_message or 'Unknown error'}")

# <CURSOR_TASK_END> 