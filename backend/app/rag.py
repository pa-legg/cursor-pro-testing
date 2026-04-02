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


def _analyse_source_coverage(contexts: list[dict]) -> dict:
    """Analyse retrieved sources for cross-referencing and coverage gaps."""
    if not contexts:
        return {
            "unique_documents": 0,
            "unique_files": [],
            "cross_referenced": False,
            "source_types": [],
            "coverage_gaps": ["No documents in the knowledge base. Upload relevant files first."],
            "agreement_count": 0,
        }

    filenames = set()
    file_types = set()
    for ctx in contexts:
        meta = ctx["metadata"]
        filenames.add(meta.get("filename", "Unknown"))
        file_types.add(meta.get("file_type", "unknown"))

    unique_docs = len(filenames)
    cross_referenced = unique_docs >= 2

    coverage_gaps = []
    present_types = file_types
    desired_types = {"pdf", "image", "txt", "code"}
    type_labels = {
        "pdf": "technical manuals/datasheets (PDF)",
        "image": "schematics/diagrams (images)",
        "txt": "text documentation/notes",
        "code": "source code/firmware",
    }
    code_exts = {"py", "c", "cpp", "h", "hpp", "rs", "js", "ts", "java", "go", "sh"}
    normalised = set()
    for t in present_types:
        if t in code_exts:
            normalised.add("code")
        elif t == "image":
            normalised.add("image")
        elif t == "pdf":
            normalised.add("pdf")
        else:
            normalised.add("txt")

    for desired in desired_types - normalised:
        if desired in type_labels:
            coverage_gaps.append(f"No {type_labels[desired]} found — consider uploading this type.")

    if not cross_referenced:
        coverage_gaps.append(
            "Claims are supported by a single document only. "
            "Upload additional sources to enable cross-referencing."
        )

    high_relevance_count = sum(1 for c in contexts if c["relevance"] > 0.5)

    return {
        "unique_documents": unique_docs,
        "unique_files": sorted(filenames),
        "cross_referenced": cross_referenced,
        "source_types": sorted(present_types),
        "coverage_gaps": coverage_gaps,
        "agreement_count": high_relevance_count,
    }


def compute_confidence(contexts: list[dict], source_analysis: dict) -> dict:
    """Enhanced confidence scoring with data sufficiency analysis."""
    if not contexts:
        return {
            "level": "low",
            "score": 0.0,
            "needs_more_data": True,
            "reason": "No relevant documents found in the knowledge base.",
        }

    avg_relevance = sum(c["relevance"] for c in contexts) / len(contexts)
    top_relevance = contexts[0]["relevance"] if contexts else 0
    cross_ref = source_analysis["cross_referenced"]
    unique_docs = source_analysis["unique_documents"]
    agreement = source_analysis["agreement_count"]

    score = (top_relevance * 0.35) + (avg_relevance * 0.25) + (min(agreement, 3) / 3 * 0.2)
    if cross_ref:
        score += 0.2
    score = round(min(score, 1.0), 2)

    needs_more_data = False
    reasons = []

    if score >= 0.65 and cross_ref:
        level = "high"
    elif score >= 0.40:
        level = "medium"
        if not cross_ref:
            reasons.append("Single source — cross-reference with additional documents recommended.")
            needs_more_data = True
    else:
        level = "low"
        needs_more_data = True
        if top_relevance < 0.4:
            reasons.append("Low relevance match — uploaded documents may not cover this topic.")
        if not cross_ref:
            reasons.append("Cannot cross-reference — only one source document available.")

    if source_analysis["coverage_gaps"]:
        needs_more_data = True

    reason = " ".join(reasons) if reasons else (
        "Multiple corroborating sources found." if cross_ref else "Adequate single-source match."
    )

    return {
        "level": level,
        "score": score,
        "needs_more_data": needs_more_data,
        "reason": reason,
    }


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


def _build_system_prompt(contexts: list[dict], source_analysis: dict, confidence: dict) -> str:
    """Build enhanced system prompt with validation instructions."""
    context_text = ""
    if contexts:
        for i, ctx in enumerate(contexts):
            meta = ctx["metadata"]
            source_label = meta.get("filename", "Unknown")
            if "page" in meta:
                source_label += f" (page {meta['page']})"
            context_text += (
                f"\n[Source {i+1}: {source_label} | "
                f"Relevance: {ctx['relevance']} | "
                f"Type: {meta.get('file_type', 'unknown')}]\n{ctx['text']}\n"
            )

    system_prompt = (
        "You are TeardownOS Assistant, a technical security research assistant. "
        "You help security researchers understand complex industrial control systems, "
        "their components, interfaces, protocols, and potential vulnerabilities.\n\n"
        "RESPONSE RULES:\n"
        "1. Base your answers ONLY on the provided source material. Never fabricate information.\n"
        "2. Always cite which source(s) support each claim using [Source N] notation.\n"
        "3. If multiple sources agree on a fact, note this explicitly (e.g. 'confirmed by Sources 1 and 3').\n"
        "4. If sources conflict or are ambiguous, present ALL interpretations clearly as alternatives.\n"
        "5. If the sources don't contain enough information to fully answer, say so explicitly "
        "and describe what additional documentation would help.\n"
        "6. Be precise and technical — security researchers need accuracy over brevity.\n\n"
        "VALIDATION RULES:\n"
        "7. Before making any claim, verify it appears in at least one source. Do NOT extrapolate beyond sources.\n"
        "8. For each technical specification (voltage, frequency, protocol version, memory address), "
        "quote the exact value from the source rather than paraphrasing.\n"
        "9. If a claim is supported by only one source, prefix it with '[Single source]'.\n"
        "10. If you detect any contradiction between sources, flag it with '⚠️ CONFLICT:' and explain both positions.\n\n"
        "ARCHITECTURE ANALYSIS:\n"
        "11. When describing system architecture, identify: physical components, data interfaces, "
        "communication protocols, firmware/software layers, and security-relevant attack surfaces.\n"
        "12. Structure architectural responses as: Overview → Components → Interfaces → Protocols → Security Notes.\n"
    )

    if context_text:
        system_prompt += f"\n--- RETRIEVED SOURCES ({len(contexts)} chunks from {source_analysis['unique_documents']} documents) ---\n"
        system_prompt += context_text
        system_prompt += "\n--- END SOURCES ---\n"

        if source_analysis["cross_referenced"]:
            system_prompt += (
                f"\nℹ️ Cross-referencing enabled: {source_analysis['unique_documents']} documents available. "
                "Prioritise claims supported by multiple sources.\n"
            )
        else:
            system_prompt += (
                "\n⚠️ Single-source mode: all chunks come from one document. "
                "Clearly indicate that claims cannot be independently verified.\n"
            )
    else:
        system_prompt += (
            "\nNo relevant documents were found in the knowledge base. "
            "Let the user know they should upload relevant documents first.\n"
        )

    return system_prompt


def _build_confidence_suffix(confidence: dict, source_analysis: dict) -> str:
    """Build structured metadata suffix appended after the LLM response."""
    parts = []

    if confidence["needs_more_data"]:
        parts.append(f"\n\n📊 **Confidence: {confidence['level'].upper()}** (score: {confidence['score']})")
        parts.append(f"*{confidence['reason']}*")
        if source_analysis["coverage_gaps"]:
            parts.append("\n**📋 Data gaps identified:**")
            for gap in source_analysis["coverage_gaps"]:
                parts.append(f"  • {gap}")
    else:
        parts.append(f"\n\n📊 **Confidence: {confidence['level'].upper()}** (score: {confidence['score']})")
        parts.append(f"*{confidence['reason']}*")

    return "\n".join(parts)


def generate_rag_response_stream(query: str, conversation_history: list[dict] = None):
    """Stream a RAG response with validation, cross-checking, and confidence analysis."""
    contexts = retrieve_context(query, top_k=TOP_K)
    source_analysis = _analyse_source_coverage(contexts)
    confidence = compute_confidence(contexts, source_analysis)
    sources = build_sources(contexts)

    system_prompt = _build_system_prompt(contexts, source_analysis, confidence)

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

    suffix = _build_confidence_suffix(confidence, source_analysis)
    full_response += suffix
    yield {"type": "token", "content": suffix}

    yield {
        "type": "done",
        "content": full_response,
        "sources": sources,
        "confidence": confidence["level"],
        "confidence_score": confidence["score"],
        "needs_more_data": confidence["needs_more_data"],
        "coverage_gaps": source_analysis["coverage_gaps"],
        "cross_referenced": source_analysis["cross_referenced"],
    }


def generate_architecture_summary(top_k: int = 20) -> dict:
    """Generate a structured system architecture summary from all indexed documents."""
    arch_queries = [
        "system architecture components interfaces hardware",
        "communication protocols data interfaces network",
        "processors microcontrollers firmware software",
        "physical components wiring connections power",
        "security vulnerabilities attack surface",
    ]

    all_contexts = []
    seen_texts = set()
    for q in arch_queries:
        ctx = retrieve_context(q, top_k=top_k // len(arch_queries))
        for c in ctx:
            text_key = c["text"][:100]
            if text_key not in seen_texts:
                seen_texts.add(text_key)
                all_contexts.append(c)

    source_analysis = _analyse_source_coverage(all_contexts)
    confidence = compute_confidence(all_contexts, source_analysis)
    sources = build_sources(all_contexts)

    context_text = ""
    for i, ctx in enumerate(all_contexts):
        meta = ctx["metadata"]
        source_label = meta.get("filename", "Unknown")
        if "page" in meta:
            source_label += f" (page {meta['page']})"
        context_text += f"\n[Source {i+1}: {source_label}]\n{ctx['text']}\n"

    system_prompt = (
        "You are TeardownOS Assistant. Generate a structured SYSTEM ARCHITECTURE SUMMARY "
        "from the provided source material about an industrial system under security assessment.\n\n"
        "Produce the summary in EXACTLY this structure:\n\n"
        "## System Overview\nBrief description of the system and its purpose.\n\n"
        "## Physical Components\nList all identified hardware: processors, memory, sensors, actuators, etc. "
        "Include model numbers, specifications, and manufacturer where available.\n\n"
        "## Communication Interfaces\nList all interfaces: Ethernet, Serial, CAN, USB, wireless, etc. "
        "Include protocols, port numbers, and data rates.\n\n"
        "## Software & Firmware\nIdentify OS, RTOS, firmware versions, programming languages, libraries.\n\n"
        "## Data Flows & Protocols\nDescribe how data moves through the system. "
        "Include protocol details (Modbus, EtherNet/IP, OPC-UA, etc.).\n\n"
        "## Security Assessment\nIdentify potential attack surfaces, known vulnerabilities, "
        "default credentials, unencrypted channels, debug interfaces, missing authentication.\n\n"
        "## Information Gaps\nList what information is missing and what additional documents "
        "would help complete the picture.\n\n"
        "RULES:\n"
        "- Cite sources for every claim using [Source N].\n"
        "- Flag single-source claims with '[Single source]'.\n"
        "- Flag conflicts between sources with '⚠️ CONFLICT:'.\n"
        "- Only include information found in the sources. Do not fabricate.\n"
    )

    if context_text:
        system_prompt += f"\n--- ALL AVAILABLE SOURCES ---\n{context_text}\n--- END SOURCES ---\n"

    client = ollama.Client(host=OLLAMA_BASE_URL)
    response = client.chat(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Generate the system architecture summary from all available documents."},
        ],
    )

    return {
        "summary": response["message"]["content"],
        "sources": sources,
        "confidence": confidence,
        "source_analysis": source_analysis,
    }
