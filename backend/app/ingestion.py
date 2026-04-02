import base64
import hashlib
import re
from pathlib import Path

import fitz  # PyMuPDF
import ollama
from PIL import Image

from app.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBED_MODEL,
    IMAGE_EXTENSIONS,
    OLLAMA_BASE_URL,
    VISION_MODEL,
)
from app.vectorstore import get_collection


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks, respecting sentence boundaries where possible."""
    if not text or not text.strip():
        return []

    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        words = sentence.split()
        sentence_length = len(words)

        if current_length + sentence_length > chunk_size and current_chunk:
            chunk_text_str = " ".join(current_chunk)
            if chunk_text_str.strip():
                chunks.append(chunk_text_str.strip())

            overlap_words = []
            overlap_count = 0
            for s in reversed(current_chunk):
                s_words = s.split()
                if overlap_count + len(s_words) <= overlap:
                    overlap_words.insert(0, s)
                    overlap_count += len(s_words)
                else:
                    break
            current_chunk = overlap_words + [sentence]
            current_length = sum(len(s.split()) for s in current_chunk)
        else:
            current_chunk.append(sentence)
            current_length += sentence_length

    if current_chunk:
        chunk_text_str = " ".join(current_chunk)
        if chunk_text_str.strip():
            chunks.append(chunk_text_str.strip())

    return chunks


def extract_pdf_text(file_path: Path) -> list[dict]:
    """Extract text from PDF, returning list of {page, text} dicts."""
    pages = []
    doc = fitz.open(str(file_path))
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text("text")
        if text.strip():
            pages.append({"page": page_num + 1, "text": text.strip()})
    doc.close()
    return pages


def extract_text_file(file_path: Path) -> str:
    """Read a plain text file."""
    try:
        return file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return file_path.read_text(encoding="latin-1", errors="replace")


def describe_image(file_path: Path) -> str:
    """Use Ollama vision model to describe an image."""
    client = ollama.Client(host=OLLAMA_BASE_URL)
    with open(file_path, "rb") as f:
        img_bytes = f.read()

    img_b64 = base64.b64encode(img_bytes).decode("utf-8")

    response = client.chat(
        model=VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": (
                    "You are a technical documentation analyst for security research. "
                    "Describe this image in detail. If it's a schematic, wiring diagram, "
                    "circuit board, or technical diagram, identify all components, connections, "
                    "labels, and technical specifications visible. If it's a photograph of "
                    "hardware, describe the physical components and any visible markings, "
                    "model numbers, or identifiers."
                ),
                "images": [img_b64],
            }
        ],
    )
    return response["message"]["content"]


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts using Ollama."""
    client = ollama.Client(host=OLLAMA_BASE_URL)
    embeddings = []
    for text in texts:
        resp = client.embed(model=EMBED_MODEL, input=text)
        embeddings.append(resp["embeddings"][0])
    return embeddings


async def ingest_document(doc_id: str, filename: str, file_path: Path) -> int:
    """
    Process a document: extract content, chunk, embed, store in ChromaDB.
    Returns the number of chunks created.
    """
    ext = file_path.suffix.lstrip(".").lower()
    collection = get_collection()

    chunks_data = []

    if ext == "pdf":
        pages = extract_pdf_text(file_path)
        for page_info in pages:
            text_chunks = chunk_text(page_info["text"])
            for i, chunk in enumerate(text_chunks):
                chunks_data.append({
                    "text": chunk,
                    "metadata": {
                        "doc_id": doc_id,
                        "filename": filename,
                        "file_type": "pdf",
                        "page": page_info["page"],
                        "chunk_index": i,
                    },
                })

    elif ext in IMAGE_EXTENSIONS:
        description = describe_image(file_path)
        text_chunks = chunk_text(description)
        for i, chunk in enumerate(text_chunks):
            chunks_data.append({
                "text": chunk,
                "metadata": {
                    "doc_id": doc_id,
                    "filename": filename,
                    "file_type": "image",
                    "chunk_index": i,
                    "description": "Image analysis via vision model",
                },
            })

    else:
        text = extract_text_file(file_path)
        text_chunks = chunk_text(text)
        for i, chunk in enumerate(text_chunks):
            chunks_data.append({
                "text": chunk,
                "metadata": {
                    "doc_id": doc_id,
                    "filename": filename,
                    "file_type": ext,
                    "chunk_index": i,
                },
            })

    if not chunks_data:
        return 0

    texts = [c["text"] for c in chunks_data]
    metadatas = [c["metadata"] for c in chunks_data]
    ids = [
        f"{doc_id}_{hashlib.md5(t.encode()).hexdigest()[:8]}_{i}"
        for i, t in enumerate(texts)
    ]

    embeddings = generate_embeddings(texts)

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    return len(chunks_data)
