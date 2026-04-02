import { useState, useEffect, useRef, useCallback } from 'react';
import {
  getConversations,
  getMessages,
  streamChat,
  deleteConversation,
  renameConversation,
  getArchitectureSummary,
  type Conversation,
  type Message,
  type ChatDoneEvent,
} from '../services/api';
import '../styles/chat.css';

interface ResponseMeta {
  confidence: string;
  confidence_score?: number;
  needs_more_data?: boolean;
  coverage_gaps?: string[];
  cross_referenced?: boolean;
}

export default function ChatAssistant() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [streamContent, setStreamContent] = useState('');
  const [lastMeta, setLastMeta] = useState<ResponseMeta | null>(null);
  const [archLoading, setArchLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const refreshConversations = useCallback(async () => {
    try {
      const convs = await getConversations();
      setConversations(convs);
    } catch { /* */ }
  }, []);

  useEffect(() => {
    refreshConversations();
  }, [refreshConversations]);

  useEffect(() => {
    if (activeConvId) {
      getMessages(activeConvId).then(setMessages).catch(() => {});
    }
  }, [activeConvId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamContent]);

  const handleSend = useCallback(async () => {
    const query = input.trim();
    if (!query || streaming) return;

    setInput('');
    setStreaming(true);
    setStreamContent('');
    setLastMeta(null);

    const userMsg: Message = {
      id: Date.now(),
      conversation_id: activeConvId || '',
      role: 'user',
      content: query,
      sources: null,
      confidence: null,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);

    let fullContent = '';
    let convId = activeConvId;

    try {
      for await (const chunk of streamChat(query, activeConvId || undefined)) {
        if (chunk.type === 'token' && chunk.content) {
          fullContent += chunk.content;
          setStreamContent(fullContent);
        } else if (chunk.type === 'done') {
          const done = chunk as ChatDoneEvent;
          convId = done.conversation_id || convId;

          const meta: ResponseMeta = {
            confidence: done.confidence,
            confidence_score: done.confidence_score,
            needs_more_data: done.needs_more_data,
            coverage_gaps: done.coverage_gaps,
            cross_referenced: done.cross_referenced,
          };
          setLastMeta(meta);

          const assistantMsg: Message = {
            id: Date.now() + 1,
            conversation_id: convId || '',
            role: 'assistant',
            content: fullContent,
            sources: done.sources || null,
            confidence: done.confidence || null,
            created_at: new Date().toISOString(),
          };
          setMessages(prev => [...prev, assistantMsg]);
          setStreamContent('');

          if (convId && convId !== activeConvId) {
            setActiveConvId(convId);
          }
          refreshConversations();
        }
      }
    } catch {
      const errorMsg: Message = {
        id: Date.now() + 1,
        conversation_id: convId || '',
        role: 'assistant',
        content: '❌ Error communicating with the assistant. Please check that Ollama is running.',
        sources: null,
        confidence: null,
        created_at: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMsg]);
      setStreamContent('');
    } finally {
      setStreaming(false);
    }
  }, [input, streaming, activeConvId, refreshConversations]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  const handleNewConv = useCallback(() => {
    setActiveConvId(null);
    setMessages([]);
    setLastMeta(null);
  }, []);

  const handleDeleteConv = useCallback(async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Delete this conversation?')) return;
    try {
      await deleteConversation(convId);
      if (activeConvId === convId) {
        setActiveConvId(null);
        setMessages([]);
      }
      refreshConversations();
    } catch { /* */ }
  }, [activeConvId, refreshConversations]);

  const handleRenameConv = useCallback(async (convId: string, currentTitle: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const newTitle = prompt('Rename conversation:', currentTitle);
    if (!newTitle || newTitle === currentTitle) return;
    try {
      await renameConversation(convId, newTitle);
      refreshConversations();
    } catch { /* */ }
  }, [refreshConversations]);

  const handleArchSummary = useCallback(async () => {
    if (archLoading || streaming) return;
    setArchLoading(true);

    const userMsg: Message = {
      id: Date.now(),
      conversation_id: activeConvId || '',
      role: 'user',
      content: '📐 Generate System Architecture Summary',
      sources: null,
      confidence: null,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);

    try {
      const result = await getArchitectureSummary();
      const assistantMsg: Message = {
        id: Date.now() + 1,
        conversation_id: '',
        role: 'assistant',
        content: result.summary,
        sources: result.sources,
        confidence: result.confidence.level,
        created_at: new Date().toISOString(),
      };
      setMessages(prev => [...prev, assistantMsg]);
      setLastMeta({
        confidence: result.confidence.level,
        confidence_score: result.confidence.score,
        needs_more_data: result.confidence.needs_more_data,
        coverage_gaps: result.source_analysis.coverage_gaps,
        cross_referenced: result.source_analysis.cross_referenced,
      });
    } catch {
      const errorMsg: Message = {
        id: Date.now() + 1,
        conversation_id: '',
        role: 'assistant',
        content: '❌ Failed to generate architecture summary. Ensure documents are uploaded and Ollama is running.',
        sources: null,
        confidence: null,
        created_at: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setArchLoading(false);
    }
  }, [archLoading, streaming, activeConvId]);

  return (
    <div className="chat">
      <div className="chat__body">
        <div className="chat__sidebar">
          <div className="chat__sidebar-header">
            <span className="chat__sidebar-title">History</span>
            <button className="chat__new-btn" onClick={handleNewConv}>+ New</button>
          </div>
          <div className="chat__conv-list">
            {conversations.map(conv => (
              <div
                key={conv.id}
                className={`chat__conv-item ${activeConvId === conv.id ? 'chat__conv-item--active' : ''}`}
                onClick={() => { setActiveConvId(conv.id); setLastMeta(null); }}
                title={conv.title}
              >
                <span className="chat__conv-item-title">{conv.title}</span>
                <span className="chat__conv-item-actions">
                  <button onClick={(e) => handleRenameConv(conv.id, conv.title, e)} title="Rename">✎</button>
                  <button onClick={(e) => handleDeleteConv(conv.id, e)} title="Delete">✕</button>
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="chat__main">
          <div className="chat__messages">
            {messages.length === 0 && !streaming && (
              <div className="chat__welcome">
                <div className="icon">🔬</div>
                <div className="title">TeardownOS Assistant</div>
                <div className="subtitle">
                  Upload documents by dragging files onto the desktop. Then ask questions
                  here — the assistant retrieves relevant information and provides cited,
                  cross-referenced answers with confidence scoring.
                </div>
                <div className="chat__quick-actions">
                  <button className="chat__action-btn" onClick={handleArchSummary} disabled={archLoading}>
                    📐 Generate Architecture Summary
                  </button>
                </div>
              </div>
            )}

            {messages.map(msg => (
              <MessageBubble key={msg.id} message={msg} />
            ))}

            {streaming && streamContent && (
              <div className="chat-message chat-message--assistant">
                <span className="chat-message__role">assistant</span>
                <div className="chat-message__bubble">{streamContent}</div>
              </div>
            )}

            {lastMeta && (
              <MetaPanel meta={lastMeta} />
            )}

            <div ref={messagesEndRef} />
          </div>

          {streaming && (
            <div className="chat__streaming-indicator">
              <span className="processing-spinner" />
              <span>Generating response...</span>
            </div>
          )}

          {archLoading && (
            <div className="chat__streaming-indicator">
              <span className="processing-spinner" />
              <span>Generating architecture summary (this may take a minute)...</span>
            </div>
          )}

          <div className="chat__input-area">
            <button
              className="chat__arch-btn"
              onClick={handleArchSummary}
              disabled={archLoading || streaming}
              title="Generate System Architecture Summary"
            >
              📐
            </button>
            <textarea
              className="chat__input"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your uploaded documents..."
              rows={1}
              disabled={streaming || archLoading}
            />
            <button className="chat__send-btn" onClick={handleSend} disabled={!input.trim() || streaming || archLoading}>
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetaPanel({ meta }: { meta: ResponseMeta }) {
  return (
    <div className="chat-meta-panel">
      <div className="chat-meta-panel__row">
        <span className={`chat-meta-panel__confidence chat-meta-panel__confidence--${meta.confidence}`}>
          {meta.confidence.toUpperCase()} CONFIDENCE
          {meta.confidence_score !== undefined && ` (${(meta.confidence_score * 100).toFixed(0)}%)`}
        </span>
        {meta.cross_referenced && (
          <span className="chat-meta-panel__badge chat-meta-panel__badge--cross-ref">✓ Cross-referenced</span>
        )}
        {!meta.cross_referenced && (
          <span className="chat-meta-panel__badge chat-meta-panel__badge--single">⚠ Single source</span>
        )}
        {meta.needs_more_data && (
          <span className="chat-meta-panel__badge chat-meta-panel__badge--needs-data">📋 More data needed</span>
        )}
      </div>
      {meta.coverage_gaps && meta.coverage_gaps.length > 0 && (
        <div className="chat-meta-panel__gaps">
          <span className="chat-meta-panel__gaps-title">Data gaps:</span>
          {meta.coverage_gaps.map((gap, i) => (
            <span key={i} className="chat-meta-panel__gap-item">• {gap}</span>
          ))}
        </div>
      )}
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  return (
    <div className={`chat-message chat-message--${message.role}`}>
      <span className="chat-message__role">{message.role}</span>
      <div className="chat-message__bubble">{message.content}</div>
      {message.role === 'assistant' && (
        <div className="chat-message__meta">
          {message.confidence && (
            <span className={`chat-message__confidence chat-message__confidence--${message.confidence}`}>
              {message.confidence} confidence
            </span>
          )}
          {message.sources && message.sources.length > 0 && (
            <span className="chat-message__sources">
              Sources: {message.sources.map((s, i) => (
                <span key={i} title={`Relevance: ${(s.relevance * 100).toFixed(0)}%${s.page ? ` | Page ${s.page}` : ''}`}>
                  {s.filename}{i < message.sources!.length - 1 ? ', ' : ''}
                </span>
              ))}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
