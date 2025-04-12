import streamlit as st
import os
import tempfile
import logging
import sys
import time

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

# --- Constants for Agent Names ---
ORCHESTRATOR_NAME = "Orchestrator"
ANSWER_AGENT_NAME = "Answer Agent"
QUESTION_AGENT_NAME = "Question Agent"
SYSTEM_NAME = "System"

# --- Auto-scroll JavaScript for Chat Container ---
auto_scroll_js = """
<script>
// More aggressive auto-scroll function that tries multiple approaches
function forceScrollToBottom() {
    try {
        // Method 1: Try direct ID access
        const container = document.getElementById('chat-container');
        if (container) {
            container.scrollTop = container.scrollHeight;
            console.log('Direct scroll applied');
        }
        
        // Method 2: Try to find containers across all possible iframe contexts
        let allContainers = [];
        
        // Current document
        allContainers = allContainers.concat(Array.from(document.querySelectorAll('#chat-container')));
        allContainers = allContainers.concat(Array.from(document.querySelectorAll('div[style*="overflow-y: scroll"]')));
        
        // Parent document (if we're in an iframe)
        try {
            if (window.parent && window.parent.document) {
                allContainers = allContainers.concat(Array.from(window.parent.document.querySelectorAll('#chat-container')));
                allContainers = allContainers.concat(Array.from(window.parent.document.querySelectorAll('div[style*="overflow-y: scroll"]')));
            }
        } catch (e) { console.error('Parent access error:', e); }
        
        // Try to access all iframes in the page
        try {
            const iframes = window.parent.document.querySelectorAll('iframe');
            for (const iframe of iframes) {
                try {
                    if (iframe.contentDocument) {
                        allContainers = allContainers.concat(Array.from(iframe.contentDocument.querySelectorAll('#chat-container')));
                        allContainers = allContainers.concat(Array.from(iframe.contentDocument.querySelectorAll('div[style*="overflow-y: scroll"]')));
                    }
                } catch (e) { console.error('iframe access error:', e); }
            }
        } catch (e) { console.error('iframes query error:', e); }
        
        // Scroll all potential containers
        for (const container of allContainers) {
            if (container && container.scrollHeight > container.clientHeight) {
                container.scrollTop = container.scrollHeight;
                console.log('Container scrolled:', container);
            }
        }
    } catch (e) {
        console.error('Scroll error:', e);
    }
}

// Execute with multiple delays in a wide time range
forceScrollToBottom();
setTimeout(forceScrollToBottom, 100);
setTimeout(forceScrollToBottom, 300);
setTimeout(forceScrollToBottom, 500);
setTimeout(forceScrollToBottom, 800);
setTimeout(forceScrollToBottom, 1200);
setTimeout(forceScrollToBottom, 2000);

// Also capture all possible events that could signal DOM is ready
window.addEventListener('load', forceScrollToBottom);
window.addEventListener('DOMContentLoaded', forceScrollToBottom);
document.addEventListener('readystatechange', forceScrollToBottom);
if (window.frameElement) {
    window.frameElement.addEventListener('load', forceScrollToBottom);
}

// Also add a persistent interval to check regularly
setInterval(forceScrollToBottom, 2000);
</script>
"""

# --- Streamlit App --- #
st.set_page_config(layout="wide")
st.title("Automated Q&A Orchestration Chat")

st.sidebar.header("Configuration")

# --- Session State Initialization for Automated Flow ---
def initialize_session_state(force_reset=False):
    """Initialize or reset session state variables.
    
    Args:
        force_reset: If True, will reset all values even if they already exist.
    """
    defaults = {
        'workflow_started': False,
        'setup_done': False,
        'is_running': False,
        'current_step': 'idle',
        'agents_initialized': False,
        'orchestrator': None,
        'question_agent': None,
        'answer_agent': None,
        'answer_doc_content': None,
        'initial_questions': [],
        'current_initial_q_index': -1,
        'current_follow_up_count': 0,
        'current_question': None,
        'current_answer': None,
        'current_satisfaction': None,
        'current_reason': None,
        'chat_history': [],
        'error_message': None,
        'q_temp_path': None,
        'a_temp_path': None,
        'max_follow_ups_config': 1
    }
    for key, default_value in defaults.items():
        if force_reset or key not in st.session_state:
            st.session_state[key] = default_value

# Initial initialization
initialize_session_state()

# File Uploaders
st.sidebar.subheader("Input Documents")
question_doc_file = st.sidebar.file_uploader("Upload Document for Question Generation (.txt, .md)", type=["txt", "md"], key="q_uploader")
answer_doc_file = st.sidebar.file_uploader("Upload Document for Answering (.txt, .md)", type=["txt", "md"], key="a_uploader")

# Parameters
st.sidebar.subheader("Parameters")
num_initial_questions = st.sidebar.number_input("Number of Initial Questions to Generate", min_value=1, max_value=20, value=3, step=1)
st.session_state.max_follow_ups_config = st.sidebar.number_input("Max Follow-up Attempts per Question", min_value=0, max_value=5, value=st.session_state.max_follow_ups_config, step=1)

# --- Workflow Control Buttons --- #
col1, col2 = st.sidebar.columns(2)
with col1:
    start_button = st.sidebar.button("Start Workflow", 
                                     disabled=st.session_state.workflow_started or st.session_state.is_running, 
                                     key="start_button")
with col2:
    reset_button = st.sidebar.button("Reset", 
                                     disabled=not st.session_state.workflow_started,
                                     key="reset_button")

# --- Initialization Functions (cached for efficiency) ---
def initialize_agents():
    """Initializes the agents and LLM interface."""
    try:
        question_agent = QuestionAgent()
        answer_agent = AnswerAgent()
        llm_interface = LLMInterface(model_key=MODEL_NAME)
        st.session_state.question_agent = question_agent
        st.session_state.answer_agent = answer_agent
        return question_agent, answer_agent, llm_interface
    except Exception as e:
        st.error(f"Error initializing agents: {e}")
        logger.error(f"Agent initialization failed: {e}", exc_info=True)
        return None, None, None

# --- Helper Function --- #
def cleanup_temp_files():
    """Cleans up temporary files stored in session state."""
    paths_to_clean = ['q_temp_path', 'a_temp_path']
    for path_key in paths_to_clean:
        path = st.session_state.get(path_key)
        if path and os.path.exists(path):
            try:
                os.unlink(path)
                logger.info(f"Deleted temp file: {path}")
                st.session_state[path_key] = None
            except Exception as e:
                logger.error(f"Error deleting temp file {path}: {e}")

def add_chat_message(role, content):
    """Appends a message to the chat history and triggers auto-scroll."""
    st.session_state.chat_history.append({"role": role, "content": content})
    # Add a small delay to ensure message is in DOM before scroll
    time.sleep(0.1)
    
    # Trigger auto-scroll after each message
    st.components.v1.html(auto_scroll_js, height=0, width=0)

def reset_state():
    """Resets the application state and cleans up resources."""
    try:
        # Clean up temp files
        cleanup_temp_files()
        
        # First clear key workflow components
        st.session_state.orchestrator = None
        st.session_state.question_agent = None
        st.session_state.answer_agent = None
        st.session_state.answer_doc_content = None
        
        # Clear all messages from chat history
        st.session_state.chat_history = []
        
        # Clear questions and other state
        st.session_state.initial_questions = []
        st.session_state.current_initial_q_index = -1
        st.session_state.current_follow_up_count = 0
        st.session_state.current_question = None
        st.session_state.current_answer = None
        
        # Reset workflow state flags
        st.session_state.workflow_started = False
        st.session_state.setup_done = False
        st.session_state.is_running = False
        st.session_state.current_step = 'idle'
        st.session_state.agents_initialized = False
        st.session_state.error_message = None
        
        logger.info("Application state has been fully reset")
    except Exception as e:
        logger.error(f"Error during reset: {e}")
    
    # Force a complete page rerun
    st.rerun()

if reset_button:
    reset_state()

# --- Perform Setup on Start Button Click --- #
def perform_setup():
    """Handles the initial setup process."""
    # Clear any old state to ensure we're starting fresh
    st.session_state.orchestrator = None
    st.session_state.question_agent = None
    st.session_state.answer_agent = None
    st.session_state.answer_doc_content = None
    st.session_state.agents_initialized = False
    st.session_state.chat_history = []
    st.session_state.error_message = None
    
    # Set initial workflow state
    st.session_state.workflow_started = True
    st.session_state.is_running = False  # Will set to True only after successful setup
    add_chat_message(SYSTEM_NAME, "Starting workflow setup...")

    try:
        add_chat_message(SYSTEM_NAME, "Initializing agents...")
        # Create fresh agent instances each time
        question_agent, answer_agent, llm_interface = initialize_agents()
        
        if not question_agent or not answer_agent or not llm_interface:
            raise Exception("Failed to initialize one or more agents")
        
        st.session_state.question_agent = question_agent
        st.session_state.answer_agent = answer_agent
        st.session_state.agents_initialized = True
        add_chat_message(SYSTEM_NAME, "Agents initialized.")

        add_chat_message(SYSTEM_NAME, "Processing input documents...")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".md", mode='wb') as q_temp:
            q_temp.write(question_doc_file.getvalue())
            st.session_state.q_temp_path = q_temp.name
        with tempfile.NamedTemporaryFile(delete=False, suffix=".md", mode='wb') as a_temp:
            a_temp.write(answer_doc_file.getvalue())
            st.session_state.a_temp_path = a_temp.name
        add_chat_message(SYSTEM_NAME, "Input documents processed.")

        add_chat_message(ORCHESTRATOR_NAME, "Initializing...")
        orchestrator = Orchestrator(
            question_agent=question_agent,
            answer_agent=answer_agent,
            llm_interface=llm_interface,
            max_follow_ups=st.session_state.max_follow_ups_config
        )
        st.session_state.orchestrator = orchestrator

        add_chat_message(ORCHESTRATOR_NAME, f"Loading answer document: {os.path.basename(st.session_state.a_temp_path)}")
        orchestrator.load_answer_doc(st.session_state.a_temp_path)
        st.session_state.answer_doc_content = orchestrator.answer_doc_content
        add_chat_message(ORCHESTRATOR_NAME, "Answer document loaded.")

        add_chat_message(QUESTION_AGENT_NAME, f"Generating {num_initial_questions} initial questions from {os.path.basename(st.session_state.q_temp_path)}...")
        initial_questions = orchestrator.generate_initial_questions(
            question_doc_path=st.session_state.q_temp_path,
            num_questions=num_initial_questions
        )
        st.session_state.initial_questions = initial_questions
        add_chat_message(QUESTION_AGENT_NAME, f"Generated {len(initial_questions)} questions.")

        if not initial_questions:
            error_msg = "No initial questions were generated. Workflow cannot proceed."
            add_chat_message(SYSTEM_NAME, f"Error: {error_msg}")
            st.warning("No initial questions were generated.")
            st.session_state.setup_done = False
            st.session_state.current_step = 'error'
            st.session_state.error_message = error_msg
            st.session_state.is_running = False
            return False
        else:
            st.session_state.current_initial_q_index = 0
            st.session_state.current_follow_up_count = 0
            st.session_state.current_question = initial_questions[0]
            st.session_state.current_answer = None
            st.session_state.current_satisfaction = None
            st.session_state.current_reason = None
            st.session_state.current_step = 'show_initial_question'
            st.session_state.setup_done = True
            add_chat_message(SYSTEM_NAME, "Setup complete. Starting automated execution...")
            st.success("Setup complete.")
            return True

    except Exception as e:
        error_msg = f"An unexpected error occurred during setup: {e}"
        add_chat_message(SYSTEM_NAME, f"Error: {error_msg}")
        st.error(error_msg)
        logger.error(f"Workflow setup failed: {e}", exc_info=True)
        cleanup_temp_files()
        st.session_state.setup_done = False
        st.session_state.workflow_started = False
        st.session_state.is_running = False
        st.session_state.current_step = 'error'
        st.session_state.error_message = f"Setup failed: {e}"
        return False

if start_button:
    # Clear any previous error state first
    st.session_state.error_message = None
    st.session_state.current_step = 'idle'
    
    if question_doc_file is not None and answer_doc_file is not None:
        # Explicitly reset chat history and component states before setup
        st.session_state.chat_history = []
        st.session_state.orchestrator = None
        st.session_state.question_agent = None
        st.session_state.answer_agent = None
        
        # Run setup process
        setup_successful = perform_setup()
        
        if setup_successful:
            st.session_state.is_running = True
            st.rerun()
    else:
        st.warning("Please upload both documents before starting.")

# --- State Machine Logic for Automated Workflow Step ---
def run_single_workflow_step():
    """Executes one step of the automated workflow."""
    current_step = st.session_state.current_step
    logger.info(f"Running auto step. Current state: {current_step}")

    orchestrator = st.session_state.orchestrator
    answer_agent = st.session_state.answer_agent
    answer_doc_content = st.session_state.answer_doc_content

    if not orchestrator or not answer_agent or answer_doc_content is None:
        error_msg = "Workflow components missing unexpectedly. Resetting."
        add_chat_message(SYSTEM_NAME, f"Error: {error_msg}")
        st.error(error_msg)
        st.session_state.current_step = 'error'
        st.session_state.error_message = "Core components missing."
        st.session_state.is_running = False
        return

    try:
        if current_step == 'show_initial_question':
            q_idx = st.session_state.current_initial_q_index
            q_text = st.session_state.current_question
            add_chat_message(ORCHESTRATOR_NAME, f"**Initial Question {q_idx + 1}:**\n{q_text}")
            st.session_state.current_step = 'get_answer'

        elif current_step == 'get_answer':
            with st.spinner("Generating answer..."):
                add_chat_message(ORCHESTRATOR_NAME, "Asking Answer Agent...")
                st.session_state.current_answer = answer_agent.ask_with_content(
                    st.session_state.current_question, answer_doc_content
                )
            add_chat_message(ANSWER_AGENT_NAME, st.session_state.current_answer)
            st.session_state.current_step = 'check_satisfaction'

        elif current_step == 'check_satisfaction':
            with st.spinner("Checking satisfaction..."):
                add_chat_message(ORCHESTRATOR_NAME, "Evaluating answer satisfaction...")
                satisfied, reason = orchestrator.check_satisfaction(
                    st.session_state.current_question,
                    st.session_state.current_answer
                )
                st.session_state.current_satisfaction = satisfied
                st.session_state.current_reason = reason
                status_text = "Satisfied" if satisfied else "Unsatisfied"
                reason_text = reason or "N/A"
                add_chat_message(ORCHESTRATOR_NAME, f"**Assessment:** {status_text}\n**Reason:** {reason_text}")
            if satisfied:
                add_chat_message(ORCHESTRATOR_NAME, "Answer is satisfactory. Moving to next question.")
                st.session_state.current_step = 'next_initial_question'
            else:
                if st.session_state.current_follow_up_count < st.session_state.max_follow_ups_config:
                    add_chat_message(ORCHESTRATOR_NAME, "Answer is unsatisfactory. Generating follow-up question.")
                    st.session_state.current_step = 'get_follow_up'
                else:
                    add_chat_message(ORCHESTRATOR_NAME, f"Answer unsatisfactory, but max follow-ups ({st.session_state.max_follow_ups_config}) reached. Moving to next question.")
                    st.session_state.current_step = 'next_initial_question'

        elif current_step == 'get_follow_up':
            with st.spinner("Generating follow-up question..."):
                follow_up_q = orchestrator.generate_follow_up(
                    st.session_state.current_question,
                    st.session_state.current_answer
                )
            if follow_up_q:
                st.session_state.current_follow_up_count += 1
                st.session_state.current_question = follow_up_q
                st.session_state.current_answer = None
                st.session_state.current_satisfaction = None
                st.session_state.current_reason = None
                add_chat_message(ORCHESTRATOR_NAME, f"**Follow-up Question {st.session_state.current_follow_up_count}:**\n{follow_up_q}")
                st.session_state.current_step = 'get_answer'
            else:
                add_chat_message(ORCHESTRATOR_NAME, "Failed to generate a follow-up question. Moving to next initial question.")
                st.error("Failed to generate a follow-up question.")
                st.session_state.current_step = 'next_initial_question'

        elif current_step == 'next_initial_question':
            st.session_state.current_initial_q_index += 1
            q_idx = st.session_state.current_initial_q_index
            if q_idx < len(st.session_state.initial_questions):
                add_chat_message(SYSTEM_NAME, f"--- Preparing Initial Question {q_idx + 1} --- ")
                st.session_state.current_follow_up_count = 0
                st.session_state.current_question = st.session_state.initial_questions[q_idx]
                st.session_state.current_answer = None
                st.session_state.current_satisfaction = None
                st.session_state.current_reason = None
                st.session_state.current_step = 'show_initial_question'
            else:
                # Add completion message and set workflow to finished state
                add_chat_message(SYSTEM_NAME, "--- All initial questions processed! Workflow Complete. ---")
                
                # Force an extra scroll for the final message
                st.components.v1.html(auto_scroll_js, height=0, width=0)
                
                st.success("Workflow Complete!")
                st.session_state.current_step = 'finished'
                st.session_state.is_running = False
                cleanup_temp_files()
                
                # Extra delay and auto-scroll to catch the final message
                time.sleep(0.8)
                st.components.v1.html(auto_scroll_js, height=0, width=0)
                
                # One more rerun with delayed auto-scroll to ensure final message is visible
                time.sleep(0.5)
                st.rerun()

        elif current_step in ['idle', 'finished', 'error']:
             logger.warning(f"run_single_workflow_step called in terminal state: {current_step}")
             st.session_state.is_running = False

    except ContextLengthError as e:
        error_msg = f"Context Length Error: {e}. Please check document sizes or content."
        add_chat_message(SYSTEM_NAME, f"Error: {error_msg}")
        st.error(error_msg)
        st.session_state.current_step = 'error'
        st.session_state.error_message = error_msg
        st.session_state.is_running = False
    except Exception as e:
        error_msg = f"An unexpected error occurred during step {current_step}: {e}"
        add_chat_message(SYSTEM_NAME, f"Error: {error_msg}")
        st.error(error_msg)
        logger.error(f"Error during step {current_step}: {e}", exc_info=True)
        st.session_state.current_step = 'error'
        st.session_state.error_message = error_msg
        st.session_state.is_running = False

# --- Main Execution Loop --- #
# Display chat container header
st.header("Conversation Log")

# Create a fixed-height container for status messages
status_container = st.container(height=60)

# Status indicator - always in the same fixed container
with status_container:
    if st.session_state.is_running:
        st.info(f"Workflow running - Step: {st.session_state.current_step}")
    elif st.session_state.current_step == 'finished':
        st.success("Workflow complete!")
    elif st.session_state.current_step == 'error':
        st.error(f"Error: {st.session_state.error_message}")
    else:
        st.info("Upload documents and click 'Start Workflow' to begin.")

# Create a single fixed-height container with consistent dimensions and spacing
container_html = f'''
<div id="chat-container" style="
    height: 70vh; 
    min-height: 400px;
    max-height: 800px;
    overflow-y: scroll; 
    border: 1px solid #ccc; 
    border-radius: 5px; 
    padding: 15px; 
    margin: 10px 0 20px 0;
    background-color: white;
    display: block;
    position: relative;
    box-sizing: border-box;
    width: 100%;
">
'''

# Add message styling directly
container_html += '''
<style>
.msg { 
    padding: 10px; 
    margin-bottom: 10px; 
    border-radius: 5px;
    width: 35%; /* Set default width to 35% */
    box-sizing: border-box;
    display: block; 
}

/* Left aligned messages (Orchestrator & Question Agent) */
.msg-left {
    float: left;
    clear: both;
    text-align: left;
    margin-right: auto;
    border-bottom-left-radius: 2px; /* Sharper corner on bottom left */
}

/* Right aligned messages (Answer Agent) */
.msg-right {
    float: right;
    clear: both;
    text-align: left;
    margin-left: auto;
    border-bottom-right-radius: 2px; /* Sharper corner on bottom right */
}

/* System messages are centered and full width for clarity */
.msg-system {
    width: 90%;
    margin-left: auto;
    margin-right: auto;
    clear: both;
    text-align: center;
    font-size: 0.9em;
    color: #666;
}

/* Color styling */
.system { background-color: transparent; }
.orchestrator { background-color: #e6f7ff; }
.question { background-color: #f0f7ff; }
.answer { background-color: #f5f5f5; }

/* Force scrollbar to always be visible */
#chat-container::-webkit-scrollbar {
    width: 10px;
    display: block !important;
}

#chat-container::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 5px;
}

#chat-container::-webkit-scrollbar-thumb {
    background: #888;
    border-radius: 5px;
}

#chat-container::-webkit-scrollbar-thumb:hover {
    background: #555;
}

/* Add clearfix to handle floated messages */
.clearfix::after {
    content: "";
    clear: both;
    display: table;
}
</style>
'''

# Add all messages to the container
if st.session_state.chat_history:
    for message in st.session_state.chat_history:
        role = message["role"]
        content = message["content"]
        
        # Map role to CSS class
        role_class = "system"
        alignment_class = "msg-system"
        
        if role == ORCHESTRATOR_NAME:
            role_class = "orchestrator"
            alignment_class = "msg-left"
        elif role == QUESTION_AGENT_NAME:
            role_class = "question"
            alignment_class = "msg-left"
        elif role == ANSWER_AGENT_NAME:
            role_class = "answer"
            alignment_class = "msg-right"
        
        # Add the message with appropriate alignment class
        container_html += f'<div class="msg {role_class} {alignment_class}"><strong>{role}</strong><br>{content}</div>'
    
    # Add clearfix to ensure container expands properly
    container_html += '<div class="clearfix"></div>'
else:
    # Single-line placeholder with no whitespace or line breaks
    container_html += '<div style="display:flex;justify-content:center;align-items:center;height:100%;color:#888;"><p>Messages will appear here when the workflow starts.</p></div>'

# Close the container
container_html += '</div>'

# Render the container HTML - always the same fixed size
st.markdown(container_html, unsafe_allow_html=True)

# Only run a single workflow step per app rerun
if st.session_state.is_running and st.session_state.current_step not in ['finished', 'error', 'idle']:
    try:
        # Run only one step
        run_single_workflow_step()
        
        # Add a message separator to help visually track progress
        if st.session_state.current_step != 'finished':
            add_chat_message(SYSTEM_NAME, f"--- Processing next step: {st.session_state.current_step} ---")
        
        # Add another auto-scroll call after adding new messages
        st.components.v1.html(auto_scroll_js, height=0, width=0)
        
        # Small delay before rerun to allow DOM updates and scrolling to complete
        time.sleep(0.8)
        
        # Force a rerun to update the UI
        st.rerun()
    except Exception as e:
        st.error(f"Error in workflow execution: {str(e)}")
        st.session_state.current_step = 'error'
        st.session_state.is_running = False
        st.session_state.error_message = str(e)
        logger.error(f"Workflow execution error: {e}", exc_info=True)

# --- Debug Info --- #
st.sidebar.markdown("--- Debug Info ---")
st.sidebar.write(f"Workflow Started: `{st.session_state.workflow_started}`")
st.sidebar.write(f"Setup Done: `{st.session_state.setup_done}`")
st.sidebar.write(f"Is Running: `{st.session_state.is_running}`")
st.sidebar.write(f"Current Step: `{st.session_state.current_step}`")
st.sidebar.write(f"Initial Q Index: `{st.session_state.current_initial_q_index}`")
st.sidebar.write(f"Follow-up Count: `{st.session_state.current_follow_up_count}`")
