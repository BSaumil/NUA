import React, { useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, Sparkles, RefreshCcw, Wand2, Trash2, Send, Calendar } from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent } from '../ui/card';
import { toast } from 'sonner';
import { socialAPI } from '../../services/api';

/**
 * Month-grid content calendar for /social-media.
 *
 * Each day cell shows scheduled & published posts as colour-coded chips
 * (one colour per platform). Drag a chip onto another day → reschedules
 * the post via PATCH /api/social/posts/{id}. The "AI Weekly Plan" button
 * generates a 7-day cross-platform schedule from top-selling products +
 * active promos (POST /api/social/ai-weekly-plan).
 *
 * Pure presentational where it can be — the parent SocialMedia.jsx owns
 * the posts array, account list and reload() callback.
 */
const PLATFORM_COLORS = {
  instagram: '#E1306C',
  facebook:  '#1877F2',
  tiktok:    '#69C9D0',
  x:         '#000000',
  google_business: '#34A853',
};

const sameDay = (a, b) =>
  a.getFullYear() === b.getFullYear()
  && a.getMonth() === b.getMonth()
  && a.getDate() === b.getDate();

const startOfMonthGrid = (anchor) => {
  // First Monday-or-earlier sunday before the 1st of the month.
  const first = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
  const weekday = first.getDay();           // 0..6, Sunday=0
  const offset = (weekday + 6) % 7;          // Monday-first grid → Mon=0
  return new Date(first.getFullYear(), first.getMonth(), 1 - offset);
};

export const SocialCalendar = ({ theme, posts, accounts, onReload }) => {
  const [anchor, setAnchor] = useState(new Date());
  const [planning, setPlanning] = useState(false);
  const [dragId, setDragId] = useState(null);
  const [hoverDay, setHoverDay] = useState(null);

  // Build a 6-week grid (42 cells) starting at the first Monday on/before
  // the 1st of the anchored month. This keeps the layout stable across
  // 28/29/30/31-day months.
  const gridDays = useMemo(() => {
    const start = startOfMonthGrid(anchor);
    return Array.from({ length: 42 }, (_, i) => {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      return d;
    });
  }, [anchor]);

  const postsByDay = useMemo(() => {
    const map = new Map();
    (posts || []).forEach((p) => {
      const ts = p.scheduledFor || p.publishedAt || p.createdAt;
      if (!ts) return;
      const d = new Date(ts);
      if (isNaN(d)) return;
      const key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(p);
    });
    return map;
  }, [posts]);

  const monthLabel = anchor.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
  const today = new Date();

  // -------- Drag-to-reschedule --------
  const handleDragStart = (e, post) => {
    if (post.status === 'published') return;   // can't reschedule history
    setDragId(post.id);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', post.id);
  };
  const handleDragOver = (e, day) => {
    e.preventDefault();
    setHoverDay(day.toDateString());
  };
  const handleDrop = async (e, day) => {
    e.preventDefault();
    setHoverDay(null);
    const id = e.dataTransfer.getData('text/plain') || dragId;
    if (!id) return;
    const post = (posts || []).find((p) => p.id === id);
    if (!post) return;
    const old = post.scheduledFor ? new Date(post.scheduledFor) : new Date();
    const next = new Date(day);
    next.setHours(old.getHours() || 12, old.getMinutes() || 0, 0, 0);
    try {
      await socialAPI.updatePost(id, {
        scheduledFor: next.toISOString(),
        status: post.status === 'draft' ? 'scheduled' : post.status,
      });
      toast.success(`Rescheduled to ${next.toLocaleDateString()}`);
      onReload && onReload();
    } catch {
      toast.error('Reschedule failed');
    } finally {
      setDragId(null);
    }
  };

  const handleWeeklyPlan = async () => {
    if (!accounts || accounts.length === 0) {
      return toast.error('Connect at least one social account first');
    }
    if (!window.confirm('Generate a 7-day plan? Existing auto-plan posts in the window will be replaced.')) return;
    setPlanning(true);
    try {
      const r = await socialAPI.aiWeeklyPlan({ daysAhead: 7, save: true, tone: 'warm', postTime: '12:00' });
      toast.success(`Saved ${r.data?.saved} posts across ${r.data?.platformsUsed?.length || 0} platforms`);
      onReload && onReload();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'AI plan failed');
    } finally { setPlanning(false); }
  };

  const handlePublish = async (id) => {
    try { await socialAPI.publishPost(id); toast.success('Published'); onReload && onReload(); }
    catch { toast.error('Publish failed'); }
  };
  const handleDelete = async (id) => {
    if (!window.confirm('Delete this post?')) return;
    try { await socialAPI.deletePost(id); toast.success('Deleted'); onReload && onReload(); }
    catch { toast.error('Failed'); }
  };

  // KPIs
  const counts = useMemo(() => {
    const c = { scheduled: 0, published: 0, draft: 0 };
    (posts || []).forEach((p) => {
      if (p.status === 'scheduled') c.scheduled++;
      else if (p.status === 'published') c.published++;
      else if (p.status === 'draft') c.draft++;
    });
    return c;
  }, [posts]);

  return (
    <Card data-testid="social-calendar">
      <CardContent className="p-4 space-y-3">
        {/* Header row */}
        <div className="flex flex-wrap items-center gap-2">
          <Calendar size={18} style={{ color: theme.primary }} />
          <h2 className="text-lg font-bold" style={{ color: theme.text }}>Content Calendar</h2>
          <div className="ml-auto flex items-center gap-1.5">
            <Button size="sm" variant="outline" onClick={() => setAnchor(new Date(anchor.getFullYear(), anchor.getMonth() - 1, 1))} data-testid="cal-prev">
              <ChevronLeft size={14} />
            </Button>
            <span className="text-sm font-semibold min-w-[150px] text-center" data-testid="cal-month-label">{monthLabel}</span>
            <Button size="sm" variant="outline" onClick={() => setAnchor(new Date(anchor.getFullYear(), anchor.getMonth() + 1, 1))} data-testid="cal-next">
              <ChevronRight size={14} />
            </Button>
            <Button size="sm" variant="outline" onClick={() => setAnchor(new Date())} data-testid="cal-today">Today</Button>
            <Button
              size="sm"
              className="text-white hover:opacity-90"
              style={{ background: theme.primary }}
              onClick={handleWeeklyPlan}
              disabled={planning}
              data-testid="ai-weekly-plan-btn"
            >
              {planning ? <><RefreshCcw size={12} className="mr-1.5 animate-spin" /> Planning…</>
                        : <><Wand2 size={12} className="mr-1.5" /> AI Weekly Plan</>}
            </Button>
          </div>
        </div>

        {/* KPI strip */}
        <div className="flex items-center gap-3 text-xs">
          <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-semibold" data-testid="kpi-scheduled">
            {counts.scheduled} scheduled
          </span>
          <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-semibold" data-testid="kpi-published">
            {counts.published} published
          </span>
          <span className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 font-semibold" data-testid="kpi-drafts">
            {counts.draft} drafts
          </span>
          <span className="ml-auto text-[10px] text-gray-400">Drag a chip onto another day to reschedule</span>
        </div>

        {/* Day-of-week header */}
        <div className="grid grid-cols-7 gap-1 text-[10px] uppercase tracking-widest text-gray-400 px-0.5">
          {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(d => <div key={d}>{d}</div>)}
        </div>

        {/* 6×7 month grid */}
        <div className="grid grid-cols-7 gap-1" data-testid="calendar-grid">
          {gridDays.map((day, idx) => {
            const inMonth = day.getMonth() === anchor.getMonth();
            const isToday = sameDay(day, today);
            const key = `${day.getFullYear()}-${day.getMonth()}-${day.getDate()}`;
            const dayPosts = postsByDay.get(key) || [];
            const isHover = hoverDay === day.toDateString();
            return (
              <div
                key={idx}
                onDragOver={(e) => handleDragOver(e, day)}
                onDragLeave={() => setHoverDay(null)}
                onDrop={(e) => handleDrop(e, day)}
                className={`min-h-[88px] p-1.5 rounded border text-xs transition-colors ${inMonth ? 'bg-white' : 'bg-gray-50/60 opacity-60'} ${isToday ? 'ring-2 ring-orange-300' : ''} ${isHover ? 'bg-amber-50' : ''}`}
                data-testid={`cal-cell-${day.toISOString().slice(0, 10)}`}
              >
                <div className={`text-[10px] font-semibold ${isToday ? 'text-orange-600' : 'text-gray-500'} mb-1`}>
                  {day.getDate()}
                </div>
                <div className="space-y-1">
                  {dayPosts.slice(0, 4).map((p) => (
                    <div
                      key={p.id}
                      draggable={p.status !== 'published'}
                      onDragStart={(e) => handleDragStart(e, p)}
                      className={`text-[10px] rounded px-1.5 py-0.5 truncate cursor-grab active:cursor-grabbing ${p.status === 'published' ? 'opacity-80' : ''}`}
                      style={{
                        background: `${PLATFORM_COLORS[p.platform] || '#888'}15`,
                        borderLeft: `3px solid ${PLATFORM_COLORS[p.platform] || '#888'}`,
                        color: PLATFORM_COLORS[p.platform] || '#444',
                      }}
                      title={p.caption}
                      data-testid={`cal-post-${p.id}`}
                    >
                      <span className="font-semibold mr-1">
                        {p.status === 'published' ? '✓' : p.status === 'scheduled' ? '◷' : '✎'}
                      </span>
                      <span className="font-medium">{(p.platform || '').slice(0, 2).toUpperCase()}</span>
                      <span className="ml-1 opacity-80">{(p.caption || '').slice(0, 16)}</span>
                    </div>
                  ))}
                  {dayPosts.length > 4 && (
                    <div className="text-[9px] text-gray-400">+{dayPosts.length - 4} more</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Upcoming next 7 days */}
        <div className="mt-2 border-t pt-3" data-testid="upcoming-strip">
          <h3 className="text-xs uppercase tracking-widest text-gray-500 mb-2 flex items-center gap-1.5">
            <Sparkles size={12} /> Next 7 days
          </h3>
          {(() => {
            const win = (posts || [])
              .filter((p) => p.scheduledFor)
              .filter((p) => {
                const t = new Date(p.scheduledFor).getTime();
                return t >= Date.now() && t <= Date.now() + 7 * 86400000;
              })
              .sort((a, b) => a.scheduledFor.localeCompare(b.scheduledFor))
              .slice(0, 8);
            if (win.length === 0) {
              return <p className="text-xs text-gray-400 italic">Nothing scheduled in the next 7 days — try AI Weekly Plan.</p>;
            }
            return (
              <ul className="space-y-1">
                {win.map((p) => (
                  <li
                    key={p.id}
                    className="flex items-center gap-2 text-xs hover:bg-gray-50 rounded px-1.5 py-1"
                    data-testid={`upcoming-${p.id}`}
                  >
                    <span
                      className="w-2 h-2 rounded-full shrink-0"
                      style={{ background: PLATFORM_COLORS[p.platform] || '#888' }}
                    />
                    <span className="font-semibold w-20">{new Date(p.scheduledFor).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric' })}</span>
                    <span className="text-gray-500 w-20">{p.platform}</span>
                    <span className="flex-1 truncate">{p.caption}</span>
                    <button onClick={() => handlePublish(p.id)} className="text-gray-400 hover:text-emerald-600" data-testid={`upcoming-publish-${p.id}`} title="Publish now">
                      <Send size={12} />
                    </button>
                    <button onClick={() => handleDelete(p.id)} className="text-gray-400 hover:text-red-600" data-testid={`upcoming-delete-${p.id}`} title="Delete">
                      <Trash2 size={12} />
                    </button>
                  </li>
                ))}
              </ul>
            );
          })()}
        </div>
      </CardContent>
    </Card>
  );
};
