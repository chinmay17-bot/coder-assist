import streamlit as st
import streamlit.components.v1 as components
import re
from streamlit_ace import st_ace  
from langchain_core.messages import HumanMessage

# Import your compiled graph
from agent.graph import agent as compiled_graph

# --- HELPER FUNCTION: EXTRACT CODE ---
def extract_code(markdown_text: str, language: str) -> str:
    pattern = rf"```{language}.*?\n(.*?)```"
    match = re.search(pattern, markdown_text, re.DOTALL | re.IGNORECASE)
    return match.group(1) if match else ""

st.set_page_config(page_title="DevTeam AI", page_icon="👨‍💻", layout="wide")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "project_files" not in st.session_state:
    st.session_state.project_files = {"html": "", "css": "", "js": ""}

AVATARS = {"user": "👤", "planner": "🧠", "architect": "📐", "coder": "💻"}

st.title(" AI DevTeam Workspace")

# --- CREATE SIDE-BY-SIDE COLUMNS ---
# col_chat gets 40% of the screen, col_workspace gets 60%
col_chat, col_workspace = st.columns([0.4, 0.6], gap="large")

# ==========================================
# LEFT SIDE: CHAT INTERFACE
# ==========================================
with col_chat:
    st.header("💬 Chat")
    
    # Create a scrollable container for chat messages
    chat_container = st.container(height=600)
    
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"], avatar=AVATARS.get(msg["role"], "🤖")):
                st.markdown(msg["content"])

    # Chat input at the bottom of the column
    if prompt := st.chat_input("What should we build or change?"):
        with chat_container:
            with st.chat_message("user", avatar=AVATARS["user"]):
                st.markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "content": prompt})

        inputs = {"user_prompt": prompt}
        config = {"recursion_limit": 100}

        with chat_container:
            with st.spinner("The team is working..."):
                # 1. Run the entire stream without interrupting it
                for output in compiled_graph.stream(inputs, config):
                    for node_name, state_update in output.items():
                        if "messages" in state_update and state_update["messages"]:
                            latest_msg = state_update["messages"][-1].content
                            role = node_name.lower()
                            
                            with st.chat_message(role, avatar=AVATARS.get(role, "🤖")):
                                st.markdown(f"**{role.capitalize()}**\n\n{latest_msg}")
                            
                            st.session_state.chat_history.append({"role": role, "content": latest_msg})

                            # Intercept Code
                            if role == "coder":
                                html_code = extract_code(latest_msg, "html")
                                css_code = extract_code(latest_msg, "css")
                                js_code = extract_code(latest_msg, "javascript") or extract_code(latest_msg, "js")
                                
                                if html_code: st.session_state.project_files["html"] = html_code
                                if css_code: st.session_state.project_files["css"] = css_code
                                if js_code: st.session_state.project_files["js"] = js_code
                
                # 2. Safely rerun the UI *after* the graph is completely finished
                st.rerun()

# ==========================================
# RIGHT SIDE: EDITOR & PREVIEW
# ==========================================
with col_workspace:
    tab_editor, tab_preview = st.tabs(["📝 Code Editor", "🖥️ Live Preview"])

    # --- THE INTERACTIVE CODE EDITOR ---
    with tab_editor:
        # Let the user choose which file to edit
        file_to_edit = st.selectbox("Select file:", ["html", "css", "js"], index=0)
        
        # Map file extensions to ACE editor syntax highlighting
        language_map = {"html": "html", "css": "css", "js": "javascript"}
        
        # Render the code editor
        edited_code = st_ace(
            value=st.session_state.project_files[file_to_edit],
            language=language_map[file_to_edit],
            theme="monokai", # Dark mode theme!
            key=f"ace_editor_{file_to_edit}",
            height=500,
            show_gutter=True,
            auto_update=True # Updates session state as you type
        )
        
        # If the user types in the editor, save it back to our project state!
        if edited_code != st.session_state.project_files[file_to_edit]:
            st.session_state.project_files[file_to_edit] = edited_code
            # Force a rerun so the Live Preview tab updates immediately
            st.rerun()

    # --- THE LIVE PREVIEW ---
    with tab_preview:
        if st.session_state.project_files["html"]:
            combined_code = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>{st.session_state.project_files['css']}</style>
            </head>
            <body>
                {st.session_state.project_files['html']}
                <script>{st.session_state.project_files['js']}</script>
            </body>
            </html>
            """
            components.html(combined_code, height=600, scrolling=True)
        else:
            st.info("Your preview will appear here once the Coder writes the HTML.")