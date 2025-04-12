import streamlit as st
import streamlit.components.v1 as components

def auto_scroll():
    """
    Create a component for auto-scrolling Streamlit containers.
    Targets the specific container ID we added to the streamlit_app.py.
    """
    # Direct scroll implementation targeting our specific container
    scroll_js = """
    <script>
    // Function to find and scroll our specific chat container
    function scrollToBottom() {
        // First try: Find by ID (most direct)
        const container = document.getElementById('chat-messages-container');
        if (container) {
            // Find the scrollable parent of our container
            let scrollableParent = container;
            while (scrollableParent && scrollableParent !== document.body) {
                // Check if this element or any parent is scrollable
                const style = window.getComputedStyle(scrollableParent);
                const isScrollable = style.overflowY === 'auto' || 
                                    style.overflowY === 'scroll' ||
                                    scrollableParent.scrollHeight > scrollableParent.clientHeight;
                
                if (isScrollable && scrollableParent.clientHeight > 50) {
                    // Found a scrollable parent, scroll it
                    scrollableParent.scrollTop = scrollableParent.scrollHeight;
                    console.log('Scrolled container:', scrollableParent);
                    break;
                }
                
                scrollableParent = scrollableParent.parentElement;
            }
        }
        
        // Second try: Find all reasonably sized divs that might be scrollable
        const allDivs = document.querySelectorAll('div');
        allDivs.forEach(div => {
            // Only target divs that are likely our container (reasonably sized)
            if (div.clientHeight > 100 && div.scrollHeight > div.clientHeight) {
                div.scrollTop = div.scrollHeight;
            }
        });
        
        // Third try: Find the last message and scroll to it
        const messages = document.querySelectorAll('.chat-message');
        if (messages.length > 0) {
            const lastMessage = messages[messages.length - 1];
            try {
                lastMessage.scrollIntoView({block: 'end'});
            } catch (e) {
                console.error('ScrollIntoView failed:', e);
            }
        }
    }
    
    // Execute multiple times with increasing delays
    scrollToBottom();
    setTimeout(scrollToBottom, 100);
    setTimeout(scrollToBottom, 300);
    setTimeout(scrollToBottom, 800);
    </script>
    """
    
    # Inject the scrolling JavaScript 
    components.html(scroll_js, height=0, width=0) 