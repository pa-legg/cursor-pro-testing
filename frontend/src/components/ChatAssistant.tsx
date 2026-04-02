import { useState, useEffect, useRef, useCallback } from 'react';
import { getConversations, getMessages, streamChat, type Conversation, type Message } from '../services/api';
import '../styles/chat.css';

export default function ChatAssistant() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [streamContent, setStreamContent] = useState('');
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
          convId = chunk.conversation_id || convId;

          const assistantMsg: Message = {
            id: Date.now() + 1,
            conversation_id: convId || '',
            role: 'assistant',
            content: fullContent,
            sources: chunk.sources || null,
            confidence: chunk.confidence || null,
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
    } catch (err) {
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
  }, []);

  const selectConversation = useCallback((convId: string) => {
    setActiveConvId(convId);
  }, []);

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
                onClick={() => selectConversation(conv.id)}
                title={conv.title}
              >
                {conv.title}
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
                  Ask questions about uploaded documents. The assistant uses RAG to retrieve relevant information
                  and provides cited, confidence-scored answers. Upload documents by dragging files onto the desktop.
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

            <div ref={messagesEndRef} />
          </div>

          {streaming && (
            <div className="chat__streaming-indicator">
              <span className="processing-spinner" />
              <span>Generating response...</span>
            </div>
          )}

          <div className="chat__input-area">
            <textarea
              className="chat__input"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your uploaded documents..."
              rows={1}
              disabled={streaming}
            />
            <button className="chat__send-btn" onClick={handleSend} disabled={!input.trim() || streaming}>
              Send
            </button>
          </div>
        </div>
      </div>
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
