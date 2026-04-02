const API_BASE = '/api';

export interface Document {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  upload_time: string;
  status: 'queued' | 'processing' | 'indexed' | 'error';
  chunk_count: number;
  error_message: string | null;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Source {
  filename: string;
  file_type: string;
  relevance: number;
  page?: number;
}

export interface Message {
  id: number;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  sources: Source[] | null;
  confidence: string | null;
  created_at: string;
}

export async function uploadFile(file: File): Promise<Document> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Upload failed');
  }
  return res.json();
}

export async function getDocuments(): Promise<Document[]> {
  const res = await fetch(`${API_BASE}/documents`);
  const data = await res.json();
  return data.documents;
}

export async function getDocument(docId: string): Promise<Document> {
  const res = await fetch(`${API_BASE}/documents/${docId}`);
  return res.json();
}

export async function getConversations(): Promise<Conversation[]> {
  const res = await fetch(`${API_BASE}/conversations`);
  const data = await res.json();
  return data.conversations;
}

export async function createConversation(title: string): Promise<Conversation> {
  const res = await fetch(`${API_BASE}/conversations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
  return res.json();
}

export async function getMessages(conversationId: string): Promise<Message[]> {
  const res = await fetch(`${API_BASE}/conversations/${conversationId}/messages`);
  const data = await res.json();
  return data.messages;
}

export async function* streamChat(
  query: string,
  conversationId?: string
): AsyncGenerator<{ type: string; content?: string; conversation_id?: string; sources?: Source[]; confidence?: string }> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, conversation_id: conversationId }),
  });

  if (!res.ok) throw new Error('Chat request failed');
  if (!res.body) throw new Error('No response body');

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          yield data;
        } catch {
          // skip malformed
        }
      }
    }
  }
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`);
    return res.ok;
  } catch {
    return false;
  }
}
