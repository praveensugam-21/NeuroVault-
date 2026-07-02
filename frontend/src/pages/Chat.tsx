import React, { useState, useRef, useEffect } from 'react';
import { Send, MessageSquare, BookOpen, AlertCircle, Loader2 } from 'lucide-react';
import api from '../services/api';
import type { ChatMessage, ChatCitation } from '../types';

export const Chat: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [citations, setCitations] = useState<ChatCitation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const quickQueries = [
    { title: 'PAN Number', query: 'What is my PAN number?' },
    { title: 'Driving License', query: 'When does my driving licence expire?' },
    { title: 'Academic Summary', query: 'Summarize my academic history' },
    { title: 'Required Renewals', query: 'What documents do I need to renew?' }
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (text: string) => {
    if (!text.trim() || loading) return;

    setError(null);
    const userMsg: ChatMessage = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInputValue('');
    setLoading(true);

    try {
      const response = await api.post('/api/chat/', {
        question: text,
        history: messages.slice(-10)
      });

      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: response.data.answer
      };

      setMessages((prev) => [...prev, assistantMsg]);
      setCitations(response.data.citations || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to communicate with RAG Query Engine.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSend(inputValue);
  };

  return (
    <div className="flex h-full overflow-hidden bg-[#F8FAFC] dark:bg-slate-950">
      {/* Chat Stream Area (Single Column Centered Layout) */}
      <div className="flex-1 flex flex-col h-full bg-white dark:bg-slate-900">
        
        {/* Page Header */}
        <header className="h-14 border-b border-[#E5E7EB] dark:border-slate-800 px-8 flex items-center shrink-0">
          <div className="flex items-center gap-2 text-xs text-[#6B7280]">
            <span>Assistant</span>
            <span>/</span>
            <span className="text-[#111827] dark:text-slate-200 font-medium">Memory Assistant</span>
          </div>
        </header>

        {/* Chat Thread Scroll Region */}
        <div className="flex-1 overflow-y-auto p-8 space-y-6 max-w-4xl w-full mx-auto">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-lg mx-auto space-y-8 py-12">
              <div className="p-3 bg-[#F3F4F6] dark:bg-slate-850 rounded border border-[#E5E7EB] dark:border-slate-800">
                <MessageSquare className="w-6 h-6 text-[#2563EB]" />
              </div>
              <div className="space-y-2">
                <h2 className="text-sm font-semibold text-[#111827] dark:text-slate-100">Ask your memory index</h2>
                <p className="text-xs text-[#6B7280] leading-relaxed max-w-sm">
                  Query key credential values, document expiry dates, academic performance, or employment records instantly using semantic search.
                </p>
              </div>

              {/* Action Preset Cards directly inside Empty State */}
              <div className="grid grid-cols-2 gap-3 w-full pt-4">
                {quickQueries.map((q) => (
                  <button
                    key={q.title}
                    onClick={() => handleSend(q.query)}
                    className="text-left p-3.5 bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 hover:border-[#2563EB]/40 text-xs text-[#111827] dark:text-slate-350 hover:text-[#2563EB] rounded transition-all shadow-[0_1px_2px_rgba(0,0,0,0.01)]"
                  >
                    <p className="font-semibold">{q.title}</p>
                    <p className="text-[10px] text-[#6B7280] truncate mt-0.5">{q.query}</p>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((msg, index) => {
                const isUser = msg.role === 'user';
                return (
                  <div
                    key={index}
                    className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-2xl p-4 border rounded text-xs leading-relaxed ${
                        isUser
                          ? 'bg-[#EFF6FF] border-[#BFDBFE] text-[#1E40AF] font-medium'
                          : 'bg-[#F9FAFB] dark:bg-slate-950 border-[#E5E7EB] dark:border-slate-850 text-[#111827] dark:text-slate-205 shadow-[0_1px_2px_rgba(0,0,0,0.015)]'
                      }`}
                      style={{ whiteSpace: 'pre-line' }}
                    >
                      {msg.content}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {loading && (
            <div className="flex justify-start">
              <div className="bg-[#F8FAFC] dark:bg-slate-950 border border-[#E5E7EB] dark:border-slate-800 text-[#6B7280] text-[10px] p-3.5 rounded flex items-center gap-2">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-[#2563EB]" />
                <span>Searching vector database and generating grounded response...</span>
              </div>
            </div>
          )}

          {error && (
            <div className="bg-[#DC2626]/5 border border-[#DC2626]/20 text-[#DC2626] p-3 rounded text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Dock */}
        <div className="border-t border-[#E5E7EB] dark:border-slate-800 bg-white dark:bg-slate-900 shrink-0 py-6 px-8">
          <form onSubmit={handleSubmit} className="flex gap-3 max-w-4xl mx-auto w-full">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Ask anything about your stored documents..."
              className="nv-input"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || loading}
              className="nv-btn-primary h-10 px-5 font-semibold"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Ask</span>
            </button>
          </form>
        </div>
      </div>

      {/* RAG Citations Panel (Only shows when references exist) */}
      {citations.length > 0 && (
        <div className="w-80 bg-[#F8FAFC] dark:bg-slate-950 p-6 space-y-6 h-full overflow-y-auto shrink-0 border-l border-[#E5E7EB] dark:border-slate-800">
          <div className="flex items-center gap-2 pb-3 border-b border-[#E5E7EB] dark:border-slate-800">
            <BookOpen className="w-4 h-4 text-[#2563EB]" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-[#111827] dark:text-slate-200">
              Source Citations
            </h2>
          </div>

          <div className="space-y-4">
            {citations.map((c, i) => (
              <div 
                key={i} 
                className="p-4 border border-[#E5E7EB] dark:border-slate-800 rounded bg-white dark:bg-slate-900 space-y-2 shadow-[0_1px_2px_rgba(0,0,0,0.02)]"
              >
                <div>
                  <h4 className="text-xs font-semibold text-[#111827] dark:text-slate-200 truncate">{c.document_name}</h4>
                  <span className="nv-badge nv-badge-neutral text-[9px] mt-1">
                    {c.category}
                  </span>
                </div>
                <p className="text-[10px] text-[#6B7280] dark:text-slate-400 leading-relaxed bg-[#F8FAFC] dark:bg-slate-950 border border-[#E5E7EB] dark:border-slate-800 p-2.5 rounded font-mono break-words">
                  "{c.snippet}"
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
