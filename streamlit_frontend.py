import streamlit as st
from langgraph_backend import chatbot, update_thread, get_sorted_threads, generate_title, delete_chats
from langchain_core.messages import HumanMessage
import uuid
import threading

def generate_thread_id():
    return str(uuid.uuid4())

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state.thread_id = thread_id
    update_thread(thread_id) # Register new thread
    st.session_state.messages_history = []

def load_conversation(thread_id):
    return chatbot.get_state(config={'configurable': {'thread_id': thread_id}}).values['messages']

if 'messages_history' not in st.session_state:
    st.session_state.messages_history = []

if 'thread_id' not in st.session_state:
    st.session_state.thread_id = generate_thread_id()
    update_thread(st.session_state.thread_id)

st.sidebar.title('AI Chatbot Interface')

if st.sidebar.button("New Chat"):
    reset_chat()

if st.sidebar.button("Delete All Chats"):
    delete_chats()
    reset_chat()

st.sidebar.header("My Conversations")

# Refresh threads list
chat_threads = get_sorted_threads()

for thread in chat_threads:
    thread_id = thread['id']
    name = thread['name']
    if st.sidebar.button(name, key=thread_id):
        st.session_state.thread_id = thread_id

        try:
            messages = load_conversation(thread_id)

            temp_messages = []

            for msg in messages:
                if isinstance(msg, HumanMessage):
                    role = 'user'
                else:
                    role = 'assistant'
                temp_messages.append({'role': role, 'content': msg.content})
        except:
            temp_messages = []
        st.session_state.messages_history = temp_messages

for message in st.session_state.messages_history:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

user_input = st.chat_input('Ask a question or start a conversation')

if user_input:
    st.session_state.messages_history.append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.markdown(user_input)
    CONFIG = {'configurable': {'thread_id': st.session_state.thread_id}}
    with st.chat_message('assistant'):
        ai_message = st.write_stream(messages_chunk.content for messages_chunk, metadata in chatbot.stream(
            {'messages': [HumanMessage(content=user_input)]},
            config = CONFIG,
            stream_mode = 'messages'
        ))
    st.session_state.messages_history.append({'role': 'assistant', 'content': ai_message})

    # Update timestamp
    update_thread(st.session_state.thread_id)
    
    # Generate title in background
    def run_title_gen(tid):
        generate_title(tid)
        
    thread = threading.Thread(target=run_title_gen, args=(st.session_state.thread_id,))
    thread.start()
    st.rerun()
