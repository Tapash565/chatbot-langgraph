from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from dotenv import load_dotenv
import sqlite3

load_dotenv()

llm = ChatGroq(model='openai/gpt-oss-20b', temperature=0.7)

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):
    messages = state['messages']
    response = llm.invoke(messages)
    return {'messages': [response]}

conn = sqlite3.connect(database='chatbot.db', check_same_thread=False)
# Checkpointer
checkpointer = SqliteSaver(conn=conn)

graph = StateGraph(ChatState)

graph.add_node('chat_node', chat_node)
graph.add_edge(START, 'chat_node')
graph.add_edge('chat_node', END)

chatbot = graph.compile(checkpointer=checkpointer)

def init_db():
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS thread_metadata (
                thread_id TEXT PRIMARY KEY,
                name TEXT,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
    except Exception as e:
        print(f"DB Init Error: {e}")

init_db()

def update_thread(thread_id, name=None):
    cursor = conn.cursor()
    if name:
        cursor.execute('''
            INSERT INTO thread_metadata (thread_id, name, last_active) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(thread_id) DO UPDATE SET name=excluded.name, last_active=CURRENT_TIMESTAMP
        ''', (thread_id, name))
    else:
        cursor.execute('''
            INSERT INTO thread_metadata (thread_id, name, last_active) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(thread_id) DO UPDATE SET last_active=CURRENT_TIMESTAMP
        ''', (thread_id, f"Conversation {thread_id[:4]}")) # Default name if new
    conn.commit()

def get_sorted_threads():
    cursor = conn.cursor()
    # Backfill if needed (simple check)
    all_checkpoints = set()
    for c in checkpointer.list(None):
        all_checkpoints.add(c.config['configurable']['thread_id'])
    
    for tid in all_checkpoints:
        cursor.execute("SELECT 1 FROM thread_metadata WHERE thread_id = ?", (tid,))
        if not cursor.fetchone():
            update_thread(tid)
            
    cursor.execute("SELECT thread_id, name FROM thread_metadata ORDER BY last_active DESC")
    return [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]

def generate_title(thread_id):
    messages = chatbot.get_state(config={'configurable': {'thread_id': thread_id}}).values.get('messages', [])
    if not messages:
        return
    
    # Simple check to see if title is already set to something custom (heuristic: distinctive name check could be complex, 
    # so we just rely on the caller to only call this when appropriate, or check if it's the default name)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM thread_metadata WHERE thread_id = ?", (thread_id,))
    row = cursor.fetchone()
    if row and row[0] and not row[0].startswith("Conversation "):
        return # Already named
        
    conversation_text = "\n".join([f"{msg.type}: {msg.content}" for msg in messages[-4:]]) # Last few messages
    prompt = f"Generate a short, 3-5 word title for this conversation summary. Do not use quotes:\n\n{conversation_text}"
    
    try:
        response = llm.invoke(prompt)
        title = response.content.strip().replace('"', '')
        update_thread(thread_id, name=title)
    except Exception as e:
        print(f"Title Gen Error: {e}")

def delete_chats():
    cursor = conn.cursor()
    cursor.execute("DELETE FROM thread_metadata")
    cursor.execute("DELETE FROM checkpoints")
    cursor.execute("DELETE FROM writes")
    conn.commit()