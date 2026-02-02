# LangGraph Chatbot

A stateful conversational AI application built with [LangGraph](https://langchain-ai.github.io/langgraph/), [LangChain](https://python.langchain.com/), and [Streamlit](https://streamlit.io/). This chatbot features persistent memory, automatic conversation naming, and activity-based sorting.

## Features
*   **Persistent Conversations**: Chats are stored in a local SQLite database (`chatbot.db`).
*   **Auto-Naming**: Conversations are automatically titled by an LLM based on context.
*   **Activity Sorting**: The conversation list is sorted by the most recent activity.
*   **State Management**: Uses `LangGraph` checkpoints to maintain conversation state.
*   **Chat Management**: Ability to create new chats and delete all chat history.

## File Structure
```
chatbot-langgraph/
├── chatbot.db              # SQLite database for storing thread state and metadata
├── langgraph_backend.py    # Backend logic: LangGraph definition, DB operations, Title generation
├── requirements.txt        # Python dependencies
├── streamlit_frontend.py   # Streamlit UI application
└── .gitignore              # Git ignore rules
```

## Setup & Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/Tapash565/chatbot-langgraph.git
    cd chatbot-langgraph
    ```

2.  **Create a virtual environment**:
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Linux/Mac
    source venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuration**:
    Create a `.env` file in the root directory and add your API keys (e.g., for Groq or OpenAI):
    ```env
    GROQ_API_KEY=your_api_key_here
    ```

## Usage

Run the Streamlit application:
```bash
streamlit run streamlit_frontend.py
```

Opens in your browser at `http://localhost:8501`.
