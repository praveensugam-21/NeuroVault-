import React, { useState, useRef, useEffect } from 'react';
import { Send, MessageSquare, BookOpen, AlertCircle, Loader2, Trash2, Copy, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import api from '../services/api';
import type { ChatMessage, ChatCitation } from '../types';

export const Chat: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [citations, setCitations] = useState<ChatCitation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load smart suggestions on mount
  useEffect(() => {
    const fetchSuggestions = async () => {
      try {
        const response = await api.get('/api/chat/suggestions');
        setSuggestions(response.data);
      } catch (err) {
        // Fallback to defaults
        setSuggestions([
          'Summarize my vault',
          'What is my PAN number?',
          'When does my driving licence expire?',
          'What key documents am I missing?'
        ]);
      }
    };
    fetchSuggestions();
  }, []);

  const handleSend = async (text: string) => {
    if (!text.trim() || loading) return;

    setError(null);
    const userMsg: ChatMessage = { role: 'user', content: text };
    const currentHistory = [...messages, userMsg];
    setMessages(currentHistory);
    setInputValue('');
    setLoading(true);

    try {
      // Send query with context history
      const response = await api.post('/api/chat/', {
        question: text,
        history: messages.slice(-10) // Send last 10 messages for context
      });

      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: response.data.answer
      };

      setMessages((prev) => [...prev, assistantMsg]);
      setCitations(response.data.citations || []);
      
      // Refresh suggestions occasionally
      const newSugg = await api.get('/api/chat/suggestions');
      setSuggestions(newSugg.data);
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

  const handleClear = () => {
    setMessages([]);
    setCitations([]);
    setError(null);
  };

  const handleCopy = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedId(index);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="flex h-full overflow-hidden bg-[#F8FAFC] dark:bg-slate-950">
      {/* Chat Stream Area */}
      <div className="flex-1 flex flex-col h-full bg-white dark:bg-slate-900">
        
        {/* Page Header */}
        <header className="h-14 border-b border-[#E5E7EB] dark:border-slate-800 px-8 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2 text-xs text-[#6B7280]">
            <span>Assistant</span>
            <span>/</span>
            <span className="text-[#111827] dark:text-slate-200 font-medium">Memory Assistant</span>
          </div>

          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-400 dark:border-emerald-800/40">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              Local & Private
            </span>
            {messages.length > 0 && (
              <button 
                onClick={handleClear}
                className="flex items-center gap-1.5 px-2.5 py-1 text-xs text-rose-600 hover:bg-rose-50 dark:text-rose-400 dark:hover:bg-rose-950/20 border border-rose-200 dark:border-rose-800/40 rounded transition"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Clear Chat
              </button>
            )}
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
                {suggestions.map((q) => (
                  <button
                    key={q}
                    onClick={() => handleSend(q)}
                    className="text-left p-3.5 bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 hover:border-[#2563EB]/40 text-xs text-[#111827] dark:text-slate-350 hover:text-[#2563EB] rounded transition-all shadow-[0_1px_2px_rgba(0,0,0,0.01)]"
                  >
                    <p className="font-semibold truncate">{q}</p>
                    <p className="text-[10px] text-[#6B7280] mt-0.5">Click to ask instantly</p>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((msg, index) => {
                const isUser = msg.role === 'user';
                return (
                  <div
                    key={index}
                    className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`relative group max-w-2xl p-4 border rounded text-xs leading-relaxed ${
                        isUser
                          ? 'bg-[#EFF6FF] border-[#BFDBFE] text-[#1E40AF] font-medium'
                          : 'bg-[#F9FAFB] dark:bg-slate-950 border-[#E5E7EB] dark:border-slate-850 text-[#111827] dark:text-slate-200 shadow-[0_1px_2px_rgba(0,0,0,0.015)]'
                      }`}
                    >
                      {/* Copy Action Button */}
                      {!isUser && (
                        <button
                          onClick={() => handleCopy(msg.content, index)}
                          className="absolute right-2 top-2 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 opacity-0 group-hover:opacity-100 transition duration-150"
                          title="Copy to clipboard"
                        >
                          {copiedId === index ? (
                            <Check className="w-3.5 h-3.5 text-emerald-500" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      )}

                      {isUser ? (
                        <p style={{ whiteSpace: 'pre-line' }}>{msg.content}</p>
                      ) : (
                        <div className="prose prose-xs max-w-none dark:prose-invert">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {msg.content}
                          </ReactMarkdown>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {loading && (
            <div className="flex justify-start animate-pulse">
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
              className="nv-input flex-1 px-4 py-2 border border-[#E5E7EB] dark:border-slate-800 rounded bg-white dark:bg-slate-900 text-xs focus:outline-none focus:ring-1 focus:ring-[#2563EB]"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || loading}
              className="nv-btn-primary h-10 px-5 font-semibold flex items-center gap-2"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Ask</span>
            </button>
          </form>
        </div>
      </div>

      {/* RAG Citations Panel */}
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
                className="p-4 border border-[#E5E7EB] dark:border-slate-800 rounded bg-white dark:bg-slate-900 space-y-2 shadow-[0_1px_2px_rgba(0,0,0,0.02)] transition hover:shadow-md"
              >
                <div className="flex justify-between items-start gap-2">
                  <h4 className="text-xs font-semibold text-[#111827] dark:text-slate-200 truncate max-w-[70%]">{c.document_name}</h4>
                  {c.similarity && (
                    <span className="text-[10px] font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/20 px-1.5 py-0.5 rounded">
                      {Math.round(c.similarity * 100)}% Match
                    </span>
                  )}
                </div>
                <div className="flex flex-wrap gap-1.5 mt-1.5">
                  <span className="text-[9px] bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded text-slate-600 dark:text-slate-350 font-medium">
                    {c.category}
                  </span>
                  {c.section && (
                    <span className="text-[9px] font-semibold bg-blue-50 text-blue-700 dark:bg-blue-950/30 dark:text-blue-400 border border-blue-100 dark:border-blue-900/30 px-2 py-0.5 rounded">
                      Section: {c.section}
                    </span>
                  )}
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
