import React from 'react';
import { Flame, Pause, Check, Send, Zap, BellRing, Users } from 'lucide-react';
import { Button } from '../ui/button';
import { courseStatus } from '../../lib/coursing';

const STATUS_TONE = {
  queued: { bg: '#f1f5f9', fg: '#475569', label: 'queued' },
  held:   { bg: '#f3e8ff', fg: '#7e22ce', label: 'held' },
  fired:  { bg: '#fef3c7', fg: '#b45309', label: 'fired' },
  ready:  { bg: '#dcfce7', fg: '#15803d', label: 'ready' },
  served: { bg: '#d1fae5', fg: '#047857', label: 'served' },
};

/**
 * Course header inside the POS cart: which course, what state it's in at the
 * pass, and the Fire / Hold controls.
 *
 * Fire and Hold only mean anything once the order exists in the kitchen, so
 * before the cart is sent they're not rendered at all — showing dead buttons
 * would suggest the kitchen had the order when it doesn't.
 */
export function CourseHeader({ course, config, kitchenOrder, onFire, onHold, onServe, busy }) {
  const sent = !!kitchenOrder;
  const status = sent ? courseStatus(kitchenOrder, course.key) : null;
  const tone = STATUS_TONE[status] || STATUS_TONE.queued;

  return (
    <div className="flex items-center justify-between px-2 py-1 rounded-t-md border-b"
      style={{ background: tone.bg }} data-testid={`cart-course-${course.key}`}>
      <div className="flex items-center gap-1.5">
        <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: tone.fg }}>
          {course.label}
        </span>
        <span className="text-[9px] text-gray-500">
          {course.items.length} item{course.items.length === 1 ? '' : 's'}
        </span>
        {sent && (
          <span className="text-[9px] uppercase px-1 rounded" style={{ color: tone.fg }}
            data-testid={`cart-course-status-${course.key}`}>
            · {tone.label}
          </span>
        )}
      </div>

      {sent && (
        <div className="flex gap-1">
          {['queued', 'held'].includes(status) && (
            <button type="button" disabled={busy} onClick={() => onFire(course.key)}
              className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500 text-white hover:bg-amber-600 disabled:opacity-50 flex items-center gap-0.5"
              data-testid={`cart-fire-${course.key}`}>
              <Flame size={9} /> Fire
            </button>
          )}
          {status === 'queued' && (
            <button type="button" disabled={busy} onClick={() => onHold(course.key)}
              className="text-[10px] px-1.5 py-0.5 rounded bg-white border hover:bg-purple-50 disabled:opacity-50 flex items-center gap-0.5"
              data-testid={`cart-hold-${course.key}`}>
              <Pause size={9} /> Hold
            </button>
          )}
          {status === 'fired' && (
            <span className="text-[10px] px-1.5 py-0.5 text-amber-700 flex items-center gap-0.5">
              <Flame size={9} /> cooking
            </span>
          )}
          {/* The kitchen called this course ready — the whole point of
              plumbing ready-state back, so nobody watches the pass. */}
          {status === 'ready' && (
            <button type="button" disabled={busy} onClick={() => onServe(course.key)}
              className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 flex items-center gap-0.5 animate-pulse"
              data-testid={`cart-serve-${course.key}`}>
              <BellRing size={9} /> Ready — run it
            </button>
          )}
          {status === 'served' && (
            <span className="text-[10px] px-1.5 py-0.5 text-emerald-700 flex items-center gap-0.5">
              <Check size={9} /> served
            </span>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Standing banner for any course the kitchen has called ready.
 *
 * Sits above the cart rather than inside a course group, because a server
 * scanning the POS mid-service shouldn't have to find the right group to
 * notice food is dying on the pass.
 */
export function ReadyBanner({ courses, onServe, busy }) {
  if (!courses || courses.length === 0) return null;
  return (
    <div className="mb-2 rounded-md border border-emerald-300 bg-emerald-50 p-2" data-testid="cart-ready-banner">
      <div className="flex items-center gap-1.5 mb-1">
        <BellRing size={12} className="text-emerald-700" />
        <span className="text-[11px] font-semibold text-emerald-800">
          Ready at the pass
        </span>
      </div>
      <div className="flex flex-wrap gap-1">
        {courses.map(c => (
          <button key={c.key} type="button" disabled={busy} onClick={() => onServe(c.key)}
            className="text-[10px] px-2 py-0.5 rounded bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50"
            data-testid={`ready-run-${c.key}`}>
            {c.label} — run it
          </button>
        ))}
      </div>
    </div>
  );
}

/**
 * Send-to-kitchen bar. "Send" respects the venue's coursing rules (first
 * course fires, the rest hold); "Fire All" is the straight-fire escape hatch
 * for when the table wants everything at once.
 */
export function SendToKitchenBar({ config, sent, busy, onSend, onStraightFire, disabled,
                                   pendingItems = 0, rounds = 1 }) {
  // Everything in the cart is already on the ticket — nothing to send.
  if (sent && pendingItems === 0) {
    return (
      <div className="text-[11px] text-center text-emerald-700 py-1" data-testid="cart-sent-to-kitchen">
        On ticket{rounds > 1 ? ` · ${rounds} rounds` : ''} — fire courses above as the table is ready.
      </div>
    );
  }
  // A ticket exists and the table has ordered more: this is a second round on
  // the same ticket, not a new one the runner has to reconcile.
  const adding = sent && pendingItems > 0;
  return (
    <div data-testid="cart-send-bar">
      {adding && (
        <p className="text-[10px] text-gray-500 mb-1 text-center" data-testid="cart-round-hint">
          {pendingItems} new item{pendingItems === 1 ? '' : 's'} — adds to the table's existing ticket as round {rounds + 1}
        </p>
      )}
      <div className="flex gap-2">
        <Button variant="outline" className="flex-1 h-9 text-xs" disabled={busy || disabled}
          onClick={onSend} data-testid="cart-send-kitchen">
          <Send size={13} className="mr-1" /> {adding ? 'Add to Ticket' : 'Send to Kitchen'}
        </Button>
        {config?.allowStraightFire && (
          <Button variant="outline" className="flex-1 h-9 text-xs" disabled={busy || disabled}
            onClick={onStraightFire} data-testid="cart-straight-fire"
            title="Send everything to the pass now, ignoring courses">
            <Zap size={13} className="mr-1" /> Fire All Now
          </Button>
        )}
      </div>
    </div>
  );
}

/** Seat picker for a cart line, so runners know who gets what. */
export function SeatPicker({ value, onChange, seats }) {
  return (
    <span className="flex items-center gap-1">
      <Users size={9} className="text-gray-400" />
      <select
        className="text-[10px] border rounded px-1 py-0.5 bg-white"
        value={value ?? ''}
        onChange={e => onChange(e.target.value === '' ? null : parseInt(e.target.value, 10))}
        data-testid="seat-select"
      >
        <option value="">Seat —</option>
        {seats.map(s => <option key={s} value={s}>Seat {s}</option>)}
      </select>
    </span>
  );
}
