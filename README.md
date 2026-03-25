# LangGraph Chatbot

A stateful conversational AI application built with [LangGraph](https://langchain-ai.github.io/langgraph/), [FastAPI](https://fastapi.tiangolo.com/), and [Next.js](https://nextjs.org/). This version uses one frontend and one backend contract for chat, threads, and document upload.

## Features
*   **Persistent Conversations**: Chats are stored in a local SQLite database (`chatbot.db`).
*   **Auto-Naming**: Conversations are automatically titled by an LLM based on context.
*   **Activity Sorting**: The conversation list is sorted by the most recent activity.
*   **State Management**: Uses `LangGraph` checkpoints to maintain conversation state.
*   **Single Frontend**: Next.js is the supported UI.
*   **Frontend/Backend Compatibility**: The web client and API share aligned routes for SSE chat streaming, thread history, and PDF upload.

## File Structure
```text
chatbot-langgraph/
├── backend/                # FastAPI app, LangGraph agent, and services
├── frontend/               # Next.js frontend
├── chatbot.db              # SQLite database for storing thread state and metadata
├── faiss_indices/          # Vector indices for document retrieval
├── pyproject.toml          # Python project metadata
├── requirements.txt        # Python dependencies
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
    Create a `.env` file in the root directory and add your API keys:
    ```env
    GROQ_API_KEY=your_api_key_here
    NEXT_PUBLIC_API_URL=http://localhost:8000/api
    ```

## Usage

1. Start the backend:
```bash
uvicorn backend.main:app --reload
```

2. Start the frontend:
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.
