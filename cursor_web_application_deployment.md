# Web application deployment
_Exported on 02/04/2026 at 20:07:52 BST from Cursor (2.6.22)_

---

**User**

deploy this web application

---

**Cursor**

This app has some specific requirements (Ollama for LLM inference, persistent storage for ChromaDB/SQLite/uploads) that narrow down deployment options. Before I create a plan, I need to understand your target environment.

**Deployment Target**

> **Where do you want to deploy this application?**
> - Docker Compose (local or any Docker-capable machine)
> - Cloud VM (AWS EC2, GCP, Azure, DigitalOcean, etc.)
> - Fly.io
> - Railway
> - Other / not sure — suggest the best option

> **Ollama (the LLM runtime) needs GPU or decent CPU. How do you want to handle it?**
> - Bundle Ollama in the deployment (run alongside the app)
> - I have a separate Ollama server already running (just point to it)
> - Not sure — recommend something

---

**User**

run this application locally

---

**Cursor**

Let me create a plan to get the application running locally.

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**


Implementing the local run plan: checking prerequisites, then starting services.




Ollama is running. Config defaults: `llama3.2:3b`, `moondream` for vision, `nomic-embed-text`. Pulling the plan's models (`llama3.2:3b`, `llava:7b`, `nomic-embed-text`) and installing dependencies.




Checking whether we can bind to port 8000 (Docker may be using it):




Starting the frontend on port 5174 because 5173 is in use.




Identifying the issue: `localhost:8000` resolves to IPv6 and hits Docker; our FastAPI listens on IPv4 `127.0.0.1:8000`. Updating the Vite proxy to `http://127.0.0.1:8000` and restarting the frontend.




Here’s what’s in place:

### Done
1. **Prereqs** – `ollama`, Python 3.14, `pip`, Node 24, npm are available.
2. **Ollama** – Already running; pulled **`llama3.2:3b`**, **`llava:7b`**, **`nomic-embed-text`**.
3. **Backend** – Virtualenv at [`backend/.venv`](backend/.venv), deps installed. API is up with  
   `VISION_MODEL=llava:7b` (matches the plan; default in code is `moondream`).
4. **Frontend** – `npm install` completed; Vite is running.
5. **Health** – `GET /api/health` returns `ok` and `ollama: connected`.

### How to open it
- **App (UI):** **http://localhost:5175/**  
  Port **5173** (and 5174) are already used on your machine (e.g. Docker), so Vite is on **5175**.
- **API (direct):** **http://127.0.0.1:8000/api/health**

### Dev proxy fix
`localhost:8000` was resolving to **IPv6** and hitting **Docker** on `:8000`, not FastAPI. The Vite proxy target was changed to **`http://127.0.0.1:8000`** in [`frontend/vite.config.ts`](frontend/vite.config.ts) so `/api` goes to this project’s backend.

### Processes (background)
- **Backend:** `uvicorn` with reload in `backend/` (PID ~7177 in the tool session).
- **Frontend:** `npm run dev` on port **5175**.

To run again later:
```bash
# Terminal 1 — ensure Ollama is up, then:
cd backend && . .venv/bin/activate && VISION_MODEL=llava:7b uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2:
cd frontend && npm run dev -- --port 5175 --strictPort --host 0.0.0.0
```

---

**User**

launch the app now

---

**Cursor**


Checking service status and starting anything that isn't running.



