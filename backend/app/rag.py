import ollama
from app.config import EMBED_MODEL, LLM_MODEL, OLLAMA_BASE_URL, TOP_K
from app.vectorstore import query_documents


def get_query_embedding(query: str) -> list[float]:
    client = ollama.Client(host=OLLAMA_BASE_URL)
    resp = client.embed(model=EMBED_MODEL, input=query)
    return resp["embeddings"][0]


def retrieve_context(query: str, top_k: int = TOP_K) -> list[dict]:
    """Retrieve relevant document chunks for a query."""
    embedding = get_query_embedding(query)
    results = query_documents(embedding, top_k=top_k)

    contexts = []
    if results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i] if results["metadatas"][0] else {}
            distance = results["distances"][0][i] if results["distances"][0] else 1.0
            relevance = max(0, 1 - distance)
            contexts.append({
                "text": doc,
                "metadata": meta,
                "relevance": round(relevance, 3),
            })

    return contexts


def compute_confidence(contexts: list[dict]) -> str:
    if not contexts:
        return "low"
    avg_relevance = sum(c["relevance"] for c in contexts) / len(contexts)
    top_relevance = contexts[0]["relevance"] if contexts else 0

    if top_relevance > 0.7 and avg_relevance > 0.5:
        return "high"
    elif top_relevance > 0.4 or avg_relevance > 0.3:
        return "medium"
    return "low"


def build_sources(contexts: list[dict]) -> list[dict]:
    sources = []
    seen = set()
    for ctx in contexts:
        meta = ctx["metadata"]
        key = (meta.get("filename", ""), meta.get("page", ""), meta.get("chunk_index", ""))
        if key not in seen:
            seen.add(key)
            source = {
                "filename": meta.get("filename", "Unknown"),
                "file_type": meta.get("file_type", "unknown"),
                "relevance": ctx["relevance"],
            }
            if "page" in meta:
                source["page"] = meta["page"]
            sources.append(source)
    return sources[:5]


def generate_rag_response(query: str, conversation_history: list[dict] = None) -> dict:
    """Generate a RAG response with citations and confidence."""
    contexts = retrieve_context(query)
    confidence = compute_confidence(contexts)
    sources = build_sources(contexts)

    context_text = ""
    if contexts:
        for i, ctx in enumerate(contexts):
            meta = ctx["metadata"]
            source_label = meta.get("filename", "Unknown")
            if "page" in meta:
                source_label += f" (page {meta['page']})"
            context_text += f"\n[Source {i+1}: {source_label} | Relevance: {ctx['relevance']}]\n{ctx['text']}\n"

    system_prompt = (
        "You are TeardownOS Assistant, a technical security research assistant. "
        "You help security researchers understand complex industrial systems, their components, "
        "interfaces, and potential vulnerabilities.\n\n"
        "RULES:\n"
        "1. Base your answers ONLY on the provided source material.\n"
        "2. Always cite which source(s) support each claim using [Source N] notation.\n"
        "3. If the sources don't contain enough information, say so clearly.\n"
        "4. If sources conflict or are ambiguous, present alternative interpretations.\n"
        "5. Be precise and technical. Security researchers need accuracy.\n"
        "6. When describing system architecture, identify components, interfaces, protocols, and data flows.\n"
    )

    if context_text:
        system_prompt += f"\n--- RETRIEVED SOURCES ---\n{context_text}\n--- END SOURCES ---\n"
    else:
        system_prompt += (
            "\nNo relevant documents were found in the knowledge base. "
            "Let the user know they should upload relevant documents first.\n"
        )

    messages = [{"role": "system", "content": system_prompt}]

    if conversation_history:
        for msg in conversation_history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": query})

    client = ollama.Client(host=OLLAMA_BASE_URL)
    response = client.chat(model=LLM_MODEL, messages=messages)

    answer = response["message"]["content"]

    if confidence == "low":
        answer += (
            "\n\n⚠️ **Low Confidence:** The available sources may not fully address this query. "
            "Consider uploading additional documentation for more reliable answers."
        )

    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
    }


def generate_rag_response_stream(query: str, conversation_history: list[dict] = None):
    """Stream a RAG response, yielding chunks. Returns metadata at end."""
    contexts = retrieve_context(query)
    confidence = compute_confidence(contexts)
    sources = build_sources(contexts)

    context_text = ""
    if contexts:
        for i, ctx in enumerate(contexts):
            meta = ctx["metadata"]
            source_label = meta.get("filename", "Unknown")
            if "page" in meta:
                source_label += f" (page {meta['page']})"
            context_text += f"\n[Source {i+1}: {source_label} | Relevance: {ctx['relevance']}]\n{ctx['text']}\n"

    system_prompt = (
        "You are TeardownOS Assistant, a technical security research assistant. "
        "You help security researchers understand complex industrial systems, their components, "
        "interfaces, and potential vulnerabilities.\n\n"
        "RULES:\n"
        "1. Base your answers ONLY on the provided source material.\n"
        "2. Always cite which source(s) support each claim using [Source N] notation.\n"
        "3. If the sources don't contain enough information, say so clearly.\n"
        "4. If sources conflict or are ambiguous, present alternative interpretations.\n"
        "5. Be precise and technical. Security researchers need accuracy.\n"
        "6. When describing system architecture, identify components, interfaces, protocols, and data flows.\n"
    )

    if context_text:
        system_prompt += f"\n--- RETRIEVED SOURCES ---\n{context_text}\n--- END SOURCES ---\n"
    else:
        system_prompt += (
            "\nNo relevant documents were found in the knowledge base. "
            "Let the user know they should upload relevant documents first.\n"
        )

    messages = [{"role": "system", "content": system_prompt}]

    if conversation_history:
        for msg in conversation_history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": query})

    client = ollama.Client(host=OLLAMA_BASE_URL)
    stream = client.chat(model=LLM_MODEL, messages=messages, stream=True)

    full_response = ""
    for chunk in stream:
        token = chunk["message"]["content"]
        full_response += token
        yield {"type": "token", "content": token}

    if confidence == "low":
        suffix = (
            "\n\n⚠️ **Low Confidence:** The available sources may not fully address this query. "
            "Consider uploading additional documentation for more reliable answers."
        )
        full_response += suffix
        yield {"type": "token", "content": suffix}

    yield {
        "type": "done",
        "content": full_response,
        "sources": sources,
        "confidence": confidence,
    }
