import streamlit as st
import streamlit.components.v1 as components
import re
from streamlit_ace import st_ace
from langchain_core.messages import HumanMessage

from agent.graph import agent as compiled_graph

# --- HELPER FUNCTION: EXTRACT CODE ---
def extract_code(markdown_text: str, language: str) -> str:
    pattern = rf"```{language}.*?\n(.*?)```"
    match = re.search(pattern, markdown_text, re.DOTALL | re.IGNORECASE)
    return match.group(1) if match else ""

# --- STREAMLIT CONFIG ---
st.set_page_config(page_title="DevTeam IDE", page_icon="⚡", layout="wide")

# --- CUSTOM CSS FOR FIXED ZERO-MARGIN CHAT ---
st.markdown("""
    <style>
        /* 1. Remove master padding to push the layout completely flush */
        .block-container { 
            padding: 0rem !important; 
            max-width: 100% !important; 
        }
        header { visibility: hidden; display: none; }
        
        /* 2. Target the Chat Column to make it sticky and full-height */
        div[data-testid="column"]:nth-of-type(1) {
            position: sticky;
            top: 0;
            height: 100vh;
            background-color: #121212; 
            border-right: 1px solid #333; 
            padding: 1.5rem 1rem; 
            overflow-y: hidden;
        }
        
        /* 3. Add padding to the IDE column */
        div[data-testid="column"]:nth-of-type(2) {
            padding: 1.5rem 2rem;
        }
        
        /* 4. Style the file explorer buttons */
        .stButton>button { text-align: left; border: none; background-color: transparent; border-radius: 0; padding-left: 5px;}
        .stButton>button:hover { background-color: rgba(255,255,255,0.1); }
    </style>
""", unsafe_allow_html=True)

# --- INITIALIZE SESSION STATE ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "vfs" not in st.session_state:
    st.session_state.vfs = {
        "index.html": "<!-- DevTeam Workspace -->\n<h1>Hello World</h1>", 
        "style.css": "body {\n  background-color: #1e1e1e;\n  color: #ffffff;\n  font-family: sans-serif;\n}", 
        "script.js": "console.log('Environment Ready');"
    }

if "active_file" not in st.session_state:
    st.session_state.active_file = "index.html"

# Minimal Avatars
AVATARS = {"user": "👤", "planner": "📋", "architect": "📐", "coder": "⚡"}

# --- MAIN LAYOUT SPLIT ---
col_chat, col_ide = st.columns([0.25, 0.75], gap="small")

# ==========================================
# LEFT SIDE: FIXED CHAT
# ==========================================
with col_chat:
    st.markdown("### ⚡ Copilot Chat")
    
    chat_container = st.container(height=700, border=False)
    
    with chat_container:
        if not st.session_state.chat_history:
            st.caption("No active tasks. Ask me to build something!")
            
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"], avatar=AVATARS.get(msg["role"], "🤖")):
                st.markdown(msg["content"])

    if prompt := st.chat_input("Ask Copilot..."):
        with chat_container:
            with st.chat_message("user", avatar=AVATARS["user"]):
                st.markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "content": prompt})

        inputs = {"user_prompt": prompt}
        config = {"recursion_limit": 100}

        with chat_container:
            with st.spinner("Thinking..."):
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
                                
                                if html_code: st.session_state.vfs["index.html"] = html_code
                                if css_code: st.session_state.vfs["style.css"] = css_code
                                if js_code: st.session_state.vfs["script.js"] = js_code
                st.rerun()

# ==========================================
# RIGHT SIDE: MAIN CLOUD IDE
# ==========================================
with col_ide:
    col_explorer, col_editor = st.columns([0.15, 0.85], gap="small")

    # --- 1. THE FILE EXPLORER ---
    with col_explorer:
        st.caption("EXPLORER")
        
        for filename in st.session_state.vfs.keys():
            btn_type = "primary" if st.session_state.active_file == filename else "secondary"
            if st.button(f"📄 {filename}", type=btn_type, use_container_width=True):
                st.session_state.active_file = filename
                st.rerun()

    # --- 2. THE ACE EDITOR ---
    with col_editor:
        active_file = st.session_state.active_file
        
        ext = active_file.split(".")[-1]
        language_map = {"html": "html", "css": "css", "js": "javascript"}
        ace_lang = language_map.get(ext, "text")
        
        dynamic_key = f"editor_{active_file}_{len(st.session_state.chat_history)}"
        
        edited_code = st_ace(
            value=st.session_state.vfs.get(active_file, ""),
            language=ace_lang,
            theme="tomorrow_night", 
            height=450,
            key=dynamic_key,
            auto_update=True,
            show_gutter=True,
            font_size=14
        )
        
        if edited_code and edited_code != st.session_state.vfs[active_file]:
            st.session_state.vfs[active_file] = edited_code
            st.rerun()
            
    # --- 3. TERMINAL / PREVIEW PANEL (Restored to Live Inline Preview!) ---
    st.write("") 
    tab_preview, tab_terminal = st.tabs(["🌐 PORTS: 8080 (Browser Preview)", "🖥️ TERMINAL"])

    with tab_preview:
        if st.session_state.vfs.get("index.html"):
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
            
            # Rendering live directly in the IDE again
            components.html(combined_code, height=450, scrolling=True)
            
        else:
            st.caption("No index.html found in the workspace.")
            
    with tab_terminal:
        st.code("user@devteam-ide:~/project$ npm run dev\n> Local server running on port 8080...\n> Watching for file changes...", language="bash")