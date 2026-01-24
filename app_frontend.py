import streamlit as st
import requests
import time
import json

# --- Configuration ---
API_BASE_URL = "http://127.0.0.1:8000/api"

# --- Page Configuration ---
st.set_page_config(
    page_title="RAG Knowledge Base",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Modern Dark Theme ---
st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    .stApp {
        font-family: 'Inter', sans-serif;
    }
    
    /* Main background with subtle gradient */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Card styling */
    .card {
        background: linear-gradient(135deg, rgba(30, 30, 46, 0.9) 0%, rgba(45, 45, 68, 0.9) 100%);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(10px);
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    .sub-header {
        color: rgba(255, 255, 255, 0.7);
        font-size: 1rem;
        margin-bottom: 2rem;
    }
    
    /* Status badge */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 0.875rem;
        font-weight: 500;
    }
    
    .status-online {
        background: rgba(16, 185, 129, 0.2);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    .status-offline {
        background: rgba(239, 68, 68, 0.2);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%);
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
        border: 1px solid rgba(102, 126, 234, 0.3);
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .metric-label {
        color: rgba(255, 255, 255, 0.7);
        font-size: 0.875rem;
        margin-top: 0.25rem;
    }
    
    /* Chat message styling */
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem 1.25rem;
        border-radius: 18px 18px 4px 18px;
        margin: 0.5rem 0;
        max-width: 80%;
        margin-left: auto;
    }
    
    .assistant-message {
        background: rgba(55, 55, 75, 0.8);
        padding: 1rem 1.25rem;
        border-radius: 18px 18px 18px 4px;
        margin: 0.5rem 0;
        max-width: 80%;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    /* Input styling */
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        background: rgba(30, 30, 46, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        color: white;
        padding: 0.75rem 1rem;
    }
    
    .stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
    }
    
    /* File uploader */
    .stFileUploader > div {
        background: rgba(30, 30, 46, 0.6);
        border: 2px dashed rgba(102, 126, 234, 0.5);
        border-radius: 12px;
        padding: 2rem;
        transition: all 0.3s ease;
    }
    
    .stFileUploader > div:hover {
        border-color: #667eea;
        background: rgba(102, 126, 234, 0.1);
    }
    
    /* Selectbox styling */
    .stSelectbox > div > div {
        background: rgba(30, 30, 46, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: rgba(55, 55, 75, 0.5);
        border-radius: 10px;
    }
    
    /* Sidebar styling */
    .css-1d391kg, [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(20, 20, 35, 0.95) 0%, rgba(30, 30, 50, 0.95) 100%);
    }
    
    /* Progress indicator */
    .loading-pulse {
        animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    /* Hide default streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Divider */
    .gradient-divider {
        height: 2px;
        background: linear-gradient(90deg, transparent, #667eea, #764ba2, transparent);
        margin: 1.5rem 0;
        border: none;
    }
</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "active_tasks" not in st.session_state:
    st.session_state.active_tasks = {}

# --- Helper Functions ---



def get_vector_store_count():
    """Get the number of documents in the vector store."""
    try:
        response = requests.get(f"{API_BASE_URL}/stats", timeout=3)
        if response.status_code == 200:
            return response.json().get("vector_store_count", 0)
    except:
        pass
    return 0

def format_docs_display(docs):
    """Helper to display retrieved documents cleanly."""
    if not docs:
        st.info("📭 No sources returned.")
        return
        
    for i, doc in enumerate(docs):
        score = doc.get('score', doc.get('similarity_score', 'N/A'))
        if isinstance(score, float):
            score = f"{score:.2%}"
        with st.expander(f"📄 Source {i+1} • Relevance: {score}"):
            st.markdown(f"**Content:**\n\n{doc.get('content', 'No content')}")
            if doc.get('metadata'):
                st.caption("Metadata:")
                st.json(doc.get('metadata', {}))

def stream_task_updates(task_id, container):
    """
    Connects to the SSE endpoint and updates the UI container in real-time.
    """
    url = f"{API_BASE_URL}/tasks/{task_id}/stream"
    
    try:
        container.info(f"🔌 Connecting to task stream...")
        
        with requests.get(url, stream=True, timeout=120) as response:
            if response.status_code != 200:
                container.error(f"Failed to connect: {response.status_code}")
                return None

            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    
                    if decoded_line.startswith("data: "):
                        json_str = decoded_line.replace("data: ", "", 1)
                        try:
                            data = json.loads(json_str)
                            status = data.get("status")
                            progress = data.get("progress", {})
                            current_step = progress.get("current_step", "Processing...")
                            percentage = progress.get("percentage", 0)
                            
                            if status == "pending":
                                container.info(f"⏳ **Pending:** {current_step}")
                            elif status == "processing":
                                container.warning(f"⚙️ **Processing ({percentage:.0f}%):** {current_step}")
                            elif status == "completed":
                                container.success("✅ **Task Completed Successfully!**")
                                result = data.get("result")
                                if result:
                                    with container.expander("📋 View Result"):
                                        st.json(result)
                                return "completed"
                            elif status == "failed":
                                container.error(f"❌ **Failed:** {data.get('error', 'Unknown error')}")
                                return "failed"
                                
                        except json.JSONDecodeError:
                            continue
                            
    except Exception as e:
        container.error(f"⚠️ Stream error: {e}")
        return "error"

# --- Sidebar ---
with st.sidebar:
    st.markdown('<p class="main-header" style="font-size: 1.5rem;">🧠 RAG Manager</p>', unsafe_allow_html=True)
    
    # Connection status
    
    doc_count = get_vector_store_count()
    st.markdown(f"""
        <div class="metric-card" style="margin-top: 1rem;">
        <div class="metric-value">{doc_count:,}</div>
        <div class="metric-label">📚 Indexed Documents</div>
    </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<hr class="gradient-divider">', unsafe_allow_html=True)
    
    # Navigation
    page = st.radio(
        "Navigation",
        ["💬 Chat & Search", "📥 Data Ingestion", "📊 System Status"],
        label_visibility="collapsed"
    )

# ==========================================
# PAGE 1: CHAT & SEARCH
# ==========================================
if page == "💬 Chat & Search":
    st.markdown('<p class="main-header">💬 AI-Powered Search</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Ask questions about your indexed documents</p>', unsafe_allow_html=True)
    
    # Search mode selection
    col1, col2 = st.columns([3, 1])
    with col1:
        search_mode = st.selectbox(
            "Search Mode",
            ["🎯 Advanced RAG (Hybrid)", "🔍 Standard RAG", "🤖 LLM Direct"],
            label_visibility="collapsed"
        )
    with col2:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
    
    st.markdown('<hr class="gradient-divider">', unsafe_allow_html=True)
    
    # Chat display
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🤖"):
                st.markdown(msg["content"])
                if "sources" in msg and msg["sources"]:
                    with st.expander("📚 View Sources", expanded=False):
                        format_docs_display(msg["sources"])
    
    # Chat input
    if query := st.chat_input("Ask a question about your documents..."):
        st.session_state.chat_history.append({"role": "user", "content": query})
        
        with st.chat_message("user", avatar="🧑"):
            st.markdown(query)
        
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("🔄 Thinking..."):
                try:
                    params = {"query": query}
                    answer = ""
                    sources = []
                    
                    if "Advanced" in search_mode:
                        res = requests.get(f"{API_BASE_URL}/advanced_query", params=params, timeout=60)
                        data = res.json()
                        answer = data.get("response", {}).get("answer", "No answer generated.")
                        sources = data.get("response", {}).get("sources", [])
                    elif "Standard" in search_mode:
                        res = requests.get(f"{API_BASE_URL}/rag_search", params=params, timeout=30)
                        sources = res.json()
                        answer = "📄 **Here are the most relevant documents:**" if sources else "No relevant documents found."
                    else:  # LLM Direct
                        res = requests.get(f"{API_BASE_URL}/llm_search", params=params, timeout=60)
                        answer = res.json() if isinstance(res.json(), str) else str(res.json())
                    
                    st.markdown(answer)
                    
                    if sources:
                        with st.expander("📚 View Sources", expanded=False):
                            format_docs_display(sources)
                    
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources
                    })
                    
                except requests.exceptions.Timeout:
                    st.error("⏱️ Request timed out. The server might be loading models. Please try again.")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

# ==========================================
# PAGE 2: DATA INGESTION
# ==========================================
elif page == "📥 Data Ingestion":
    st.markdown('<p class="main-header">📥 Ingest Data</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Add documents to your knowledge base</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        st.markdown("### 📤 Upload Source")
        
        ingest_type = st.selectbox(
            "Source Type",
            ["📄 PDF Documents", "📊 CSV File", "🌐 Single Webpage", "🕸️ Recursive Crawl"],
            label_visibility="collapsed"
        )
        
        task_response = None
        new_task_id = None
        
        if "PDF" in ingest_type:
            files = st.file_uploader(
                "Drop PDF files here",
                type=['pdf'],
                accept_multiple_files=True,
                help="Upload one or more PDF files to index"
            )
            if st.button("🚀 Upload & Process", disabled=not files, use_container_width=True):
                with st.spinner("📤 Uploading..."):
                    files_list = [("files", (f.name, f, "application/pdf")) for f in files]
                    task_response = requests.post(f"{API_BASE_URL}/upload/pdfs/async", files=files_list)
        
        elif "CSV" in ingest_type:
            f = st.file_uploader("Drop CSV file here", type=['csv'])
            delim = st.text_input("Delimiter", ",", help="Character used to separate values")
            if st.button("🚀 Upload", disabled=not f, use_container_width=True):
                with st.spinner("📤 Ingesting..."):
                    res = requests.post(
                        f"{API_BASE_URL}/upload/csv",
                        files={"file": (f.name, f, "text/csv")},
                        data={"delimiter": delim}
                    )
                    if res.status_code == 200:
                        st.success("✅ CSV Ingested Successfully!")
                        st.json(res.json())
                    else:
                        st.error(f"❌ Error: {res.text}")
        
        elif "Single" in ingest_type:
            url = st.text_input("Enter URL", placeholder="https://example.com/page")
            if st.button("🚀 Ingest", disabled=not url, use_container_width=True):
                task_response = requests.post(f"{API_BASE_URL}/ingest/webpage/async", json={"url": url})
        
        elif "Recursive" in ingest_type:
            base_url = st.text_input("Base URL", placeholder="https://docs.example.com")
            depth = st.slider("Crawl Depth", 1, 5, 2, help="How many levels deep to crawl")
            if st.button("🚀 Start Crawl", disabled=not base_url, use_container_width=True):
                task_response = requests.post(
                    f"{API_BASE_URL}/ingest/recursive/async",
                    json={"base_url": base_url, "max_depth": depth}
                )
        
        # Handle task creation
        if task_response:
            if task_response.status_code == 200:
                data = task_response.json()
                new_task_id = data.get("task_id")
                if new_task_id:
                    st.session_state.active_tasks[new_task_id] = {
                        "type": ingest_type,
                        "start_time": time.time(),
                        "status": "pending"
                    }
            else:
                st.error(f"❌ Failed: {task_response.text}")
    
    with col2:
        st.markdown("### 📡 Live Progress")
        
        if new_task_id:
            st.info(f"🆔 Task: `{new_task_id[:12]}...`")
            status_container = st.empty()
            final_status = stream_task_updates(new_task_id, status_container)
            
            if final_status in ["completed", "failed"]:
                if new_task_id in st.session_state.active_tasks:
                    st.session_state.active_tasks[new_task_id]["status"] = final_status
        
        st.markdown('<hr class="gradient-divider">', unsafe_allow_html=True)
        st.markdown("### 📋 Task History")
        
        if not st.session_state.active_tasks:
            st.caption("No tasks yet. Upload something to get started!")
        else:
            for tid, info in list(st.session_state.active_tasks.items()):
                status_emoji = {
                    "pending": "⏳",
                    "processing": "⚙️",
                    "completed": "✅",
                    "failed": "❌"
                }.get(info.get("status"), "❓")
                
                with st.expander(f"{status_emoji} {info['type']} ({tid[:8]}...)"):
                    st.write(f"**Status:** {info.get('status', 'Unknown').title()}")
                    if st.button("🗑️ Remove", key=f"del_{tid}"):
                        del st.session_state.active_tasks[tid]
                        st.rerun()

# ==========================================
# PAGE 3: SYSTEM STATUS
# ==========================================
elif page == "📊 System Status":
    st.markdown('<p class="main-header">📊 System Overview</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Monitor your RAG pipeline status</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    try:
        res = requests.get(f"{API_BASE_URL}/stats", timeout=5)
        if res.status_code == 200:
            stats = res.json()
            doc_count = stats.get("vector_store_count", 0)
            
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{doc_count:,}</div>
                    <div class="metric-label">📄 Indexed Chunks</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">✅</div>
                    <div class="metric-label">🔌 API Status</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">💾</div>
                    <div class="metric-label">Data Persisted</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('<hr class="gradient-divider">', unsafe_allow_html=True)
            
            # Additional info
            st.markdown("### 📈 Details")
            with st.expander("Document Loader Stats"):
                st.json(stats.get("document_loader_stats", {}))
                
    except Exception as e:
        st.error(f"⚠️ Could not fetch stats: {e}")
    
    st.markdown('<hr class="gradient-divider">', unsafe_allow_html=True)
    
    # Component status
    st.markdown("### 🔧 Component Status")
    try:
        comp_res = requests.get(f"{API_BASE_URL}/components/status", timeout=5)
        if comp_res.status_code == 200:
            components = comp_res.json()
            for name, status in components.items():
                is_init = status.get("initialized", False)
                error = status.get("error")
                if is_init:
                    st.success(f"✅ **{name.replace('_', ' ').title()}**: Initialized")
                elif error:
                    st.error(f"❌ **{name.replace('_', ' ').title()}**: {error}")
                else:
                    st.warning(f"⏳ **{name.replace('_', ' ').title()}**: Not yet initialized (loads on first use)")
    except:
        st.warning("Could not fetch component status")
    
    st.markdown('<hr class="gradient-divider">', unsafe_allow_html=True)
    
    # Danger zone
    st.markdown("### ⚠️ Danger Zone")
    with st.expander("🗑️ Clear All Data", expanded=False):
        st.warning("This will permanently delete all indexed documents from the vector store.")
        if st.button("🗑️ Clear Database", type="primary", use_container_width=True):
            try:
                res = requests.delete(f"{API_BASE_URL}/clear")
                if res.status_code == 200:
                    st.success("✅ Database cleared!")
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()