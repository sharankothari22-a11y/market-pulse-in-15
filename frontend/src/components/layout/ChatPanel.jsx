import { useState, useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { apiPost, API_ENDPOINTS } from '@/services/api';
import { cn } from '@/lib/utils';

const initialMessages = [
  { id: 1, type: 'ai', text: 'Welcome to Beaver Intelligence. I can help you analyze Indian market trends, stock signals, and macro indicators. What would you like to know?' },
];

export const ChatPanel = ({ sessionId }) => {
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isTyping) return;
    const userMessage = { id: Date.now(), type: 'user', text: input };
    setMessages((prev) => [...prev, userMessage]);
    const userInput = input;
    setInput('');
    setIsTyping(true);
    setErrorMsg('');
    try {
      const requestBody = { message: userInput };
      if (sessionId) requestBody.session_id = sessionId;
      const response = await apiPost(API_ENDPOINTS.chat, requestBody);
      let responseText = response.response || response.message || response.answer;
      if (!responseText) responseText = 'I received your message but could not generate a response.';
      setMessages((prev) => [...prev, { id: Date.now() + 1, type: 'ai', text: responseText }]);
    } catch (error) {
      console.error('Chat API error:', error);
      setErrorMsg("Couldn't get a response, try again");
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  return (
    <aside
      className="flex flex-col flex-shrink-0"
      style={{
        width: 340,
        backgroundColor: 'var(--bi-bg-card)',
        borderLeft: '1px solid var(--bi-border-subtle)',
      }}
      data-testid="chat-panel"
    >
      {/* Header */}
      <div
        className="flex items-center gap-2 px-4"
        style={{
          height: 56,
          borderBottom: '1px solid var(--bi-border-subtle)',
        }}
      >
        <div
          className="flex items-center justify-center"
          style={{
            width: 28, height: 28, borderRadius: '50%',
            backgroundColor: 'var(--bi-navy-700)',
            color: 'var(--bi-text-inverse)',
            fontSize: 13, fontWeight: 600,
          }}
        >B</div>
        <span style={{ color: 'var(--bi-text-primary)', fontSize: 14, fontWeight: 600 }}>
          Beaver AI
        </span>
      </div>

      {/* Messages */}
      <div
        className="flex-1 overflow-y-auto p-4 space-y-3"
        data-testid="chat-messages"
      >
        {messages.map((msg) => {
          const isUser = msg.type === 'user';
          return (
            <div key={msg.id} className={cn('flex', isUser ? 'justify-end' : 'justify-start')}>
              <div
                className="whitespace-pre-wrap"
                style={{
                  maxWidth: '85%',
                  padding: '10px 14px',
                  fontSize: 13,
                  lineHeight: 1.5,
                  borderRadius: 12,
                  backgroundColor: isUser ? 'var(--bi-navy-700)' : 'var(--bi-bg-subtle)',
                  color: isUser ? 'var(--bi-text-inverse)' : 'var(--bi-text-primary)',
                  borderBottomRightRadius: isUser ? 4 : 12,
                  borderBottomLeftRadius:  isUser ? 12 : 4,
                }}
              >
                {msg.text}
              </div>
            </div>
          );
        })}
        {isTyping && (
          <div className="flex justify-start">
            <div
              style={{
                padding: '10px 14px',
                borderRadius: 12,
                borderBottomLeftRadius: 4,
                backgroundColor: 'var(--bi-bg-subtle)',
              }}
            >
              <div className="flex gap-1">
                {[0, 150, 300].map((d) => (
                  <span key={d} className="animate-bounce"
                        style={{ width: 6, height: 6, borderRadius: '50%',
                                 backgroundColor: 'var(--bi-text-tertiary)',
                                 animationDelay: `${d}ms` }} />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-3" style={{ borderTop: '1px solid var(--bi-border-subtle)' }}>
        {errorMsg && (
          <div
            style={{ fontSize: 12, color: '#DC2626', marginBottom: 6 }}
            data-testid="chat-error"
          >
            {errorMsg}
          </div>
        )}
        <div className="flex gap-2 items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask Beaver about markets…"
            disabled={isTyping}
            style={{
              flex: 1,
              height: 36,
              padding: '0 12px',
              fontSize: 13,
              borderRadius: 8,
              border: '1px solid var(--bi-border-subtle)',
              backgroundColor: 'var(--bi-bg-card)',
              color: 'var(--bi-text-primary)',
            }}
            data-testid="chat-input"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            className="flex items-center justify-center disabled:opacity-40"
            style={{
              width: 36, height: 36,
              borderRadius: 8,
              backgroundColor: 'var(--bi-navy-700)',
              color: 'var(--bi-text-inverse)',
            }}
            data-testid="chat-send-btn"
          >
            {isTyping ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
          </button>
        </div>
      </div>
    </aside>
  );
};
