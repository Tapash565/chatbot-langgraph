# Repository Architecture Guide

This document explains the repository structure and architectural conventions used in this project.
The goal is to keep the codebase **modular, maintainable, and scalable**, while making it easy for both developers and AI tools to understand the system.

---

# 1. High-Level Architecture

The project is structured into three main layers:

1. **Frontend** – User interface and interaction layer.
2. **Backend API** – Application logic and orchestration layer.
3. **Infrastructure / Tooling** – Deployment, configuration, and operational scripts.

The request flow is:

User → Frontend → API Routes → Services → Agents / Retrieval → Database → Response

---

# 2. Repository Structure

```
project-root/
│
├── backend/
│   ├── api/
│   │   └── routes/              # FastAPI route handlers
│   │       ├── chat.py
│   │       ├── threads.py
│   │       ├── documents.py
│   │       └── health.py
│   │
│   ├── core/                    # Core application configuration
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── security.py
│   │
│   ├── db/                      # Database connections and repositories
│   │   ├── session.py
│   │   ├── repositories/
│   │   │   ├── thread_repository.py
│   │   │   └── document_repository.py
│   │   └── migrations/
│   │
│   ├── models/                  # Pydantic models and schemas
│   │   ├── thread.py
│   │   ├── chat.py
│   │   └── document.py
│   │
│   ├── services/                # Business logic layer
│   │   ├── chat_service.py
│   │   ├── thread_service.py
│   │   └── document_service.py
│   │
│   ├── agents/                  # LLM orchestration logic
│   │   ├── graph.py
│   │   ├── router.py
│   │   ├── prompts.py
│   │   └── nodes/
│   │
│   ├── memory/                  # Conversation memory and checkpointing
│   │   ├── checkpoint.py
│   │   ├── summarizer.py
│   │   └── thread_state.py
│   │
│   ├── retrieval/               # RAG pipeline
│   │   ├── embedder.py
│   │   ├── vector_store.py
│   │   ├── chunker.py
│   │   └── retriever.py
│   │
│   ├── tools/                   # Tool calling utilities
│   │   ├── calculator.py
│   │   ├── web_search.py
│   │   └── stock_price.py
│   │
│   ├── utils/                   # General helper functions
│   │   └── helpers.py
│   │
│   └── main.py                  # FastAPI application entrypoint
│
├── frontend/
│   ├── app/                     # Next.js app router
│   │   ├── page.tsx
│   │   ├── chat/
│   │   │   └── [threadId]/page.tsx
│   │   └── layout.tsx
│   │
│   ├── components/              # UI components
│   │   ├── chat/
│   │   ├── sidebar/
│   │   └── ui/
│   │
│   ├── lib/                     # API clients, hooks, utilities
│   │   ├── api-client.ts
│   │   ├── hooks/
│   │   └── utils.ts
│   │
│   ├── types/                   # TypeScript interfaces
│   │   ├── chat.ts
│   │   ├── thread.ts
│   │   └── document.ts
│   │
│   └── public/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── scripts/                     # Utility scripts
│   ├── seed_db.py
│   └── maintenance.py
│
├── docs/                        # Project documentation
│   ├── architecture.md
│   └── setup.md
│
├── infra/                       # Infrastructure and deployment
│   ├── docker/
│   ├── nginx/
│   └── ci/
│
├── data/                        # Local development data
│
├── .env.example
├── docker-compose.yml
├── README.md
├── requirements.txt
└── package.json
```

---

# 3. Backend Architecture

The backend follows a layered architecture.

```
API Routes
    ↓
Services
    ↓
Agents / Retrieval / Tools
    ↓
Repositories (Database)
    ↓
Response Models
```

Responsibilities of each layer:

### API Layer

Handles HTTP requests and responses.

Example:

* Validate request
* Call service functions
* Return response schema

### Service Layer

Contains the core application logic.

Example:

* Create threads
* Process chat requests
* Manage documents

### Agent Layer

Handles LLM orchestration.

Example:

* LangGraph workflows
* tool routing
* prompt templates
* agent decision logic

### Retrieval Layer

Responsible for document search and RAG.

Example:

* chunking
* embeddings
* vector similarity search

### Memory Layer

Manages conversation state.

Example:

* thread checkpoints
* summarization
* context reconstruction

### Database Layer

Handles persistence.

Example:

* metadata storage
* thread storage
* document indexing

---

# 4. Frontend Architecture

The frontend is built using **Next.js App Router**.

Key concepts:

### app/

Page routing and layouts.

### components/

Reusable UI components.

### lib/

Client-side logic including:

* API clients
* hooks
* utility functions

### types/

Shared TypeScript interfaces.

---

# 5. Coding Principles

The repository follows these architectural rules:

1. API routes should contain minimal logic.
2. Business logic belongs in the **services layer**.
3. Database access should be isolated to **repositories**.
4. LLM orchestration should live in the **agents layer**.
5. Prompt templates should be centralized.
6. Retrieval logic must remain separate from business logic.
7. Shared utilities should be placed in the **utils** directory.

---

# 6. Development Guidelines

When adding new features:

1. Create or update a **route** in `backend/api/routes`.
2. Implement business logic inside `backend/services`.
3. Add database queries to `backend/db/repositories`.
4. Add agent logic in `backend/agents` if LLM interaction is needed.
5. Update frontend API calls in `frontend/lib`.

---

# 7. Testing Strategy

Tests are divided into:

* **Unit tests** – test individual functions.
* **Integration tests** – test services and database interactions.
* **End-to-end tests** – simulate full user flows.

---

# 8. Environment Configuration

Environment variables should be stored in `.env` files.

Example:

```
OPENAI_API_KEY=
DATABASE_URL=
NEXT_PUBLIC_API_URL=
```

Do not commit `.env` files to version control.

---

# 9. Deployment

Deployment configuration is stored in:

```
infra/
```

This includes:

* Docker configuration
* CI/CD pipelines
* Reverse proxy configuration

---

# 10. Future Improvements

Possible future additions:

* Background task queue
* Observability (metrics + tracing)
* Model routing layer
* Multi-tenant support
* Cost-aware inference routing

---

This structure ensures the system remains **maintainable as the project grows** while keeping the separation of responsibilities clear.
