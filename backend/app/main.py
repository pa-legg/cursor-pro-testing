import asyncio
import json
import uuid
from pathlib import Path

import ollama as ollama_client
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import OLLAMA_BASE_URL, SUPPORTED_EXTENSIONS, UPLOAD_DIR
from app.database import (
    add_message,
    create_conversation,
    create_document,
    delete_conversation_db,
    delete_document_db,
    get_all_documents,
    get_conversations,
    get_messages,
    init_db,
    rename_conversation_db,
    update_document_status,
)
from app.ingestion import ingest_document
from app.rag import generate_architecture_summary, generate_rag_response_stream
from app.vectorstore import delete_document_vectors

app = FastAPI(title="TeardownOS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/api/health")
async def health():
    """Health check that also verifies Ollama connectivity."""
    ollama_ok = False
    try:
        client = ollama_client.Client(host=OLLAMA_BASE_URL)
        models = client.list()
        ollama_ok = True
        model_names = [m.model for m in models.models] if models.models else []
    except Exception:
        model_names = []

    return {
        "status": "ok" if ollama_ok else "degraded",
        "service": "TeardownOS",
        "ollama": "connected" if ollama_ok else "disconnected",
        "models": model_names,
    }


# --- Document endpoints ---


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: .{ext}")

    doc_id = str(uuid.uuid4())
    safe_filename = file.filename.replace("/", "_").replace("\\", "_")
    file_path = UPLOAD_DIR / f"{doc_id}_{safe_filename}"

    content = await file.read()
    file_path.write_bytes(content)

    await create_document(doc_id, safe_filename, ext, len(content))

    asyncio.create_task(_process_document(doc_id, safe_filename, file_path))

    return {
        "id": doc_id,
        "filename": safe_filename,
        "status": "queued",
        "file_type": ext,
        "file_size": len(content),
    }


async def _process_document(doc_id: str, filename: str, file_path: Path):
    try:
        await update_document_status(doc_id, "processing")
        chunk_count = await asyncio.to_thread(
            _sync_ingest, doc_id, filename, file_path
        )
        await update_document_status(doc_id, "indexed", chunk_count=chunk_count)
    except Exception as e:
        await update_document_status(doc_id, "error", error_message=str(e))


def _sync_ingest(doc_id: str, filename: str, file_path: Path) -> int:
    import asyncio as _asyncio
    loop = _asyncio.new_event_loop()
    try:
        return loop.run_until_complete(ingest_document(doc_id, filename, file_path))
    finally:
        loop.close()


@app.get("/api/documents")
async def list_documents():
    docs = await get_all_documents()
    return {"documents": docs}


@app.get("/api/documents/{doc_id}")
async def get_document(doc_id: str):
    docs = await get_all_documents()
    for doc in docs:
        if doc["id"] == doc_id:
            return doc
    raise HTTPException(status_code=404, detail="Document not found")


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document and its vectors from the index."""
    docs = await get_all_documents()
    doc = next((d for d in docs if d["id"] == doc_id), None)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    delete_document_vectors(doc_id)
    await delete_document_db(doc_id)

    for f in UPLOAD_DIR.glob(f"{doc_id}_*"):
        f.unlink(missing_ok=True)

    return {"status": "deleted", "id": doc_id}


# --- Architecture Summary ---


@app.get("/api/architecture/summary")
async def get_architecture_summary():
    """Generate a structured system architecture summary from all indexed documents."""
    try:
        result = await asyncio.to_thread(generate_architecture_summary)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Conversation endpoints ---


class CreateConversationRequest(BaseModel):
    title: str = "New Conversation"


class RenameConversationRequest(BaseModel):
    title: str


class ChatRequest(BaseModel):
    query: str
    conversation_id: str | None = None


@app.post("/api/conversations")
async def create_new_conversation(req: CreateConversationRequest):
    conv_id = str(uuid.uuid4())
    await create_conversation(conv_id, req.title)
    return {"id": conv_id, "title": req.title}


@app.get("/api/conversations")
async def list_conversations():
    convs = await get_conversations()
    return {"conversations": convs}


@app.get("/api/conversations/{conv_id}/messages")
async def list_messages(conv_id: str):
    msgs = await get_messages(conv_id)
    return {"messages": msgs}


@app.patch("/api/conversations/{conv_id}")
async def rename_conversation(conv_id: str, req: RenameConversationRequest):
    await rename_conversation_db(conv_id, req.title)
    return {"id": conv_id, "title": req.title}


@app.delete("/api/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    await delete_conversation_db(conv_id)
    return {"status": "deleted", "id": conv_id}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    conv_id = req.conversation_id
    if not conv_id:
        conv_id = str(uuid.uuid4())
        title = req.query[:50] + ("..." if len(req.query) > 50 else "")
        await create_conversation(conv_id, title)

    await add_message(conv_id, "user", req.query)

    history = await get_messages(conv_id)
    history_for_rag = [{"role": m["role"], "content": m["content"]} for m in history[:-1]]

    async def event_stream():
        full_answer = ""
        sources = []
        confidence = "medium"
        metadata = {}

        for chunk in generate_rag_response_stream(req.query, history_for_rag):
            if chunk["type"] == "token":
                full_answer += chunk["content"]
                yield f"data: {json.dumps({'type': 'token', 'content': chunk['content']})}\n\n"
            elif chunk["type"] == "done":
                full_answer = chunk["content"]
                sources = chunk.get("sources", [])
                confidence = chunk.get("confidence", "medium")
                metadata = {
                    "confidence_score": chunk.get("confidence_score", 0),
                    "needs_more_data": chunk.get("needs_more_data", False),
                    "coverage_gaps": chunk.get("coverage_gaps", []),
                    "cross_referenced": chunk.get("cross_referenced", False),
                }

        await add_message(conv_id, "assistant", full_answer, sources=sources, confidence=confidence)

        yield f"data: {json.dumps({'type': 'done', 'conversation_id': conv_id, 'sources': sources, 'confidence': confidence, **metadata})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
