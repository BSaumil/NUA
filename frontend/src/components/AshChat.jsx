import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Sparkles, Send, X, Minus, Brain } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const H = () => ({ Authorization: `Bearer ${localStorage.getItem('nuva_token')}` });

const SESSION_KEY_BASE = 'nua-ash-chat-session';
const userScope = () => {
  try {
    const u = JSON.parse(localStorage.getItem('nuva_user') || '{}');
    return u.email || 'anon';
  } catch { return 'anon'; }
};
const SESSION_KEY = () => `${SESSION_KEY_BASE}::${userScope()}`;
const MSGS_KEY = () => `${SESSION_KEY_BASE}::${userScope()}::msgs`;

const SUGGESTIONS = [
  'What happened yesterday?',
  'Who dismissed the burnout alert?',
  'What should I do next?',
  'Show me pending approvals',
  'Which product needs a price change?',
];

export default function AshChat() {
  const [open, setOpen] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const [msgs, setMsgs] = useState(() => JSON.parse(localStorage.getItem(MSGS_KEY()) || '[]'));
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState(() => localStorage.getItem(SESSION_KEY()) || '');
  const scrollRef = useRef(null);

  useEffect(() => {
    localStorage.setItem(MSGS_KEY(), JSON.stringify(msgs.slice(-40)));
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [msgs]);

  const send = async (text) => {
    const trimmed = (text || input).trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setMsgs(m => [...m, { role: 'user', text: trimmed, ts: Date.now() }]);
    setInput('');
    try {
      const r = await axios.post(`${API}/ash/agent`, { message: trimmed, sessionId }, { headers: H() });
      if (!sessionId) {
        setSessionId(r.data.sessionId);
        localStorage.setItem(SESSION_KEY(), r.data.sessionId);
      }
      setMsgs(m => [...m, {
        role: 'ash',
        text: r.data.reply,
        reasoning: r.data.reasoning,
        toolResults: r.data.toolResults,
        ts: Date.now(),
      }]);
    } catch (e) {
      setMsgs(m => [...m, { role: 'ash', text: '⚠️ Ash is unreachable right now. Try again in a moment.', ts: Date.now() }]);
    } finally {
      setBusy(false);
    }
  };

  const clearSession = () => {
    setMsgs([]);
    setSessionId('');
    localStorage.removeItem(SESSION_KEY());
    localStorage.removeItem(MSGS_KEY());
  };

  // FAB when closed
  if (!open) {
    return (
      <button
        onClick={() => { setOpen(true); setMinimized(false); }}
        className="fixed bottom-5 right-5 z-50 h-14 w-14 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white shadow-xl flex items-center justify-center transition-all hover:scale-105"
        data-testid="ash-chat-fab"
        aria-label="Ask Ash"
      >
        <Brain size={26} />
        <span className="absolute -top-1 -right-1 h-3 w-3 bg-emerald-400 rounded-full ring-2 ring-white animate-pulse" />
      </button>
    );
  }

  return (
    <div
      className={`fixed bottom-5 right-5 z-50 bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col transition-all ${
        minimized ? 'w-72 h-14' : 'w-96 h-[540px]'
      }`}
      data-testid="ash-chat-panel"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-t-2xl">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 bg-white/20 backdrop-blur rounded-full flex items-center justify-center">
            <Brain size={16} />
          </div>
          <div>
            <p className="font-semibold text-sm">Ash</p>
            {!minimized && <p className="text-[10px] opacity-80">Autonomous operating layer</p>}
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={() => setMinimized(m => !m)} className="p-1 hover:bg-white/20 rounded" data-testid="ash-chat-minimize">
            <Minus size={14} />
          </button>
          <button onClick={() => setOpen(false)} className="p-1 hover:bg-white/20 rounded" data-testid="ash-chat-close">
            <X size={14} />
          </button>
        </div>
      </div>

      {minimized ? null : (
        <>
          {/* Messages */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3 bg-slate-50" data-testid="ash-chat-messages">
            {msgs.length === 0 && (
              <div className="text-center py-6">
                <Sparkles className="mx-auto mb-2 text-indigo-400" size={28} />
                <p className="text-sm text-slate-600 mb-1">Hi &mdash; I&apos;m Ash.</p>
                <p className="text-xs text-slate-500 mb-4">Ask me about the last 30 audit events, open insights, pending approvals, or what to do next.</p>
                <div className="space-y-2 text-left">
                  {SUGGESTIONS.map((s, i) => (
                    <button key={i} onClick={() => send(s)} className="w-full text-left text-xs px-3 py-2 rounded-lg bg-white border hover:border-indigo-300 hover:bg-indigo-50 transition"
                      data-testid={`ash-suggest-${i}`}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {msgs.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm ${
                  m.role === 'user' ? 'bg-indigo-600 text-white' : 'bg-white border shadow-sm'
                }`} data-testid={`msg-${m.role}-${i}`}>
                  <p className="whitespace-pre-wrap">{m.text}</p>
                  {(m.toolResults && m.toolResults.length > 0) && (
                    <div className="mt-2 pt-2 border-t border-slate-100 space-y-1">
                      {m.toolResults.map((t, ix) => (
                        <div key={ix} className="text-[10px] flex items-center gap-1">
                          <Badge className={
                            t.status === 'executed' ? 'bg-emerald-500' :
                            t.status === 'pending_approval' ? 'bg-amber-500' :
                            t.status === 'blocked' ? 'bg-rose-500' : 'bg-slate-500'
                          }>{t.status.replace('_', ' ')}</Badge>
                          <span className="font-mono text-slate-600">{t.tool}</span>
                          {t.approvalId && <span className="text-slate-400">→ approval {t.approvalId.slice(0, 6)}</span>}
                        </div>
                      ))}
                    </div>
                  )}
                  {m.reasoning && (
                    <details className="mt-2 pt-2 border-t border-slate-100 text-[10px] cursor-pointer text-slate-500">
                      <summary className="font-medium">Why · confidence {Math.round((m.reasoning.confidence || 0) * 100)}%</summary>
                      <div className="mt-1 space-y-1 whitespace-pre-wrap">
                        {m.reasoning.problem && <p><b>Problem:</b> {m.reasoning.problem}</p>}
                        {m.reasoning.evidence && <p><b>Evidence:</b> {m.reasoning.evidence}</p>}
                        {m.reasoning.alternatives && <p><b>Alternatives:</b> {Array.isArray(m.reasoning.alternatives) ? m.reasoning.alternatives.join(', ') : m.reasoning.alternatives}</p>}
                        {m.reasoning.risk && <p><b>Risk:</b> {m.reasoning.risk}</p>}
                        {m.reasoning.expectedImpact && <p><b>Impact:</b> {m.reasoning.expectedImpact}</p>}
                        {m.reasoning.rollback && <p><b>Rollback:</b> {m.reasoning.rollback}</p>}
                      </div>
                    </details>
                  )}
                </div>
              </div>
            ))}
            {busy && (
              <div className="flex justify-start">
                <div className="bg-white border rounded-2xl px-3 py-2 text-sm text-slate-500 flex items-center gap-2 shadow-sm">
                  <span className="animate-pulse">Ash is thinking…</span>
                </div>
              </div>
            )}
          </div>

          {/* Composer */}
          <div className="px-3 py-2 border-t flex items-center gap-2 bg-white rounded-b-2xl">
            <Input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
              placeholder="Ask Ash…"
              className="flex-1 text-sm"
              disabled={busy}
              data-testid="ash-chat-input"
            />
            <Button size="sm" onClick={() => send()} disabled={busy || !input.trim()} className="shrink-0" data-testid="ash-chat-send">
              <Send size={14} />
            </Button>
          </div>
          {msgs.length > 0 && (
            <button onClick={clearSession} className="text-[10px] text-slate-400 hover:text-rose-500 pb-1" data-testid="ash-chat-reset">
              Reset conversation
            </button>
          )}
        </>
      )}
    </div>
  );
}
