import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, ChevronLeft, ChevronRight } from 'lucide-react';
import { chatMessages as initialMessages, mockAIResponses } from '@/data/mockData';
import { cn } from "@/lib/utils";

const AI_AVATAR = "https://static.prod-images.emergentagent.com/jobs/2a0b1db4-ca8c-467b-bf34-af2a2ee9980c/images/56de863a09d108a633fc9a71a64378aa5937e1b191e54dee11b697c3f83fc92d.png";

export const ChatPanel = () => {
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

  const getAIResponse = (userMessage) => {
    const lowerMsg = userMessage.toLowerCase();
    if (lowerMsg.includes('nifty')) return mockAIResponses.nifty;
    if (lowerMsg.includes('reliance')) return mockAIResponses.reliance;
    if (lowerMsg.includes('bank')) return mockAIResponses.banking;
    if (lowerMsg.includes('it') || lowerMsg.includes('infosys') || lowerMsg.includes('tcs')) return mockAIResponses.it;
    if (lowerMsg.includes('macro') || lowerMsg.includes('gdp') || lowerMsg.includes('inflation')) return mockAIResponses.macro;
    if (lowerMsg.includes('irfc')) return mockAIResponses.irfc;
    return mockAIResponses.default;
  };

  const handleSend = () => {
    if (!input.trim()) return;

    const userMessage = { id: Date.now(), type: 'user', text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    // Simulate AI response delay
    setTimeout(() => {
      const aiResponse = { id: Date.now() + 1, type: 'ai', text: getAIResponse(input) };
      setMessages((prev) => [...prev, aiResponse]);
      setIsTyping(false);
    }, 1000);
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
        className="w-10 h-full bg-[#111827] border-l border-[#1f2937] flex items-center justify-center hover:bg-[#1f2937] transition-colors"
        data-testid="chat-panel-expand"
      >
        <ChevronLeft className="w-5 h-5 text-[#9ca3af]" />
      </button>
    );
  }

  return (
    <motion.aside
      className="w-80 h-full bg-[#111827] border-l border-[#1f2937] flex flex-col"
      initial={{ width: 0, opacity: 0 }}
      animate={{ width: 320, opacity: 1 }}
      transition={{ duration: 0.3 }}
      data-testid="chat-panel"
    >
      {/* Header */}
      <div className="h-12 px-4 flex items-center justify-between border-b border-[#1f2937]">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-[#f9fafb]">AI Insights</span>
          <span className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse" />
        </div>
        <button
          onClick={() => setIsCollapsed(true)}
          className="p-1 hover:bg-[#1f2937] rounded transition-colors"
          data-testid="chat-panel-collapse"
        >
          <ChevronRight className="w-4 h-4 text-[#9ca3af]" />
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
                    ? 'bg-[#3b82f6] text-white'
                    : 'bg-[#1f2937] text-[#f9fafb]'
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
            <div className="bg-[#1f2937] rounded-lg px-3 py-2">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-[#9ca3af] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-[#9ca3af] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-[#9ca3af] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </motion.div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-[#1f2937]">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask about markets, signals, or stocks"
            className="flex-1 bg-[#0a0e1a] border border-[#1f2937] rounded-lg px-3 py-2 text-sm text-[#f9fafb] placeholder:text-[#6b7280] focus:outline-none focus:ring-2 focus:ring-[#3b82f6]"
            data-testid="chat-input"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            className="p-2 bg-[#3b82f6] rounded-lg hover:bg-[#2563eb] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            data-testid="chat-send-btn"
          >
            <Send className="w-4 h-4 text-white" />
          </button>
        </div>
      </div>
    </motion.aside>
  );
};
