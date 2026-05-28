import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, X, MessageSquare } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { useTheme } from '../contexts/ThemeContext';
import { v15API } from '../services/api';

const SUGGESTIONS = [
  "What were today's top 3 best-sellers?",
  "How much revenue did we make today?",
  "How many bookings do we have today?",
  "Which category drove the most sales?",
];

export default function AskNuaPanel({ open, onClose }) {
  const { theme } = useTheme();
  const [messages, setMessages] = useState([{ role: 'nua', text: "Hi! I'm NUA. Ask me anything about today's business." }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef();

  useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [messages]);

  const send = async (q) => {
    const question = (q || input).trim();
    if (!question) return;
    setMessages(m => [...m, { role: 'user', text: question }]);
    setInput('');
    setLoading(true);
    try {
      const r = await v15API.askNua(question);
      setMessages(m => [...m, { role: 'nua', text: r.data?.answer || 'No answer.' }]);
    } catch {
      setMessages(m => [...m, { role: 'nua', text: 'AI assistant unavailable right now.' }]);
    }
    setLoading(false);
  };

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[60] bg-black/40 backdrop-blur-sm flex items-end sm:items-center justify-center" onClick={onClose} data-testid="ask-nua-panel">
      <div className="bg-white w-full sm:w-[480px] h-[80vh] sm:h-[600px] rounded-t-3xl sm:rounded-2xl shadow-2xl flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="border-b px-5 py-3 flex items-center justify-between" style={{ borderColor: '#f3f4f6' }}>
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-full flex items-center justify-center" style={{ backgroundColor: `${theme.primary}15`, color: theme.primary }}><Sparkles size={18} /></div>
            <div><h2 className="font-bold text-sm">Ask NUA</h2><p className="text-[10px] text-gray-400">Natural-language analytics</p></div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg" data-testid="ask-nua-close"><X size={18} /></button>
        </div>
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-5 space-y-3" data-testid="ask-nua-messages">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] px-3 py-2 rounded-2xl text-sm ${m.role === 'user' ? 'text-white' : 'bg-gray-100 text-gray-800'}`} style={m.role === 'user' ? { backgroundColor: theme.primary } : {}}>
                {m.text}
              </div>
            </div>
          ))}
          {loading && <div className="flex justify-start"><div className="bg-gray-100 px-3 py-2 rounded-2xl text-sm animate-pulse">NUA is thinking...</div></div>}
        </div>
        {messages.length === 1 && (
          <div className="px-5 pb-2 flex flex-wrap gap-1.5">
            {SUGGESTIONS.map(s => (
              <button key={s} onClick={() => send(s)} className="text-[11px] px-2.5 py-1 rounded-full border bg-gray-50 hover:bg-gray-100 transition-colors" data-testid="ask-nua-suggest">{s}</button>
            ))}
          </div>
        )}
        <div className="border-t p-3 flex gap-2">
          <Input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()} placeholder="Ask anything..." disabled={loading} data-testid="ask-nua-input" />
          <Button onClick={() => send()} disabled={loading || !input.trim()} style={{ backgroundColor: theme.primary }} data-testid="ask-nua-send"><Send size={16} /></Button>
        </div>
      </div>
    </div>
  );
}

export function AskNuaButton({ onClick }) {
  const { theme } = useTheme();
  return (
    <button onClick={onClick} className="fixed bottom-20 right-4 z-30 w-14 h-14 rounded-full shadow-lg flex items-center justify-center hover:scale-110 transition-transform" style={{ backgroundColor: theme.primary, color: 'white' }} data-testid="ask-nua-fab">
      <Sparkles size={22} />
    </button>
  );
}
