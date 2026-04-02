import aiosqlite
import json
from datetime import datetime
from app.config import SQLITE_DB


async def get_db():
    db = await aiosqlite.connect(str(SQLITE_DB))
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    db = await get_db()
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            upload_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            chunk_count INTEGER DEFAULT 0,
            error_message TEXT
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            sources TEXT,
            confidence TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );
    """)
    await db.commit()
    await db.close()


async def create_document(doc_id: str, filename: str, file_type: str, file_size: int):
    db = await get_db()
    await db.execute(
        "INSERT INTO documents (id, filename, file_type, file_size, upload_time, status) VALUES (?, ?, ?, ?, ?, ?)",
        (doc_id, filename, file_type, file_size, datetime.utcnow().isoformat(), "queued"),
    )
    await db.commit()
    await db.close()


async def update_document_status(doc_id: str, status: str, chunk_count: int = 0, error_message: str = None):
    db = await get_db()
    await db.execute(
        "UPDATE documents SET status = ?, chunk_count = ?, error_message = ? WHERE id = ?",
        (status, chunk_count, error_message, doc_id),
    )
    await db.commit()
    await db.close()


async def get_all_documents():
    db = await get_db()
    cursor = await db.execute("SELECT * FROM documents ORDER BY upload_time DESC")
    rows = await cursor.fetchall()
    await db.close()
    return [dict(r) for r in rows]


async def create_conversation(conv_id: str, title: str):
    db = await get_db()
    now = datetime.utcnow().isoformat()
    await db.execute(
        "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (conv_id, title, now, now),
    )
    await db.commit()
    await db.close()


async def get_conversations():
    db = await get_db()
    cursor = await db.execute("SELECT * FROM conversations ORDER BY updated_at DESC")
    rows = await cursor.fetchall()
    await db.close()
    return [dict(r) for r in rows]


async def add_message(conversation_id: str, role: str, content: str, sources: list = None, confidence: str = None):
    db = await get_db()
    now = datetime.utcnow().isoformat()
    await db.execute(
        "INSERT INTO messages (conversation_id, role, content, sources, confidence, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (conversation_id, role, content, json.dumps(sources) if sources else None, confidence, now),
    )
    await db.execute(
        "UPDATE conversations SET updated_at = ? WHERE id = ?",
        (now, conversation_id),
    )
    await db.commit()
    await db.close()


async def get_messages(conversation_id: str):
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
        (conversation_id,),
    )
    rows = await cursor.fetchall()
    await db.close()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("sources"):
            d["sources"] = json.loads(d["sources"])
        result.append(d)
    return result
