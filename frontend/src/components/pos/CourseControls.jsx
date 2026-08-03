import React from 'react';
import { Flame, Pause, Check, Send, Zap } from 'lucide-react';
import { Button } from '../ui/button';
import { courseStatus } from '../../lib/coursing';

const STATUS_TONE = {
  queued: { bg: '#f1f5f9', fg: '#475569', label: 'queued' },
  held:   { bg: '#f3e8ff', fg: '#7e22ce', label: 'held' },
  fired:  { bg: '#fef3c7', fg: '#b45309', label: 'fired' },
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
export function CourseHeader({ course, config, kitchenOrder, onFire, onHold, busy }) {
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
            <span className="text-[10px] px-1.5 py-0.5 text-emerald-700 flex items-center gap-0.5">
              <Check size={9} /> at pass
            </span>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Send-to-kitchen bar. "Send" respects the venue's coursing rules (first
 * course fires, the rest hold); "Fire All" is the straight-fire escape hatch
 * for when the table wants everything at once.
 */
export function SendToKitchenBar({ config, sent, busy, onSend, onStraightFire, disabled }) {
  if (sent) {
    return (
      <div className="text-[11px] text-center text-emerald-700 py-1" data-testid="cart-sent-to-kitchen">
        Sent to kitchen — fire courses above as the table is ready.
      </div>
    );
  }
  return (
    <div className="flex gap-2" data-testid="cart-send-bar">
      <Button variant="outline" className="flex-1 h-9 text-xs" disabled={busy || disabled}
        onClick={onSend} data-testid="cart-send-kitchen">
        <Send size={13} className="mr-1" /> Send to Kitchen
      </Button>
      {config?.allowStraightFire && (
        <Button variant="outline" className="flex-1 h-9 text-xs" disabled={busy || disabled}
          onClick={onStraightFire} data-testid="cart-straight-fire"
          title="Send everything to the pass now, ignoring courses">
          <Zap size={13} className="mr-1" /> Fire All Now
        </Button>
      )}
    </div>
  );
}
