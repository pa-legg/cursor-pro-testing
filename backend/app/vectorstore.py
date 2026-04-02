import chromadb
from app.config import CHROMA_DIR

_client = None
_collection = None


def get_chroma_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return _client


def get_collection():
    global _collection
    if _collection is None:
        client = get_chroma_client()
        _collection = client.get_or_create_collection(
            name="teardown_docs",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def query_documents(query_embedding: list[float], top_k: int = 5) -> dict:
    """Query the vector store with an embedding, return top-k results."""
    collection = get_collection()

    if collection.count() == 0:
        return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    return results


def delete_document_vectors(doc_id: str):
    """Delete all vectors belonging to a specific document."""
    collection = get_collection()
    try:
        results = collection.get(where={"doc_id": doc_id})
        if results and results["ids"]:
            collection.delete(ids=results["ids"])
    except Exception:
        pass
