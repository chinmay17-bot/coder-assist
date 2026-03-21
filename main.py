import streamlit as st
import streamlit.components.v1 as components
import re
# from streamlit_monaco import st_monaco # <-- Upgraded Editor!
from streamlit_ace import st_ace
from langchain_core.messages import HumanMessage

from agent.graph import agent as compiled_graph

# --- HELPER FUNCTION: EXTRACT CODE ---
def extract_code(markdown_text: str, language: str) -> str:
    pattern = rf"```{language}.*?\n(.*?)```"
    match = re.search(pattern, markdown_text, re.DOTALL | re.IGNORECASE)
    return match.group(1) if match else ""

# --- STREAMLIT CONFIG ---
st.set_page_config(page_title="DevTeam Cloud IDE", page_icon="☁️", layout="wide", initial_sidebar_state="collapsed")

# --- INITIALIZE SESSION STATE ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Upgraded to a "Virtual File System" (VFS)
if "vfs" not in st.session_state:
    st.session_state.vfs = {
        "index.html": "<h1>Hello DevTeam!</h1>", 
        "style.css": "body { font-family: sans-serif; }", 
        "script.js": "console.log('Ready');"
    }

if "active_file" not in st.session_state:
    st.session_state.active_file = "index.html"

AVATARS = {"user": "👤", "planner": "🧠", "architect": "📐", "coder": "💻"}

# --- MAIN LAYOUT SPLIT ---
# Left 35% for Chat, Right 65% for the IDE
col_chat, col_ide = st.columns([0.35, 0.65], gap="large")

# ==========================================
# LEFT SIDE: CHAT INTERFACE
# ==========================================
with col_chat:
    st.header("💬 Dev Chat")
    chat_container = st.container(height=700)
    
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"], avatar=AVATARS.get(msg["role"], "🤖")):
                st.markdown(msg["content"])

    if prompt := st.chat_input("What are we building today?"):
        with chat_container:
            with st.chat_message("user", avatar=AVATARS["user"]):
                st.markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "content": prompt})

        inputs = {"user_prompt": prompt}
        config = {"recursion_limit": 100}

        with chat_container:
            with st.spinner("The DevTeam is coding..."):
                for output in compiled_graph.stream(inputs, config):
                    for node_name, state_update in output.items():
                        if "messages" in state_update and state_update["messages"]:
                            latest_msg = state_update["messages"][-1].content
                            role = node_name.lower()
                            
                            with st.chat_message(role, avatar=AVATARS.get(role, "🤖")):
                                st.markdown(f"**{role.capitalize()}**\n\n{latest_msg}")
                            
                            st.session_state.chat_history.append({"role": role, "content": latest_msg})

                            # Intercept Code and save to Virtual File System
                            if role == "coder":
                                html_code = extract_code(latest_msg, "html")
                                css_code = extract_code(latest_msg, "css")
                                js_code = extract_code(latest_msg, "javascript") or extract_code(latest_msg, "js")
                                
                                if html_code: st.session_state.vfs["index.html"] = html_code
                                if css_code: st.session_state.vfs["style.css"] = css_code
                                if js_code: st.session_state.vfs["script.js"] = js_code
                
                # Graph is done, refresh UI
                st.rerun()

# ==========================================
# RIGHT SIDE: THE CLOUD IDE
# ==========================================
with col_ide:
    st.header("☁️ Cloud IDE Workspace")
    
    # Split the IDE area into Explorer (20%) and Editor (80%)
    col_explorer, col_editor = st.columns([0.2, 0.8], gap="small")
    
    # --- 1. THE FILE EXPLORER ---
    with col_explorer:
        st.markdown("📂 **EXPLORER**")
        st.divider()
        
        # Create a clean button list for the Virtual File System
        for filename in st.session_state.vfs.keys():
            # Highlight the currently active file
            btn_type = "primary" if st.session_state.active_file == filename else "secondary"
            if st.button(f"📄 {filename}", type=btn_type, use_container_width=True):
                st.session_state.active_file = filename
                st.rerun()

    # --- 2. THE ACE EDITOR (Fix applied here!) ---
    with col_editor:
        active_file = st.session_state.active_file
        
        # Determine language for Ace based on file extension
        ext = active_file.split(".")[-1]
        language_map = {"html": "html", "css": "css", "js": "javascript"}
        ace_lang = language_map.get(ext, "text")
        
        # We use a dynamic key so the editor actually refreshes when switching files!
        dynamic_key = f"editor_{active_file}_{len(st.session_state.chat_history)}"
        
        # Render the Ace Editor
        edited_code = st_ace(
            value=st.session_state.vfs.get(active_file, ""),
            language=ace_lang,
            theme="monokai", # Beautiful dark mode theme
            height=450,
            key=dynamic_key,
            auto_update=True
        )
        
        # Save manual user edits back to the VFS
        if edited_code and edited_code != st.session_state.vfs[active_file]:
            st.session_state.vfs[active_file] = edited_code
            st.rerun()
            
    # --- 3. TERMINAL / PREVIEW PANEL ---
    st.divider()
    tab_preview, tab_terminal = st.tabs(["🌐 Live Browser Preview", "🖥️ Terminal Logs"])
    
    with tab_preview:
        if st.session_state.vfs.get("index.html"):
            # Stitch the VFS files together for the live browser
            combined_code = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>{st.session_state.vfs.get('style.css', '')}</style>
            </head>
            <body>
                {st.session_state.vfs.get('index.html', '')}
                <script>{st.session_state.vfs.get('script.js', '')}</script>
            </body>
            </html>
            """
            components.html(combined_code, height=400, scrolling=True)
        else:
            st.info("No index.html found in the workspace.")
            
    with tab_terminal:
        st.code("DevTeam Terminal v1.0\n> Local environment ready...\n> Waiting for AI executions...", language="bash")