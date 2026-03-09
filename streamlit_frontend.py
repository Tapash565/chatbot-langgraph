import uuid

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from langgraph_backend import (
    chatbot,
    delete_thread,
    generate_title,
    get_sorted_threads,
    ingest_pdf,
    rename_thread,
    retrieve_all_threads,
    thread_document_metadata,
    update_thread,
)


# =========================== Utilities ===========================
def generate_thread_id():
    return str(uuid.uuid4())


def reset_chat():
    thread_id = generate_thread_id()
    st.session_state["thread_id"] = thread_id
    st.session_state["chat_name"] = "Untitled Chat"
    st.session_state["editing_name"] = False
    add_thread(thread_id)
    st.session_state["message_history"] = []
    update_thread(thread_id)


def add_thread(thread_id):
    if thread_id not in st.session_state["chat_threads"]:
        st.session_state["chat_threads"].append(thread_id)


def load_conversation(thread_id):
    state = chatbot.get_state(config={"configurable": {"thread_id": thread_id}})
    return state.values.get("messages", [])


# ======================= Session Initialization ===================
if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()

if "chat_threads" not in st.session_state:
    st.session_state["chat_threads"] = retrieve_all_threads()

if "ingested_docs" not in st.session_state:
    st.session_state["ingested_docs"] = {}

if "editing_name" not in st.session_state:
    st.session_state["editing_name"] = False

add_thread(st.session_state["thread_id"])

thread_key = str(st.session_state["thread_id"])
thread_docs = st.session_state["ingested_docs"].setdefault(thread_key, {})
selected_thread = None

# Resolve current chat name from DB on first load
if "chat_name" not in st.session_state:
    _all_t = {t["id"]: t["name"] for t in get_sorted_threads()}
    st.session_state["chat_name"] = _all_t.get(thread_key, "Untitled Chat")

# ============================ Sidebar ============================
with st.sidebar:
    st.title("LangGraph Chatbot")

    # Chat name — display or inline rename
    if st.session_state.get("editing_name", False):
        new_name_input = st.text_input(
            "Chat name",
            value=st.session_state.get("chat_name", "Untitled Chat"),
            key="name_input",
        )
        _s_col, _c_col = st.columns(2)
        with _s_col:
            if st.button("💾 Save", use_container_width=True, key="save_name"):
                name_to_save = new_name_input.strip() or "Untitled Chat"
                rename_thread(thread_key, name_to_save)
                st.session_state["chat_name"] = name_to_save
                st.session_state["editing_name"] = False
                st.rerun()
        with _c_col:
            if st.button("✖ Cancel", use_container_width=True, key="cancel_name"):
                st.session_state["editing_name"] = False
                st.rerun()
    else:
        _n_col, _e_col = st.columns([5, 1])
        with _n_col:
            st.markdown(f"**{st.session_state.get('chat_name', 'Untitled Chat')}**")
        with _e_col:
            if st.button("✏️", key="edit_name", help="Rename this chat"):
                st.session_state["editing_name"] = True
                st.rerun()

    # New Chat and Delete buttons
    _col_new, _col_del = st.columns(2)
    with _col_new:
        if st.button("➕ New Chat", use_container_width=True):
            reset_chat()
            st.rerun()
    with _col_del:
        if st.button("🗑️ Delete", use_container_width=True, help="Delete current chat and its indexed document"):
            delete_thread(thread_key)
            st.session_state["ingested_docs"].pop(thread_key, None)
            reset_chat()
            st.rerun()

    st.divider()

    # Past conversations
    st.subheader("Past conversations")
    all_threads = get_sorted_threads()
    if not all_threads:
        st.write("No past conversations yet.")
    else:
        for thread in all_threads:
            tid = thread["id"]
            tname = thread["name"] or "Untitled Chat"
            _t_col, _d_col = st.columns([5, 1])
            with _t_col:
                if st.button(tname, key=f"side-thread-{tid}", use_container_width=True):
                    selected_thread = tid
            with _d_col:
                if st.button("🗑️", key=f"del-thread-{tid}", help=f"Delete '{tname}'"):
                    delete_thread(tid)
                    st.session_state["ingested_docs"].pop(tid, None)
                    if tid in st.session_state["chat_threads"]:
                        st.session_state["chat_threads"].remove(tid)
                    if tid == thread_key:
                        reset_chat()
                    st.rerun()

# ============================ Main Layout ========================
st.title(st.session_state.get("chat_name", "Untitled Chat"))

# Indexed document badge
if thread_docs:
    latest_doc = list(thread_docs.values())[-1]
    st.caption(
        f"📄 `{latest_doc.get('filename')}` — "
        f"{latest_doc.get('chunks')} chunks · {latest_doc.get('documents')} pages"
    )

# Chat messages
for message in st.session_state["message_history"]:
    with st.chat_message(message["role"]):
        st.text(message["content"])

# PDF attachment — ChatGPT-style, in the main area above the input
with st.expander("📎 Attach a PDF"):
    uploaded_pdf = st.file_uploader("Upload a PDF", type=["pdf"], label_visibility="collapsed")
    if uploaded_pdf:
        if uploaded_pdf.name in thread_docs:
            st.info(f"`{uploaded_pdf.name}` is already indexed for this chat.")
        else:
            with st.status("Indexing PDF…", expanded=True) as status_box:
                try:
                    summary = ingest_pdf(
                        uploaded_pdf.getvalue(),
                        thread_id=thread_key,
                        filename=uploaded_pdf.name,
                    )
                    thread_docs[uploaded_pdf.name] = summary
                    status_box.update(label="✅ PDF indexed", state="complete", expanded=False)
                    st.rerun()
                except ValueError as e:
                    status_box.update(label=f"❌ Error: {str(e)}", state="error", expanded=False)
                    st.error(f"Failed to process PDF: {str(e)}")
                except Exception as e:
                    status_box.update(label="❌ Indexing failed", state="error", expanded=False)
                    st.error(f"Unexpected error: {str(e)}")

user_input = st.chat_input("Ask about your document or use tools")

if user_input:
    st.session_state["message_history"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.text(user_input)

    CONFIG = {
        "configurable": {"thread_id": thread_key},
        "metadata": {"thread_id": thread_key},
        "run_name": "chat_turn",
    }

    with st.chat_message("assistant"):
        status_holder = {"box": None}

        def ai_only_stream():
            for message_chunk, _ in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode="messages",
            ):
                if isinstance(message_chunk, ToolMessage):
                    tool_name = getattr(message_chunk, "name", "tool")
                    if status_holder["box"] is None:
                        status_holder["box"] = st.status(
                            f"🔧 Using `{tool_name}` …", expanded=True
                        )
                    else:
                        status_holder["box"].update(
                            label=f"🔧 Using `{tool_name}` …",
                            state="running",
                            expanded=True,
                        )

                if isinstance(message_chunk, AIMessage):
                    yield message_chunk.content

        ai_message = st.write_stream(ai_only_stream())

        if status_holder["box"] is not None:
            status_holder["box"].update(
                label="✅ Tool finished", state="complete", expanded=False
            )

    st.session_state["message_history"].append(
        {"role": "assistant", "content": ai_message}
    )

    # Auto-generate chat title after first exchange if still "Untitled Chat"
    generate_title(thread_key)
    _all_t = {t["id"]: t["name"] for t in get_sorted_threads()}
    _new_title = _all_t.get(thread_key, "Untitled Chat")
    if _new_title != st.session_state.get("chat_name"):
        st.session_state["chat_name"] = _new_title
        st.rerun()

if selected_thread:
    st.session_state["thread_id"] = selected_thread
    _all_t = {t["id"]: t["name"] for t in get_sorted_threads()}
    st.session_state["chat_name"] = _all_t.get(str(selected_thread), "Untitled Chat")
    st.session_state["editing_name"] = False
    messages = load_conversation(selected_thread)

    # Filter out ToolMessage entries so internal tool responses aren't shown
    messages = [m for m in messages if not isinstance(m, ToolMessage)]

    temp_messages = []
    for msg in messages:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        temp_messages.append({"role": role, "content": msg.content})
    st.session_state["message_history"] = temp_messages
    st.session_state["ingested_docs"].setdefault(str(selected_thread), {})
    st.rerun()
