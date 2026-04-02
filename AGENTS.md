# AGENTS.md

## Cursor Cloud specific instructions

### Project Overview

**TeardownOS** is a browser-based Linux desktop environment for security researchers, built for the HMGCC Smart Personal Assistant challenge. It enables drag-and-drop document ingestion, RAG-powered querying with Ollama, and multimodal understanding of PDFs, images, and code.

### Architecture

| Service | Port | Tech |
|---------|------|------|
| Frontend (Vite dev server) | 5173 | React + TypeScript |
| Backend (FastAPI) | 8000 | Python, uvicorn |
| Ollama (LLM runtime) | 11434 | Local models |

The frontend proxies `/api` to the backend at port 8000 via Vite config.

### Required Ollama Models

- `llama3.2:3b` — text LLM for RAG responses
- `llava:7b` — vision model for image analysis
- `nomic-embed-text` — embedding model for vector search

Pull with: `ollama pull <model-name>`

### Running Services

1. **Ollama** must be started first: `ollama serve &`
2. **Backend**: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
3. **Frontend**: `cd frontend && npm run dev`

### API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Health check (also verifies Ollama connectivity) |
| POST | `/api/documents/upload` | Upload + auto-ingest document |
| GET | `/api/documents` | List all documents |
| DELETE | `/api/documents/{id}` | Delete document + vectors |
| GET | `/api/architecture/summary` | Generate structured architecture summary |
| POST | `/api/chat` | Streaming RAG chat (SSE) |
| POST/GET | `/api/conversations` | Create/list conversations |
| PATCH/DELETE | `/api/conversations/{id}` | Rename/delete conversation |
| GET | `/api/conversations/{id}/messages` | List messages |

### Key Gotchas

- Ollama serve must be running before the backend starts processing documents or chat queries; the backend does not retry failed Ollama connections.
- Document ingestion (especially images via LLaVA) runs synchronously in a thread pool — large images can take 30+ seconds on CPU.
- Chat responses stream via SSE (`text/event-stream`); the frontend uses `fetch` + `ReadableStream` to consume them.
- LLM inference on CPU is slow (30-90s per query for llama3.2:3b). Architecture summaries take 1-2 minutes.
- ChromaDB and SQLite data persist in `backend/data/db/`. Delete this directory to reset all indexed documents and conversation history.
- The frontend build uses `tsc -b` which enforces strict unused-variable checks; fix all TS errors before committing.
- The health endpoint at `/api/health` now checks both the FastAPI server and Ollama reachability.

### Lint / Test / Build

- **Frontend lint**: `cd frontend && npx eslint .`
- **Frontend type-check**: `cd frontend && npx tsc --noEmit`
- **Frontend build**: `cd frontend && npm run build`
- **Backend**: No formal test suite yet. Verify via `curl http://localhost:8000/api/health`.
