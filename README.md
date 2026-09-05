# SmartSupport Agent

An AI-powered customer support agent for e-commerce, built on **FastAPI** and **LangGraph**. It routes each customer message to the right specialized workflow — general chat, knowledge-graph queries, policy retrieval (RAG), image analysis, or clarification — and streams the answer back to the client over Server-Sent Events (SSE).

The domain is a consumer-electronics / smart-home store, and the business data follows the classic **Northwind** schema (Customers, Orders, Products, Suppliers, Reviews, etc.), loaded into a **Neo4j** knowledge graph.

---

## Features

- **Intent routing** — an LLM classifies each query into one of several types and dispatches it to a dedicated LangGraph node.
- **Knowledge-graph Q&A** — a multi-tool agentic-RAG workflow answers product / order / inventory questions against Neo4j using Text2Cypher, predefined Cypher templates, and Microsoft GraphRAG.
- **Policy RAG** — hybrid retrieval (vector + BM25) with cross-encoder reranking over company policy documents (returns, refunds, shipping, warranty, etc.), stored in a local Qdrant vector store.
- **Image queries** — customers can upload a product photo; a vision model describes it and the agent responds accordingly.
- **Guardrails** — keeps the assistant within the store's business scope and rejects unrelated questions.
- **Hallucination checking** — an optional grader scores whether generated answers are grounded in retrieved facts.
- **Human-in-the-loop** — LangGraph interrupts pause the flow to collect additional information, resumable via a dedicated endpoint.
- **Conversation persistence** — chat history stored in MySQL; optional Redis semantic cache.
- **Pluggable LLM providers** — OpenAI, DeepSeek, or local Ollama, selected via configuration.
- **Bundled frontend** — a pre-built SPA is served as static files from the same server.

---

## Architecture

```
Client (SPA / SSE)
      │
      ▼
FastAPI (main.py)  ──►  LangGraph agent (app/lg_agent/lg_builder.py)
      │                        │
      │              analyze_and_route_query  ── routes to ──┐
      │                        │                             │
      │        ┌───────────────┼───────────────┬─────────────┼──────────────┐
      │        ▼               ▼               ▼             ▼              ▼
      │  general query   additional info   research plan   policy query   image query
      │                                    (KG multi-tool)  (Qdrant RAG)   (vision model)
      │                                          │
      │                                          ▼
      │                                    Neo4j + Microsoft GraphRAG
      │
      └──►  Services layer (app/services): LLM factory, conversation, embedding,
            indexing, search, redis cache
```

### Routing categories

| Route | Node | Backend |
|-------|------|---------|
| `general-query` | `respond_to_general_query` | LLM only |
| `additional-query` | `get_additional_info` | LLM + guardrails |
| `graphrag-query` | `create_research_plan` | Neo4j multi-tool workflow / GraphRAG |
| `policy_query` | `create_policy_query` | Qdrant + BM25 hybrid RAG |
| `image-query` | `create_image_query` | Vision model |
| `file-query` | `create_file_query` | *(placeholder / TODO)* |

---

## Project structure

```
SmartSupport_agent/
├── Business_data/              # Northwind-style CSVs (Customers, Orders, Products, Reviews, ...)
├── requirements.txt
└── llm_backend/
    ├── main.py                 # FastAPI app + all HTTP/SSE endpoints
    ├── run.py                  # Uvicorn entry point (port 8000)
    ├── .env                    # Configuration (see below)
    ├── app/
    │   ├── core/               # config, database, logger, middleware
    │   ├── models/             # SQLAlchemy models (User, Conversation, Message)
    │   ├── services/           # LLM providers, RAG, indexing, cache, search
    │   ├── lg_agent/           # LangGraph agent
    │   │   ├── lg_builder.py   # graph definition & nodes
    │   │   ├── lg_states.py    # state / router schemas
    │   │   ├── lg_prompts.py   # system prompts
    │   │   └── kg_sub_graph/   # knowledge-graph agentic-RAG sub-workflows
    │   ├── graphrag/           # Microsoft GraphRAG project (settings, prompts)
    │   ├── prompts/ tools/     # search prompts & tool definitions
    │   ├── data/               # docs, vector store, uploads
    │   └── static/dist/        # pre-built frontend SPA
    └── scripts/                # DB init, policy index build, tests
```

---

## Requirements

- **Python 3.10+**
- **MySQL** — conversation & message storage
- **Neo4j** — business knowledge graph
- **Redis** *(optional)* — semantic cache
- **Ollama** *(optional)* — for local models / embeddings
- API keys for your chosen LLM provider (OpenAI / DeepSeek) and a vision model

---

## Setup

### 1. Install dependencies

```bash
cd SmartSupport_agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

Create `llm_backend/.env`. The settings are defined in `app/core/config.py`; the key values are:

```dotenv
# LLM providers
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
DEEPSEEK_API_KEY=...
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# Vision model (for image queries)
VISION_API_KEY=...
VISION_BASE_URL=...
VISION_MODEL=...

# Ollama (optional local models)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=...
OLLAMA_REASON_MODEL=...
OLLAMA_EMBEDDING_MODEL=bge-m3
OLLAMA_AGENT_MODEL=...

# Search
SERPAPI_KEY=...

# MySQL
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=...
DB_NAME=smart_support

# Neo4j
NEO4J_URL=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=...
NEO4J_DATABASE=neo4j

# Redis (optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
```

Provider selection (`CHAT_SERVICE`, `REASON_SERVICE`, `AGENT_SERVICE`) defaults to OpenAI and can be overridden in the environment.

### 3. Initialize the database

```bash
cd llm_backend
python scripts/init_db.py
```

### 4. Load the knowledge graph

Import the `Business_data/` CSVs into Neo4j (see `llm_backend/app/data/neo4j_admin/import_command.bat` for the `neo4j-admin` import command).

### 5. Build the policy index

Place policy documents (PDF/DOCX) under the configured `POLICY_DATA_PATH`, then:

```bash
python scripts/build_policy_index.py
python scripts/check_policy_index.py   # verify
```

---

## Running

```bash
cd llm_backend
python run.py
```

The server starts on `http://0.0.0.0:8000`. The bundled frontend is served at `/`, and API docs are available at `/docs`.

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Health check |
| `POST` | `/api/langgraph/query` | **Main agent endpoint** (multipart form: `query`, `user_id`, optional `conversation_id`, optional `image`). SSE stream. |
| `POST` | `/api/langgraph/resume` | Resume an interrupted (human-in-the-loop) conversation |
| `POST` | `/api/chat` | Plain streaming chat with history |
| `POST` | `/api/reason` | Reasoning-model response (e.g. DeepSeek-R1) |
| `POST` | `/api/search` | Search-enhanced chat |
| `POST` | `/api/upload` | Upload a file and build a RAG index |
| `POST` | `/api/conversations` | Create a conversation |
| `GET`  | `/api/conversations/user/{user_id}` | List a user's conversations |
| `GET`  | `/api/conversations/{id}/messages` | Get conversation messages |
| `PUT`  | `/api/conversations/{id}/name` | Rename a conversation |
| `DELETE` | `/api/conversations/{id}` | Delete a conversation |

### Example: query the agent

```bash
curl -N -X POST http://localhost:8000/api/langgraph/query \
  -F "query=What is the status of order 10248?" \
  -F "user_id=1"
```

Responses stream as SSE `data:` events, ending with `{"done": true, "conversation_id": "..."}`. If the graph interrupts, an event with `{"interruption": true, ...}` is sent; continue via `/api/langgraph/resume`.

---

## Tech stack

- **API**: FastAPI, Uvicorn, SSE streaming
- **Agent**: LangGraph, LangChain (OpenAI / Ollama / DeepSeek, Neo4j)
- **Knowledge graph**: Neo4j + Microsoft GraphRAG, Text2Cypher
- **RAG**: Qdrant (vector), BM25, cross-encoder reranking, sentence-transformers / FAISS
- **Storage**: MySQL (SQLAlchemy async + aiomysql), Redis semantic cache
- **Logging**: Loguru

---

## Notes

- CORS is configured for a frontend on `localhost:3000`; adjust `allow_origins` in `main.py` as needed.
- Authentication is currently stubbed (`/api/users/me` returns a demo user); the LangGraph endpoints require no login in this version.
- `create_file_query` is a placeholder for future document-query support.
