import React, { useMemo } from 'react';
import { Clock, Edit3 } from 'lucide-react';

/**
 * Sidebar showing the 10 most recently touched products today.
 *
 * "Touched today" = updatedAt OR createdAt falls within the local calendar
 * day. We rely on ISO 8601 strings already produced by the backend; if
 * neither timestamp exists the product is skipped (rather than guessed).
 */
const relTime = (iso) => {
  if (!iso) return '';
  const t = new Date(iso).getTime();
  if (!t) return '';
  const diff = Math.max(0, Date.now() - t);
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return new Date(iso).toLocaleDateString();
};

const isToday = (iso) => {
  if (!iso) return false;
  const d = new Date(iso);
  if (isNaN(d)) return false;
  const now = new Date();
  return d.getFullYear() === now.getFullYear()
    && d.getMonth() === now.getMonth()
    && d.getDate() === now.getDate();
};

export const RecentlyEditedSidebar = ({ theme, products, touchTimes = {}, onEdit }) => {
  const recents = useMemo(() => {
    return [...products]
      .map(p => ({ ...p, _ts: touchTimes[p.id] || p.updatedAt || p.createdAt }))
      .filter(p => isToday(p._ts))
      .sort((a, b) => (b._ts || '').localeCompare(a._ts || ''))
      .slice(0, 10);
  }, [products, touchTimes]);

  return (
    <aside
      className="hidden lg:flex flex-col w-60 shrink-0 bg-white rounded-lg border p-3 sticky top-4 self-start max-h-[calc(100vh-2rem)]"
      data-testid="recently-edited-sidebar"
    >
      <div className="flex items-center gap-2 mb-3 pb-2 border-b">
        <Clock size={14} style={{ color: theme.primary }} />
        <h3 className="text-xs uppercase tracking-widest font-semibold text-gray-700">
          Recently edited today
        </h3>
      </div>
      {recents.length === 0 ? (
        <p className="text-xs text-gray-400 italic py-2" data-testid="recently-edited-empty">
          Nothing yet today — edits will appear here.
        </p>
      ) : (
        <ul className="space-y-1 overflow-y-auto -mx-1 px-1" data-testid="recently-edited-list">
          {recents.map(p => (
            <li
              key={p.id}
              className="group flex items-center gap-2 px-2 py-1.5 rounded hover:bg-amber-50 cursor-pointer text-sm"
              onClick={() => onEdit(p)}
              data-testid={`recent-${p.id}`}
              title="Open editor"
            >
              <img
                src={p.image || 'https://placehold.co/24x24/e5e7eb/9ca3af?text=•'}
                alt=""
                className="w-7 h-7 rounded object-cover shrink-0"
              />
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate" style={{ color: theme.text }}>
                  {p.name}
                </p>
                <p className="text-[10px] text-gray-400">{relTime(p._ts)}</p>
              </div>
              <Edit3 size={12} className="opacity-0 group-hover:opacity-100 text-gray-400" />
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
};
