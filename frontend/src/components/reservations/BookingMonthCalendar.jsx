import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { ChevronLeft, ChevronRight, Ban, CheckCircle2, Users, CalendarX } from 'lucide-react';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { reservationsAPI } from '../../services/api';
import { toast } from 'sonner';

/** yyyy-mm-dd for a Date object, in local time. */
const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const WEEK_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTH_LABELS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

/**
 * Month calendar with a green dot on days that already have bookings, plus a
 * per-cell "Stop bookings" toggle. Blocked days can be a single day (special
 * event) OR a fromDate → toDate range. Existing bookings on a blocked day
 * are untouched — only new incoming bookings get 409'd by the backend.
 */
export default function BookingMonthCalendar({ onSelectDate }) {
  const today = useMemo(() => new Date(), []);
  const [cursor, setCursor] = useState(new Date(today.getFullYear(), today.getMonth(), 1));
  const [data, setData] = useState({ counts: {}, covers: {}, blackouts: {} });
  const [loading, setLoading] = useState(false);
  const [blockDialog, setBlockDialog] = useState(null); // { date } or { fromDate, toDate }
  const [blockReason, setBlockReason] = useState('');
  const [rangeStart, setRangeStart] = useState('');
  const [rangeEnd, setRangeEnd] = useState('');
  const [showRangeDialog, setShowRangeDialog] = useState(false);

  const monthStart = useMemo(() => new Date(cursor.getFullYear(), cursor.getMonth(), 1), [cursor]);
  const monthEnd = useMemo(() => new Date(cursor.getFullYear(), cursor.getMonth() + 1, 0), [cursor]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      // Pad ±1 week so leading/trailing cells from adjacent months still show dots
      const from = new Date(monthStart); from.setDate(from.getDate() - 7);
      const to = new Date(monthEnd); to.setDate(to.getDate() + 7);
      const r = await reservationsAPI.dayCounts(iso(from), iso(to));
      setData(r.data || { counts: {}, covers: {}, blackouts: {} });
    } catch {
      toast.error('Failed to load month view');
    } finally { setLoading(false); }
  }, [monthStart, monthEnd]);

  useEffect(() => { load(); }, [load]);

  // Build the 7×N grid — pad to full weeks
  const cells = useMemo(() => {
    const first = new Date(monthStart);
    const startDow = first.getDay(); // 0..6
    const gridStart = new Date(first);
    gridStart.setDate(gridStart.getDate() - startDow);
    const gridDays = 42; // always 6 rows so height stays consistent
    const out = [];
    for (let i = 0; i < gridDays; i++) {
      const d = new Date(gridStart);
      d.setDate(d.getDate() + i);
      out.push(d);
    }
    return out;
  }, [monthStart]);

  const toggleBlock = async (dateStr, isBlocked) => {
    try {
      if (isBlocked) {
        await reservationsAPI.deleteBlackout(dateStr);
        toast.success(`Bookings re-opened for ${dateStr}`);
      } else {
        setBlockDialog({ date: dateStr });
        setBlockReason('');
        return;
      }
      load();
    } catch { toast.error('Update failed'); }
  };

  const confirmSingleBlock = async () => {
    if (!blockDialog?.date) return;
    try {
      await reservationsAPI.createBlackout({ date: blockDialog.date, reason: blockReason || 'Bookings paused' });
      toast.success(`Bookings paused for ${blockDialog.date}`);
      setBlockDialog(null);
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Failed to pause'); }
  };

  const confirmRangeBlock = async () => {
    if (!rangeStart || !rangeEnd) { toast.error('Pick both dates'); return; }
    try {
      const r = await reservationsAPI.createBlackout({ fromDate: rangeStart, toDate: rangeEnd, reason: blockReason || 'Special event' });
      toast.success(`Paused ${r.data?.count || 0} day(s)`);
      setShowRangeDialog(false); setRangeStart(''); setRangeEnd(''); setBlockReason('');
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Failed to pause range'); }
  };

  const pauseRestOfToday = async () => {
    const todayStr = iso(today);
    const end = new Date(); end.setHours(23, 59, 59, 999);
    try {
      await reservationsAPI.createBlackout({ date: todayStr, reason: "Paused for the rest of today", blockUntil: end.toISOString() });
      toast.success('Incoming bookings paused for the rest of today');
      load();
    } catch { toast.error('Failed to pause'); }
  };

  return (
    <Card className="border-0 shadow-sm" data-testid="booking-month-calendar">
      <CardContent className="p-4">
        {/* Toolbar */}
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1))} data-testid="cal-prev-month">
              <ChevronLeft size={14} />
            </Button>
            <h3 className="text-lg font-semibold min-w-[180px] text-center" data-testid="cal-current-month">
              {MONTH_LABELS[cursor.getMonth()]} {cursor.getFullYear()}
            </h3>
            <Button variant="outline" size="sm" onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1))} data-testid="cal-next-month">
              <ChevronRight size={14} />
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setCursor(new Date(today.getFullYear(), today.getMonth(), 1))} data-testid="cal-today-btn">
              Today
            </Button>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={pauseRestOfToday} data-testid="pause-rest-of-today-btn">
              <Ban size={14} className="mr-1" /> Pause today&apos;s bookings
            </Button>
            <Button variant="outline" size="sm" onClick={() => setShowRangeDialog(true)} data-testid="block-range-btn">
              <CalendarX size={14} className="mr-1" /> Block date range
            </Button>
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 text-xs text-gray-500 mb-3 flex-wrap">
          <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" /> Bookings exist</div>
          <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-red-500 inline-block" /> Bookings paused</div>
          <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded ring-2 ring-indigo-500 inline-block" /> Today</div>
        </div>

        {/* Weekday header */}
        <div className="grid grid-cols-7 mb-1">
          {WEEK_LABELS.map(w => (
            <div key={w} className="text-center text-[11px] font-bold text-gray-400 uppercase py-1">{w}</div>
          ))}
        </div>

        {/* Grid */}
        <div className={`grid grid-cols-7 gap-1 ${loading ? 'opacity-60' : ''}`} data-testid="calendar-grid">
          {cells.map((d, i) => {
            const key = iso(d);
            const inMonth = d.getMonth() === cursor.getMonth();
            const isToday = key === iso(today);
            const count = data.counts?.[key] || 0;
            const covers = data.covers?.[key] || 0;
            const black = data.blackouts?.[key];
            const isBlocked = !!black;
            return (
              <button
                key={i}
                onClick={() => { if (inMonth && onSelectDate) onSelectDate(key); }}
                className={`aspect-square min-h-[72px] p-2 rounded-lg border text-left flex flex-col justify-between transition-colors ${
                  inMonth ? 'bg-white hover:bg-gray-50' : 'bg-gray-50 text-gray-300'
                } ${isToday ? 'ring-2 ring-indigo-500' : 'border-gray-200'} ${isBlocked && inMonth ? 'bg-red-50/40 border-red-200' : ''}`}
                data-testid={`cal-day-${key}`}
              >
                <div className="flex items-start justify-between">
                  <span className={`text-sm font-medium ${isToday ? 'text-indigo-600' : ''}`}>{d.getDate()}</span>
                  {count > 0 && !isBlocked && (
                    <span className="w-2 h-2 rounded-full bg-emerald-500" data-testid={`cal-dot-${key}`} title={`${count} booking${count === 1 ? '' : 's'}`} />
                  )}
                  {isBlocked && (
                    <Ban size={12} className="text-red-500" data-testid={`cal-block-${key}`} />
                  )}
                </div>
                {inMonth && (count > 0 || covers > 0) && !isBlocked && (
                  <div className="text-[10px] text-gray-500">
                    <div>{count} bkg{count === 1 ? '' : 's'}</div>
                    <div className="flex items-center gap-0.5"><Users size={9} /> {covers}</div>
                  </div>
                )}
                {inMonth && isBlocked && (
                  <div className="text-[10px] text-red-600 truncate" title={black.reason}>Paused</div>
                )}
                {inMonth && (
                  <div className="mt-1">
                    <span
                      role="button"
                      tabIndex={0}
                      onClick={(e) => { e.stopPropagation(); toggleBlock(key, isBlocked); }}
                      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.stopPropagation(); e.preventDefault(); toggleBlock(key, isBlocked); } }}
                      className={`inline-block text-[10px] px-1.5 py-0.5 rounded transition-colors cursor-pointer ${isBlocked ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200' : 'bg-gray-100 text-gray-600 hover:bg-red-100 hover:text-red-700'}`}
                      data-testid={`cal-toggle-${key}`}
                    >
                      {isBlocked ? <><CheckCircle2 size={9} className="inline" /> Un-pause</> : <><Ban size={9} className="inline" /> Pause</>}
                    </span>
                  </div>
                )}
              </button>
            );
          })}
        </div>

        {/* Single-day block dialog */}
        <Dialog open={!!blockDialog} onOpenChange={(o) => { if (!o) setBlockDialog(null); }}>
          <DialogContent className="max-w-sm" data-testid="block-day-dialog">
            <DialogHeader>
              <DialogTitle>Pause bookings — {blockDialog?.date}</DialogTitle>
            </DialogHeader>
            <div className="space-y-3 py-2">
              <p className="text-sm text-gray-500">New incoming bookings for this date will be rejected. Existing bookings are unaffected.</p>
              <div>
                <label className="text-xs font-medium text-gray-500 mb-1 block">Reason (guests won&apos;t see this)</label>
                <Input value={blockReason} onChange={e => setBlockReason(e.target.value)} placeholder="e.g. Private event, storm closure, fully booked" data-testid="block-reason-input" />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setBlockDialog(null)}>Cancel</Button>
              <Button className="bg-red-600 hover:bg-red-700 text-white" onClick={confirmSingleBlock} data-testid="confirm-block-btn">
                <Ban size={14} className="mr-1" /> Pause bookings
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Range block dialog */}
        <Dialog open={showRangeDialog} onOpenChange={setShowRangeDialog}>
          <DialogContent className="max-w-sm" data-testid="block-range-dialog">
            <DialogHeader>
              <DialogTitle>Block a date range</DialogTitle>
            </DialogHeader>
            <div className="space-y-3 py-2">
              <p className="text-sm text-gray-500">Use for holidays, renovations, or multi-day private events.</p>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs font-medium text-gray-500 mb-1 block">From</label>
                  <Input type="date" value={rangeStart} onChange={e => setRangeStart(e.target.value)} data-testid="range-from-input" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-500 mb-1 block">To (inclusive)</label>
                  <Input type="date" value={rangeEnd} onChange={e => setRangeEnd(e.target.value)} data-testid="range-to-input" />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500 mb-1 block">Reason</label>
                <Input value={blockReason} onChange={e => setBlockReason(e.target.value)} placeholder="e.g. Christmas closure" data-testid="range-reason-input" />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowRangeDialog(false)}>Cancel</Button>
              <Button className="bg-red-600 hover:bg-red-700 text-white" onClick={confirmRangeBlock} data-testid="confirm-range-btn">
                <CalendarX size={14} className="mr-1" /> Block range
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Active blackouts summary */}
        {Object.keys(data.blackouts || {}).length > 0 && (
          <div className="mt-4 pt-3 border-t">
            <p className="text-[11px] uppercase text-gray-500 font-bold mb-2">Active blackouts in this window</p>
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(data.blackouts).sort().map(([date, meta]) => (
                <Badge key={date} variant="outline" className="border-red-300 text-red-700 bg-red-50" data-testid={`blackout-badge-${date}`}>
                  {date}{meta.reason ? ` · ${meta.reason}` : ''}
                  <button onClick={() => toggleBlock(date, true)} className="ml-1.5 text-red-500 hover:text-red-700">×</button>
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
