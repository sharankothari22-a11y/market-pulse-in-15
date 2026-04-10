import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import { apiPost, apiGet, API_ENDPOINTS } from '@/services/api';
import { cn } from "@/lib/utils";

const AI_AVATAR = "https://static.prod-images.emergentagent.com/jobs/2a0b1db4-ca8c-467b-bf34-af2a2ee9980c/images/56de863a09d108a633fc9a71a64378aa5937e1b191e54dee11b697c3f83fc92d.png";

const initialMessages = [
  { id: 1, type: 'ai', text: 'Hello! I can help you analyze Indian market trends, stock signals, and macro indicators. What would you like to know?' },
];

export const ChatPanel = ({ sessionId }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isTyping) return;

    const userMessage = { id: Date.now(), type: 'user', text: input };
    setMessages((prev) => [...prev, userMessage]);
    const userInput = input;
    setInput('');
    setIsTyping(true);

    try {
      let responseText;

      // Build request body - include session_id if available
      const requestBody = { message: userInput };
      if (sessionId) {
        requestBody.session_id = sessionId;
      }

      // Call the chat API
      const response = await apiPost(API_ENDPOINTS.chat, requestBody);
      responseText = response.response || response.message || response.answer;

      // If no response, try to provide a fallback
      if (!responseText) {
        responseText = 'I received your message but could not generate a response.';
      }
      
      const aiResponse = { 
        id: Date.now() + 1, 
        type: 'ai', 
        text: responseText
      };
      setMessages((prev) => [...prev, aiResponse]);
    } catch (error) {
      console.error('Chat API error:', error);
      const errorResponse = { 
        id: Date.now() + 1, 
        type: 'ai', 
        text: 'Sorry, I encountered an error processing your request. Please try again.' 
      };
      setMessages((prev) => [...prev, errorResponse]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (isCollapsed) {
    return (
      <button
        onClick={() => setIsCollapsed(false)}
        className="w-10 h-full bg-[#f8fafc] border-l border-[#e5e7eb] flex items-center justify-center hover:bg-[#f1f5f9] transition-colors"
        data-testid="chat-panel-expand"
      >
        <ChevronLeft className="w-5 h-5 text-[#64748b]" />
      </button>
    );
  }

  return (
    <motion.aside
      className="w-80 h-full bg-[#f8fafc] border-l border-[#e5e7eb] flex flex-col"
      initial={{ width: 0, opacity: 0 }}
      animate={{ width: 320, opacity: 1 }}
      transition={{ duration: 0.3 }}
      data-testid="chat-panel"
    >
      {/* Header */}
      <div className="h-12 px-4 flex items-center justify-between border-b border-[#e5e7eb] bg-[#ffffff]">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-[#0f172a]">AI Insights</span>
          <span className="w-2 h-2 rounded-full bg-[#16a34a] animate-pulse" />
        </div>
        <button
          onClick={() => setIsCollapsed(true)}
          className="p-1 hover:bg-[#f1f5f9] rounded transition-colors"
          data-testid="chat-panel-collapse"
        >
          <ChevronRight className="w-4 h-4 text-[#64748b]" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4" data-testid="chat-messages">
        <AnimatePresence>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className={cn(
                "flex gap-2",
                msg.type === 'user' ? 'justify-end' : 'justify-start'
              )}
            >
              {msg.type === 'ai' && (
                <img 
                  src={AI_AVATAR} 
                  alt="AI" 
                  className="w-6 h-6 rounded-full flex-shrink-0 mt-1"
                />
              )}
              <div
                className={cn(
                  "max-w-[85%] rounded-lg px-3 py-2 text-sm",
                  msg.type === 'user'
                    ? 'bg-[#2563eb] text-white'
                    : 'bg-[#f1f5f9] text-[#0f172a] border border-[#e5e7eb]'
                )}
              >
                <p className="whitespace-pre-wrap">{msg.text}</p>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        
        {isTyping && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex gap-2 items-center"
          >
            <img src={AI_AVATAR} alt="AI" className="w-6 h-6 rounded-full" />
            <div className="bg-[#f1f5f9] border border-[#e5e7eb] rounded-lg px-3 py-2">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-[#64748b] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-[#64748b] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-[#64748b] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </motion.div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-[#e5e7eb] bg-[#ffffff]">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask about markets, signals, or stocks"
            className="flex-1 bg-[#f8fafc] border border-[#e5e7eb] rounded-lg px-3 py-2 text-sm text-[#0f172a] placeholder:text-[#94a3b8] focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
            data-testid="chat-input"
            disabled={isTyping}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            className="p-2 bg-[#2563eb] rounded-lg hover:bg-[#1d4ed8] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            data-testid="chat-send-btn"
          >
            {isTyping ? (
              <Loader2 className="w-4 h-4 text-white animate-spin" />
            ) : (
              <Send className="w-4 h-4 text-white" />
            )}
          </button>
        </div>
      </div>
    </motion.aside>
  );
};
