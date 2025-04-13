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
from core.answer_agent import ReportQAAgent # V2 uses this directly
from core.question_agent import QuestionAgent
# from core.orchestrator import Orchestrator # V1 - Remove
from core.orchestrator_v2 import OrchestratorV2 # V2
from core.llm_interface import LLMInterface
from core.answer_agent import MODEL_NAME, ContextLengthError

# Setup logging (optional for Streamlit, but can be helpful)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Constants for Agent Names ---
ORCHESTRATOR_NAME = "Orchestrator V2"
ANSWER_AGENT_NAME = "Answer Agent" # Base name, index added later
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
st.subheader("Automated Q&A Orchestration Chat (V2 - Multi-Agent Debate)")

st.sidebar.header("Configuration")

# --- Session State Initialization for V2 ---
def initialize_session_state(force_reset=False):
    """Initialize or reset session state variables for V2."""
    defaults = {
        'workflow_started': False,
        'setup_done': False,
        'is_running': False,
        'current_step': 'idle', # idle, setup, running_generator, finished, error
        'orchestrator_v2': None,
        'question_agent': None,
        'answer_agents': [],
        'chat_history': [],
        'error_message': None,
        'q_temp_path': None,
        'a_temp_paths': [],
        'output_file_path_config': "debate_results.md",
        'results_log': [], # Keep for potential summary
        'workflow_generator': None # State for the generator object
    }
     # Add default system message if chat history is empty or reset
    if force_reset or 'chat_history' not in st.session_state or not st.session_state.chat_history:
        st.session_state.chat_history = [{"role": SYSTEM_NAME, "content": "Welcome! Upload documents and configure parameters to start the V2 debate workflow."}]

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
    key="q_uploader_v2",
    disabled=st.session_state.is_running # Disable during run
)
answer_doc_files: List[st.runtime.uploaded_file_manager.UploadedFile] | None = st.sidebar.file_uploader(
    "Upload Answer Documents for Debate (.txt, .md)",
    type=["txt", "md"],
    accept_multiple_files=True,
    key="a_uploader_v2",
    disabled=st.session_state.is_running # Disable during run
)
st.sidebar.subheader("Parameters")
num_initial_questions = st.sidebar.number_input(
    "Number of Initial Questions to Generate",
    min_value=1, max_value=20, value=3, step=1, key="num_q_v2",
    disabled=st.session_state.is_running # Disable during run
)
st.session_state.output_file_path_config = st.sidebar.text_input(
    "Output Filename (.md)",
    value=st.session_state.output_file_path_config,
    key="output_fname_v2",
    disabled=st.session_state.is_running # Disable during run
)
st.sidebar.subheader("Workflow Control")
col1, col2 = st.sidebar.columns(2)
with col1:
    start_button = st.button("Start V2 Debate",
                             disabled=st.session_state.is_running,
                             key="start_button_v2",
                             use_container_width=True)
with col2:
    reset_button = st.button("Reset",
                             disabled=st.session_state.is_running,
                             key="reset_button_v2",
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
def run_v2_workflow_setup():
    """Handles the setup and prepares the generator for the V2 workflow."""
    st.session_state.error_message = None
    st.session_state.is_running = False
    st.session_state.current_step = 'setup'
    st.session_state.workflow_generator = None
    st.session_state.results_log = []
    st.session_state.setup_done = False
    cleanup_temp_files() # Clean up previous run's files

    add_chat_message(SYSTEM_NAME, "Starting V2 workflow... Validating inputs.")

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
        # Save Question Doc
        with tempfile.NamedTemporaryFile(delete=False, suffix="." + question_doc_file.name.split('.')[-1]) as tmp_q:
            tmp_q.write(question_doc_file.getvalue())
            st.session_state.q_temp_path = tmp_q.name
            logger.info(f"Saved question doc to temp file: {st.session_state.q_temp_path}")

        # Save Answer Docs
        st.session_state.a_temp_paths = [] # Reset list
        for i, answer_doc in enumerate(answer_doc_files):
            with tempfile.NamedTemporaryFile(delete=False, suffix="." + answer_doc.name.split('.')[-1]) as tmp_a:
                tmp_a.write(answer_doc.getvalue())
                st.session_state.a_temp_paths.append(tmp_a.name)
                logger.info(f"Saved answer doc {i+1} to temp file: {tmp_a.name}")

        add_chat_message(SYSTEM_NAME, f"Temporary files saved ({len(st.session_state.a_temp_paths)+1} total). Initializing agents...")
    except Exception as e:
        st.error(f"Error saving uploaded files: {e}")
        logger.error(f"Error saving temp files: {e}", exc_info=True)
        st.session_state.error_message = f"Error saving uploaded files: {e}"
        temp_files_ok = False

    if not temp_files_ok:
        st.session_state.current_step = 'idle'
        add_chat_message(SYSTEM_NAME, f"Workflow setup failed: Error saving files.")
        cleanup_temp_files()
        st.rerun()
        return

    # --- 3. Initialize Agents and Orchestrator --- #
    add_chat_message(SYSTEM_NAME, "Initializing agents...")
    try:
        # Initialize LLM Interface first
        llm_interface = initialize_llm_interface()
        if not llm_interface:
            raise RuntimeError("LLM Interface initialization failed.")

        # Initialize Question Agent
        st.session_state.question_agent = QuestionAgent(llm_interface)

        # Initialize Answer Agents (each initializes own LLMInterface)
        st.session_state.answer_agents = [
            ReportQAAgent() for _ in st.session_state.a_temp_paths
        ]
        add_chat_message(SYSTEM_NAME, f"Initialized {len(st.session_state.answer_agents)} Answer Agents.")

        # Define output path
        output_dir = os.path.join(os.path.dirname(__file__), "data", "output")
        os.makedirs(output_dir, exist_ok=True)
        output_file_path = os.path.join(output_dir, st.session_state.output_file_path_config)
        add_chat_message(SYSTEM_NAME, f"Output log will be saved to: {output_file_path}")

        # Initialize OrchestratorV2
        orchestrator = OrchestratorV2(
            question_agent=st.session_state.question_agent,
            answer_agents=st.session_state.answer_agents,
            output_file_path=output_file_path, # Pass the full path
            llm_interface=llm_interface,
            num_initial_questions=num_initial_questions
        )
        st.session_state.orchestrator_v2 = orchestrator
        add_chat_message(SYSTEM_NAME, "Orchestrator initialized.")

        # --- 4. Get the Generator --- #
        add_chat_message(SYSTEM_NAME, "Preparing interaction generator...")
        st.session_state.workflow_generator = orchestrator.run_debate_interaction(
            question_doc_path=st.session_state.q_temp_path,
            answer_doc_paths=st.session_state.a_temp_paths
        )
        st.session_state.setup_done = True
        st.session_state.current_step = 'running_generator'
        st.session_state.is_running = True
        add_chat_message(SYSTEM_NAME, "Setup complete. Running first step...")
        st.rerun() # Rerun to start processing the generator

    except Exception as e:
        st.error(f"Error during setup: {e}")
        st.session_state.error_message = f"Setup failed: {e}"
        logger.error(f"Setup failed: {e}", exc_info=True)
        st.session_state.current_step = 'idle'
        st.session_state.is_running = False
        add_chat_message(SYSTEM_NAME, f"Workflow setup failed: {e}")
        cleanup_temp_files()
        st.rerun()
        return

# --- Main UI Area (Chat Display) --- #
# Use st.container with height and border directly
chat_container = st.container(height=600, border=True)

# Render messages directly inside this container
with chat_container:
    if not st.session_state.chat_history:
        st.markdown("_Upload documents, set parameters, and click 'Start V2 Debate' to begin._")
    else:
        # Display messages from history
        for message in st.session_state.chat_history:
            role = message["role"]
            content = message["content"]

            # Escape HTML content once
            import html
            escaped_content = html.escape(content).replace("\n", "<br>")

            if role == SYSTEM_NAME:
                # Render System messages directly with custom style (no avatar/placeholder)
                display_content = f"-- {escaped_content} --"
                style = f"background-color: transparent; color: white; text-align: center; width: 90%; margin-left: auto; margin-right: auto; padding: 5px; border-radius: 8px; margin-bottom: 2px; word-wrap: break-word;"
                st.markdown(f'<div style="{style}">{display_content}</div>', unsafe_allow_html=True)
            else:
                # Render other agent messages using st.chat_message with avatars
                avatar = "👤" # Default
                if role == ORCHESTRATOR_NAME: avatar = "🤖"
                elif role == QUESTION_AGENT_NAME: avatar = "❓"
                elif role.startswith(ANSWER_AGENT_NAME): avatar = "📝"
                elif role == SYNTHESIZER_NAME: avatar = "✨"
                
                with st.chat_message(name=role, avatar=avatar):
                    # Determine background color based on role
                    base_role = role
                    if role.startswith(ANSWER_AGENT_NAME):
                        base_role = ANSWER_AGENT_NAME
                    color = AGENT_COLORS.get(base_role, AGENT_COLORS["DEFAULT"])
                    
                    # Define base style
                    style = f"color: #333; padding: 10px; border-radius: 8px; margin-bottom: 5px; word-wrap: break-word;"
                    
                    # Apply role-specific alignment and width
                    if role.startswith(ANSWER_AGENT_NAME):
                        # Answer Agent(s): RIGHT-aligned box
                        style += f" background-color: {color}; width: 70%; margin-left: auto; margin-right: 0;"
                    else:
                        # Other agents (Question, Orchestrator, Synthesizer): LEFT-aligned box
                        style += f" background-color: {color}; width: 70%; margin-right: auto; margin-left: 0;"
                    
                    # Apply the combined style within the chat message
                    st.markdown(f'<div style="{style}">{escaped_content}</div>', unsafe_allow_html=True)


# --- Generator Processing Logic --- #
if st.session_state.is_running and st.session_state.current_step == 'running_generator':
    generator = st.session_state.workflow_generator
    if generator:
        try:
            # Get the next message from the orchestrator generator
            # Use st.spinner while waiting for the next step
            with st.spinner("Processing next step..."):
                speaker, message = next(generator)
            # Display the message
            add_chat_message(speaker, message)
            # Rerun immediately to process the *next* step
            st.rerun()

        except StopIteration:
            # Generator is exhausted, workflow is finished
            add_chat_message(SYSTEM_NAME, "Workflow processing complete.")
            st.session_state.is_running = False
            st.session_state.current_step = 'finished'
            st.session_state.workflow_generator = None # Clean up generator
            cleanup_temp_files() # Clean up temp files at the end
            st.balloons() # Add success indicator
            st.rerun() # Rerun one last time to update button states/status

        except Exception as e:
            # Handle errors *during* generator execution
            error_msg = f"Error during workflow execution: {e}"
            logger.error(f"Error during generator execution: {e}", exc_info=True)
            add_chat_message(SYSTEM_NAME, f"Workflow failed! {error_msg}")
            st.session_state.error_message = error_msg
            st.session_state.is_running = False
            st.session_state.current_step = 'error'
            st.session_state.workflow_generator = None # Clean up generator
            cleanup_temp_files()
            st.rerun() # Rerun to show error
    else:
        # Safety check if generator somehow got lost
        add_chat_message(SYSTEM_NAME, "Error: Workflow generator is missing.")
        st.session_state.is_running = False
        st.session_state.current_step = 'error'
        st.session_state.error_message = "Generator missing."
        st.rerun()

# --- Status Indicators and Button Logic --- #

# Display error message if occurred at any stage
if st.session_state.error_message and st.session_state.current_step == 'error':
    st.error(f"An error occurred: {st.session_state.error_message}")

# Status indicator (outside the chat container)
status_message = "Idle. Ready to start."
if st.session_state.current_step == 'setup':
    status_message = "Setting up workflow..."
    st.info(status_message)
elif st.session_state.is_running and st.session_state.current_step == 'running_generator':
    # Spinner is handled within the generator loop now
    # Could show a general "Running..." message here if desired
    # st.info("Workflow running...")
    pass # Spinner handles visual feedback
elif st.session_state.current_step == 'finished':
    status_message = "Workflow finished successfully!"
    st.success(status_message)
elif st.session_state.current_step == 'error':
    status_message = "Workflow finished with errors."
    # Error message is displayed separately via st.error
    # st.warning(status_message) # Use warning or keep error display only

# Display idle status
if st.session_state.current_step == 'idle':
     st.info(status_message)


# Trigger workflow setup
# Only trigger if idle and button pressed
if start_button and st.session_state.current_step == 'idle':
    st.session_state.workflow_started = True # Mark button pressed
    run_v2_workflow_setup()
    # Setup function calls st.rerun() itself
# <CURSOR_TASK_END>