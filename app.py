import streamlit as st

import agent
import document_search
import study_planner
import tools

st.set_page_config(page_title="AI College Assistant", layout="wide")
st.title("AI College Assistant")


@st.cache_resource
def load_documents():
    """Index all PDFs in documents/ once, when the app starts."""
    document_search.DOCS_FOLDER.mkdir(exist_ok=True)
    return [document_search.index_pdf(p) for p in document_search.DOCS_FOLDER.glob("*.pdf")]


load_documents()

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": agent.get_system_prompt()}]
if "shown" not in st.session_state:
    st.session_state.shown = []  # what we display in the chat

# ---------------- Sidebar: upload PDF ----------------
with st.sidebar:
    st.header("Study material")
    uploaded = st.file_uploader("Upload a PDF", type="pdf")
    if uploaded and st.button("Add to assistant"):
        document_search.DOCS_FOLDER.mkdir(exist_ok=True)
        save_path = document_search.DOCS_FOLDER / uploaded.name
        save_path.write_bytes(uploaded.getbuffer())
        with st.spinner("Reading PDF..."):
            result = document_search.index_pdf(save_path)
        if result["success"]:
            st.success(f"Added {result['file']} ({result['chunks']} chunks)")
        else:
            st.error(result["error"])
    st.caption(f"Chunks loaded: {len(document_search.INDEX)}")

tab_chat, tab_plan, tab_tasks = st.tabs(["Chat", "Study plan", "Tasks"])

# ---------------- Chat tab ----------------
with tab_chat:
    for item in st.session_state.shown:
        with st.chat_message(item["role"]):
            st.write(item["text"])
            for t in item.get("tools", []):
                with st.expander(f"Tool used: {t['tool']}"):
                    st.json({"arguments": t["args"], "result": t["result"]})

    prompt = st.chat_input("Ask a question, add a task, or request a study plan")
    if prompt:
        st.session_state.shown.append({"role": "user", "text": prompt})
        st.session_state.messages.append({"role": "user", "content": prompt})
        agent.TOOL_LOG.clear()
        with st.spinner("Thinking..."):
            reply = agent.chat(st.session_state.messages)
        st.session_state.shown.append(
            {"role": "assistant", "text": reply, "tools": list(agent.TOOL_LOG)}
        )
        st.rerun()

# ---------------- Study plan tab ----------------
with tab_plan:
    with st.form("plan_form"):
        subject = st.text_input("Subject")
        exam_date = st.date_input("Exam date")
        topics = st.text_area("Topics (separate with commas)")
        hours = st.number_input("Study hours per day", 0.5, 12.0, 2.0, 0.5)
        go = st.form_submit_button("Generate plan")
    if go:
        result = study_planner.generate_study_plan(subject, exam_date.isoformat(), topics, hours)
        if result["success"]:
            for day in result["plan"]:
                parts = ", ".join(f"{s['topic']} ({s['hours']} h)" for s in day["sessions"])
                st.write(f"**{day['date']} ({day['day']})**: {parts}")
        else:
            st.error(result["error"])

# ---------------- Tasks tab ----------------
with tab_tasks:
    with st.form("task_form", clear_on_submit=True):
        title = st.text_input("Task title")
        deadline = st.date_input("Deadline", key="task_deadline")
        add = st.form_submit_button("Add task")
    if add:
        result = tools.add_task(title, deadline.isoformat())
        if result["success"]:
            st.success(f"Task #{result['task_id']} saved")
        else:
            st.error(result["error"])

    all_tasks = tools.list_tasks("all")["tasks"]
    if all_tasks:
        st.dataframe(all_tasks, use_container_width=True)
    else:
        st.info("No tasks yet.")