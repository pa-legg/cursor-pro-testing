# Product Requirements Document: TeardownOS

## Smart Personal Assistant for Security Researchers

**Version:** 1.0
**Date:** April 2026
**Status:** Draft
**Challenge Reference:** HMGCC Co-Creation — Smart Personal Assistant for Security Researchers

---

## 1. Executive Summary

**TeardownOS** is a standalone, offline-capable web application that presents a familiar Linux desktop environment in the browser, enabling security researchers to ingest, index, search, and interrogate vast quantities of technical documentation about complex industrial machinery. The tool uses local large language models (via Ollama) to provide conversational, citation-backed answers across multimodal inputs — PDFs, images, schematics, datasheets, code, and more — without requiring an internet connection.

The application is designed around the UWEcyber VM web app paradigm: a realistic Linux desktop rendered entirely in the browser, where the user interacts with windows, a taskbar, a file manager, and a terminal, giving security researchers a natural, distraction-free workspace.

---

## 2. Problem Statement

Security researchers assessing industrial control systems (ICS) must manually find, organise, and cross-reference large volumes of open-source technical information — vendor manuals, datasheets, schematics, firmware code, forum discussions, and teardown photographs. This research phase is laborious and delays the actual vulnerability analysis.

There is currently no single tool that:
- Operates fully offline on a laptop.
- Ingests and indexes structured and unstructured multimodal data.
- Provides conversational, citation-backed querying with confidence scoring.
- Maintains long-running conversation memory across sessions spanning weeks.

---

## 3. User Persona

**Alicia** — an experienced security researcher focused on industrial control systems. She has been tasked to assess an industrial additive manufacturing machine for a classified manufacturing facility. She needs to rapidly build a knowledge base from vendor manuals, component datasheets, wiring diagrams, firmware dumps, forum posts, and teardown photos, then interrogate that knowledge base conversationally to understand the machine's architecture, interfaces, and potential vulnerabilities.

---

## 4. Product Vision

A browser-based Linux desktop environment where a security researcher can:

1. **Drag-and-drop** files (PDFs, images, code, text) onto the desktop window.
2. See those files appear in `~/Documents` in the virtual file manager.
3. Watch as the system automatically ingests, chunks, embeds, and indexes the content.
4. Open a **Chat Assistant** window to ask natural-language questions about all ingested material.
5. Receive well-grounded answers with **source citations**, **confidence scores**, and **alternative theories** when answers are uncertain.
6. Continue conversations across sessions with full **persistent memory**.

---

## 5. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│  Browser (React + Vite)                             │
│  ┌──────────────┐  ┌─────────────┐  ┌───────────┐  │
│  │ File Manager  │  │ Chat Window │  │  Taskbar   │  │
│  │ (~/Documents) │  │ (Assistant) │  │ (Launcher) │  │
│  └──────┬───────┘  └──────┬──────┘  └───────────┘  │
│         │                 │                         │
│  Drag-and-Drop Zone (whole window)                  │
└─────────┼─────────────────┼─────────────────────────┘
          │ REST / WebSocket│
┌─────────▼─────────────────▼─────────────────────────┐
│  Backend (Python / FastAPI)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ Ingestion    │  │ RAG Engine   │  │ Session   │ │
│  │ Pipeline     │  │ (Query +     │  │ Memory    │ │
│  │ (PDF, Image, │  │  Retrieval + │  │ (SQLite)  │ │
│  │  Code, Text) │  │  Generation) │  │           │ │
│  └──────┬───────┘  └──────┬───────┘  └───────────┘ │
│         │                 │                         │
│  ┌──────▼─────────────────▼──────┐  ┌────────────┐ │
│  │      ChromaDB (Vector Store)  │  │   Ollama   │ │
│  │      Embeddings + Metadata    │  │  (LLM +    │ │
│  │                               │  │   Vision)  │ │
│  └───────────────────────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────┘
```

---

## 6. Functional Requirements

### 6.1 Virtual Linux Desktop (FR-DESKTOP)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-DESKTOP-01 | Browser-based Linux desktop with taskbar, window management, and wallpaper | Essential |
| FR-DESKTOP-02 | Draggable, resizable, minimisable, closeable application windows | Essential |
| FR-DESKTOP-03 | Taskbar with application launcher icons and clock | Essential |
| FR-DESKTOP-04 | Desktop replicates the look and feel of a Linux environment (dark theme, monospace fonts, terminal aesthetic) | Essential |

### 6.2 File Management (FR-FILE)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-FILE-01 | Drag-and-drop files from the host OS anywhere onto the web app window | Essential |
| FR-FILE-02 | Dropped files appear in `~/Documents` in the virtual file manager | Essential |
| FR-FILE-03 | File manager window showing directory tree with file icons, sizes, and types | Essential |
| FR-FILE-04 | Support for: PDF, PNG, JPG, JPEG, GIF, BMP, TIFF, SVG, TXT, MD, CSV, JSON, XML, HTML, source code files (.py, .c, .cpp, .rs, .js, .ts, .java, .go, .sh) | Essential |
| FR-FILE-05 | Visual processing status indicator per file (queued → processing → indexed → error) | Essential |
| FR-FILE-06 | File preview capability for text and image files | Desirable |

### 6.3 Document Ingestion Pipeline (FR-INGEST)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-INGEST-01 | Automatic ingestion on file upload — extract text, chunk, embed, and store | Essential |
| FR-INGEST-02 | PDF text extraction with layout-aware parsing (PyMuPDF / pdfplumber) | Essential |
| FR-INGEST-03 | Image understanding via Ollama multimodal model (LLaVA) for schematics, photos, diagrams | Essential |
| FR-INGEST-04 | Source code ingestion with language-aware chunking | Essential |
| FR-INGEST-05 | Metadata extraction: filename, file type, page number, chunk index | Essential |
| FR-INGEST-06 | Chunking strategy: 512-token chunks with 64-token overlap, respecting natural boundaries | Essential |
| FR-INGEST-07 | Vector embeddings stored in ChromaDB with document metadata | Essential |

### 6.4 Chat Assistant / RAG Engine (FR-CHAT)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-CHAT-01 | Chat window with terminal-style aesthetic, streaming responses | Essential |
| FR-CHAT-02 | Natural language querying across all ingested documents | Essential |
| FR-CHAT-03 | Retrieval-Augmented Generation: retrieve top-k relevant chunks, synthesise answer | Essential |
| FR-CHAT-04 | Source citations in every response — file name, page/section, relevance score | Essential |
| FR-CHAT-05 | Confidence score (high/medium/low) per response, flagging when more data is needed | Essential |
| FR-CHAT-06 | Alternative theories presented when answer confidence is low | Essential |
| FR-CHAT-07 | Conversation memory persisted to SQLite — resume conversations across sessions/weeks | Essential |
| FR-CHAT-08 | Multiple named conversation threads | Desirable |
| FR-CHAT-09 | Response validation: cross-check claims against multiple source chunks before presenting | Essential |

### 6.5 Offline Operation (FR-OFFLINE)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-OFFLINE-01 | Entire system operates without internet — Ollama models pre-downloaded | Essential |
| FR-OFFLINE-02 | All dependencies bundled or installable from local packages | Essential |

### 6.6 System Architecture Understanding (FR-ARCH)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-ARCH-01 | Ability to understand and summarise system architecture from ingested documents | Essential |
| FR-ARCH-02 | Identify physical components, interfaces, data protocols from technical documentation | Essential |
| FR-ARCH-03 | Generate component-level technical summaries | Essential |

---

## 7. Non-Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-01 | Must run on a modern laptop (16GB RAM, 8-core CPU) without GPU requirement (CPU inference via Ollama) | Essential |
| NFR-02 | Document ingestion: < 30 seconds per typical PDF page | Essential |
| NFR-03 | Chat response latency: < 15 seconds for typical query (CPU inference) | Essential |
| NFR-04 | Support at least 1000 documents / 10,000 chunks in the index | Essential |
| NFR-05 | Persistent storage: all data survives browser refresh and system restart | Essential |
| NFR-06 | Security: no data leaves the local machine | Essential |

---

## 8. Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | React 18 + Vite + TypeScript | Fast dev, component model, SPA |
| UI Style | Custom CSS (Linux desktop theme) | UWEcyber VM aesthetic |
| Backend | Python 3.11+ / FastAPI | Async, fast, great ecosystem |
| LLM Runtime | Ollama (local) | Offline LLM inference, multi-model |
| Text LLM | `llama3.2:3b` (or similar) | Good balance of quality and speed |
| Vision LLM | `llava:7b` | Multimodal understanding |
| Embeddings | `nomic-embed-text` via Ollama | Local embeddings, no API keys |
| Vector Store | ChromaDB | Lightweight, embeddable, Python-native |
| PDF Parsing | PyMuPDF (fitz) | Fast, layout-aware |
| OCR Backup | Tesseract (via pytesseract) | Scanned document fallback |
| Database | SQLite | Conversation memory, session state |
| File Storage | Local filesystem | Uploaded documents |

---

## 9. User Workflow

```
1. User opens TeardownOS in browser → Linux desktop loads
2. User drags files from host OS onto the browser window
3. Files appear in ~/Documents in the File Manager
4. Ingestion pipeline processes each file:
   - PDF → extract text → chunk → embed → store
   - Image → describe via LLaVA → chunk description → embed → store
   - Code → parse → chunk with language awareness → embed → store
   - Text → chunk → embed → store
5. Status indicators update: queued → processing → indexed
6. User opens Chat Assistant from taskbar
7. User types natural-language question
8. RAG engine retrieves relevant chunks from ChromaDB
9. LLM generates answer with citations and confidence score
10. User asks follow-up questions — context maintained
11. Conversations persist across sessions
```

---

## 10. Acceptance Criteria

1. User can drag-and-drop a PDF onto the browser and it appears in the virtual file manager.
2. The PDF is automatically ingested and searchable within 60 seconds.
3. User can ask a natural-language question about the PDF content and receive a cited answer.
4. Image files (schematics, photos) can be ingested and their content queried.
5. Confidence scores are displayed with each response.
6. Conversations persist across page refreshes.
7. The entire system works offline after initial setup.

---

## 11. Out of Scope (Phase 1)

- Autonomous web scraping for source data.
- User profiling and adaptive behaviour (Phase 2).
- Multi-language translation (Phase 2).
- Collaborative multi-user mode.
- Mobile/tablet optimisation.

---

## 12. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| CPU-only LLM inference is slow | Medium | Use smaller quantised models (3B-7B), stream responses |
| Image understanding quality varies | Medium | Combine OCR + vision model, let user provide context |
| Hallucination in LLM responses | High | RAG grounding, confidence scoring, source citation, chunk verification |
| Large document sets exhaust memory | Medium | Streaming ingestion, chunked processing |

---

## 13. Future Roadmap

- **Phase 2:** User profiling, proactive suggestions, non-English support
- **Phase 3:** Component relationship graphing, attack surface visualisation
- **Phase 4:** Integration with vulnerability databases (NVD, CVE) when online
