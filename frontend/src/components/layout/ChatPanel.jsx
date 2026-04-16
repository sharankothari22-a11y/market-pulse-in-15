import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import { apiPost, API_ENDPOINTS } from '@/services/api';
import { cn } from '@/lib/utils';

const AI_AVATAR = 'https://static.prod-images.emergentagent.com/jobs/2a0b1db4-ca8c-467b-bf34-af2a2ee9980c/images/56de863a09d108a633fc9a71a64378aa5937e1b191e54dee11b697c3f83fc92d.png';

const initialMessages = [
  { id: 1, type: 'ai', text: 'Welcome to Beaver Intelligence. I can help you analyze Indian market trends, stock signals, and macro indicators. What would you like to know?' },
];

export const ChatPanel = ({ sessionId }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); };
  useEffect(() => { scrollToBottom(); }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isTyping) return;
    const userMessage = { id: Date.now(), type: 'user', text: input };
    setMessages((prev) => [...prev, userMessage]);
    const userInput = input;
    setInput('');
    setIsTyping(true);
    try {
      const requestBody = { message: userInput };
      if (sessionId) requestBody.session_id = sessionId;
      const response = await apiPost(API_ENDPOINTS.chat, requestBody);
      let responseText = response.response || response.message || response.answer;
      if (!responseText) responseText = 'I received your message but could not generate a response.';
      setMessages((prev) => [...prev, { id: Date.now() + 1, type: 'ai', text: responseText }]);
    } catch (error) {
      console.error('Chat API error:', error);
      setMessages((prev) => [...prev, { id: Date.now() + 1, type: 'ai', text: 'Sorry, I encountered an error processing your request. Please try again.' }]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  if (isCollapsed) {
    return (
      <button
        onClick={() => setIsCollapsed(false)}
        className="w-10 h-full flex items-center justify-center transition-colors"
        style={{
          backgroundColor: '#0A1628',
          borderLeft: '1px solid rgba(201, 168, 76, 0.2)',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#1E3A5F'; }}
        onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#0A1628'; }}
        data-testid="chat-panel-expand"
      >
        <ChevronLeft className="w-5 h-5" style={{ color: '#C9A84C' }} />
      </button>
    );
  }

  return (
    <motion.aside
      className="w-80 h-full flex flex-col"
      initial={{ width: 0, opacity: 0 }}
      animate={{ width: 320, opacity: 1 }}
      transition={{ duration: 0.3 }}
      style={{
        backgroundColor: '#FFFFFF',
        borderLeft: '1px solid rgba(201, 168, 76, 0.25)',
        boxShadow: '-2px 0 8px rgba(10, 22, 40, 0.05)',
      }}
      data-testid="chat-panel"
    >
      {/* Header */}
      <div
        className="h-12 px-4 flex items-center justify-between"
        style={{
          backgroundColor: '#0A1628',
          borderBottom: '1px solid rgba(201, 168, 76, 0.25)',
        }}
      >
        <div className="flex items-center gap-2">
          <span
            className="font-serif-display"
            style={{ color: '#C9A84C', fontSize: 12, letterSpacing: '0.22em', fontWeight: 700 }}
          >
            AI INSIGHTS
          </span>
          <span
            className="gold-pulse-dot"
            style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: '#C9A84C' }}
          />
        </div>
        <button
          onClick={() => setIsCollapsed(true)}
          className="p-1 rounded transition-colors"
          style={{ color: 'rgba(201, 168, 76, 0.85)' }}
          data-testid="chat-panel-collapse"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Messages */}
      <div
        className="flex-1 overflow-y-auto p-4 space-y-3"
        style={{ backgroundColor: '#FAF6EE' }}
        data-testid="chat-messages"
      >
        <AnimatePresence>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className={cn('flex gap-2', msg.type === 'user' ? 'justify-end' : 'justify-start')}
            >
              {msg.type === 'ai' && (
                <img src={AI_AVATAR} alt="AI" className="w-6 h-6 rounded-full flex-shrink-0 mt-1" />
              )}
              <div
                className="max-w-[85%] px-3 py-2 text-[13px] leading-relaxed"
                style={msg.type === 'user' ? {
                  backgroundColor: '#0A1628',
                  color: '#F5F0E8',
                  borderRadius: '4px',
                } : {
                  backgroundColor: '#FFFFFF',
                  border: '1px solid rgba(201, 168, 76, 0.22)',
                  color: '#0A1628',
                  borderRadius: '4px',
                  boxShadow: '0 1px 3px rgba(10, 22, 40, 0.06)',
                }}
              >
                <p className="whitespace-pre-wrap">{msg.text}</p>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {isTyping && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-2 items-center">
            <img src={AI_AVATAR} alt="AI" className="w-6 h-6 rounded-full" />
            <div style={{
              backgroundColor: '#FFFFFF',
              border: '1px solid rgba(201, 168, 76, 0.22)',
              borderRadius: 4,
              padding: '6px 10px',
            }}>
              <div className="flex gap-1">
                <span className="animate-bounce" style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: '#C9A84C', animationDelay: '0ms' }} />
                <span className="animate-bounce" style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: '#C9A84C', animationDelay: '150ms' }} />
                <span className="animate-bounce" style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: '#C9A84C', animationDelay: '300ms' }} />
              </div>
            </div>
          </motion.div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div
        className="p-3"
        style={{
          backgroundColor: '#FFFFFF',
          borderTop: '1px solid rgba(201, 168, 76, 0.22)',
        }}
      >
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask about markets, signals, or stocks"
            style={{
              flex: 1,
              backgroundColor: '#FAF6EE',
              border: '1px solid rgba(201, 168, 76, 0.3)',
              borderRadius: 3,
              padding: '8px 12px',
              fontSize: 12.5,
              color: '#0A1628',
            }}
            data-testid="chat-input"
            disabled={isTyping}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            className="p-2 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            style={{
              backgroundColor: '#0A1628',
              borderRadius: 3,
              color: '#C9A84C',
            }}
            data-testid="chat-send-btn"
          >
            {isTyping ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </motion.aside>
  );
};
