import React, { useState, useRef, useEffect } from 'react';
import { Send, MessageSquare, BookOpen, AlertCircle } from 'lucide-react';
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
    'What is my PAN number?',
    'When does my driving licence expire?',
    'What were my Class 12 marks?',
    'Which company gave me my first job?',
    'Summarize my entire academic history',
    'What documents do I need to renew?',
    'Show me everything related to my car'
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
      // API request using chat schema
      const response = await api.post('/api/chat/', {
        question: text,
        history: messages.slice(-10) // Send trailing conversation window
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
    <div className="flex h-full overflow-hidden">
      {/* Chat Conversation Panel */}
      <div className="flex-1 flex flex-col h-full bg-background/30 p-8 justify-between">
        <div className="space-y-2 shrink-0">
          <h1 className="text-2xl font-bold tracking-tight">AI Memory Assistant</h1>
          <p className="text-muted-foreground text-sm">
            Ask natural language questions to query details across your entire document vault.
          </p>
        </div>

        {/* Scroll Box */}
        <div className="flex-1 overflow-y-auto py-6 space-y-4 pr-2">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto space-y-6">
              <MessageSquare className="w-10 h-10 text-muted-foreground/30" />
              <div className="space-y-1">
                <p className="text-xs font-semibold">Start a conversation</p>
                <p className="text-[11px] text-muted-foreground">
                  Query items, search entities, analyze academic performance or extract financial details instantly.
                </p>
              </div>

              {/* Suggestion Chips */}
              <div className="flex flex-wrap gap-2 justify-center">
                {quickQueries.map((q) => (
                  <button
                    key={q}
                    onClick={() => handleSend(q)}
                    className="text-[10px] bg-card border border-border px-3 py-1.5 rounded-full hover:border-primary/50 text-muted-foreground hover:text-foreground transition-all"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, index) => {
              const isUser = msg.role === 'user';
              return (
                <div
                  key={index}
                  className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-xl p-4 rounded-lg text-xs leading-relaxed ${
                      isUser
                        ? 'bg-primary text-primary-foreground font-medium rounded-tr-none'
                        : 'bg-card border border-border text-foreground rounded-tl-none shadow-sm'
                    }`}
                    style={{ whiteSpace: 'pre-line' }}
                  >
                    {msg.content}
                  </div>
                </div>
              );
            })
          )}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-card border border-border text-muted-foreground text-[10px] p-3 rounded-lg rounded-tl-none animate-pulse">
                Thinking and citations lookup...
              </div>
            </div>
          )}
          {error && (
            <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900 text-red-800 dark:text-red-400 p-3 rounded-lg text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input box */}
        <form onSubmit={handleSubmit} className="flex gap-3 shrink-0 pt-4 border-t border-border mt-4">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Ask anything about your documents..."
            className="flex-1 bg-card border border-border rounded px-4 py-2.5 text-xs focus:outline-none focus:border-primary transition-colors"
          />
          <button
            type="submit"
            disabled={!inputValue.trim() || loading}
            className="bg-primary text-primary-foreground hover:bg-primary/95 px-4 py-2.5 rounded text-xs font-semibold flex items-center gap-2 disabled:opacity-50 disabled:hover:bg-primary transition-colors"
          >
            <Send className="w-3.5 h-3.5" />
            Send
          </button>
        </form>
      </div>

      {/* RAG citations sidebar panel */}
      {citations.length > 0 && (
        <div className="w-80 border-l border-border bg-card p-6 space-y-6 h-full overflow-y-auto shadow-lg shrink-0">
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-primary" />
            <h2 className="text-sm font-bold uppercase tracking-wider">Source References</h2>
          </div>

          <div className="space-y-4">
            {citations.map((c, i) => (
              <div 
                key={i} 
                className="p-3.5 border border-border rounded-lg bg-background/50 space-y-2 hover:border-primary/30 transition-all"
              >
                <div>
                  <h4 className="text-xs font-bold text-foreground truncate">{c.document_name}</h4>
                  <p className="text-[10px] text-muted-foreground uppercase">{c.category}</p>
                </div>
                <p className="text-[10px] text-muted-foreground leading-relaxed bg-secondary/35 p-2 rounded border border-border/55">
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
