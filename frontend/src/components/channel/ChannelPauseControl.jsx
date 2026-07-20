import React, { useEffect, useMemo, useState } from 'react';
import { finalizeAPI } from '../../services/api';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../ui/dialog';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { toast } from 'sonner';
import {
  Pause, Play, Clock, AlertTriangle, CalendarClock, Plus, Trash2, Zap,
} from 'lucide-react';

const WEEK_DAYS = [
  { key: 'mon', label: 'Mon' },
  { key: 'tue', label: 'Tue' },
  { key: 'wed', label: 'Wed' },
  { key: 'thu', label: 'Thu' },
  { key: 'fri', label: 'Fri' },
  { key: 'sat', label: 'Sat' },
  { key: 'sun', label: 'Sun' },
];

const emptyDayHours = () => ({ open: '09:00', close: '22:00', closed: false });

const defaultSchedule = () => ({
  enabled: false,
  mode: 'simple',
  simpleHours: emptyDayHours(),
  weeklyHours: WEEK_DAYS.reduce((acc, d) => ({ ...acc, [d.key]: emptyDayHours() }), {}),
  overrides: [],
});

/**
 * Per-channel pause / resume / schedule / hours control.
 *  - Reads state from /api/channels/state and effective status from
 *    /api/channels/{channel}/effective-status.
 *  - Simple hours: single open/close applied every day.
 *  - Weekly hours: per-day-of-week schedule with a closed toggle.
 *  - Overrides: date-based one-off closures or custom hours.
 */
export default function ChannelPauseControl({ channel, theme }) {
  const [state, setState] = useState(null);
  const [effective, setEffective] = useState(null);
  const [pauseDialog, setPauseDialog] = useState(false);
  const [scheduleDialog, setScheduleDialog] = useState(false);
  const [reason, setReason] = useState('');
  const [pausedUntil, setPausedUntil] = useState('');
  const [mode, setMode] = useState('pause'); // pause | schedule
  const [schedule, setSchedule] = useState(defaultSchedule());
  const [saving, setSaving] = useState(false);

  const loadState = async () => {
    try {
      const r = await finalizeAPI.channelStates();
      const s = (r.data || []).find(x => x.channel === channel);
      setState(s || { channel, status: 'active' });
    } catch { /* ignore */ }
    try {
      const e = await finalizeAPI.channelEffectiveStatus(channel);
      setEffective(e.data);
    } catch { /* ignore */ }
  };

  const loadSchedule = async () => {
    try {
      const r = await finalizeAPI.getChannelSchedule(channel);
      const d = r.data || {};
      setSchedule({
        enabled: !!d.enabled,
        mode: d.mode || 'simple',
        simpleHours: d.simpleHours || emptyDayHours(),
        weeklyHours: d.weeklyHours || defaultSchedule().weeklyHours,
        overrides: Array.isArray(d.overrides) ? d.overrides : [],
      });
    } catch { setSchedule(defaultSchedule()); }
  };

  useEffect(() => { loadState(); }, [channel]);

  const openPause = (m) => {
    setMode(m);
    setReason('');
    setPausedUntil('');
    setPauseDialog(true);
  };

  const openSchedule = async () => {
    await loadSchedule();
    setScheduleDialog(true);
  };

  const submitPause = async () => {
    try {
      await finalizeAPI.updateChannelState({
        channel,
        action: mode,
        pausedUntil: mode === 'schedule' ? pausedUntil : null,
        reason: reason || null,
      });
      toast.success(mode === 'schedule' ? 'Channel paused until scheduled resume' : 'Channel paused');
      setPauseDialog(false);
      loadState();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Failed'); }
  };

  const resume = async () => {
    try {
      await finalizeAPI.updateChannelState({ channel, action: 'resume', pausedUntil: null, reason: null });
      toast.success('Channel resumed');
      loadState();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Failed'); }
  };

  const saveSchedule = async () => {
    setSaving(true);
    try {
      await finalizeAPI.saveChannelSchedule(channel, schedule);
      toast.success('Schedule saved');
      setScheduleDialog(false);
      loadState();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Failed'); }
    finally { setSaving(false); }
  };

  const paused = state?.status === 'paused';
  const openInfo = effective?.openNow;
  const scheduleEnabled = effective?.schedule?.enabled;

  const setWeekly = (day, patch) => setSchedule(s => ({
    ...s,
    weeklyHours: { ...s.weeklyHours, [day]: { ...s.weeklyHours[day], ...patch } },
  }));

  const addOverride = () => setSchedule(s => ({
    ...s,
    overrides: [...s.overrides, { date: new Date().toISOString().slice(0, 10), closed: true, reason: '' }],
  }));

  const updateOverride = (idx, patch) => setSchedule(s => ({
    ...s,
    overrides: s.overrides.map((o, i) => i === idx ? { ...o, ...patch } : o),
  }));

  const removeOverride = (idx) => setSchedule(s => ({
    ...s,
    overrides: s.overrides.filter((_, i) => i !== idx),
  }));

  const statusBadge = useMemo(() => {
    if (paused) return null;
    if (!scheduleEnabled) return null;
    if (openInfo?.isOpen) return (
      <Badge className="bg-sky-100 text-sky-700 border border-sky-200" data-testid={`channel-open-hours-${channel}`}>
        <Clock size={11} className="mr-1" /> {openInfo.reason}
      </Badge>
    );
    return (
      <Badge className="bg-orange-100 text-orange-700 border border-orange-200" data-testid={`channel-closed-hours-${channel}`}>
        <CalendarClock size={11} className="mr-1" /> Closed · {openInfo?.reason}
      </Badge>
    );
  }, [paused, scheduleEnabled, openInfo, channel]);

  return (
    <>
      <div className="flex items-center gap-2 flex-wrap" data-testid={`channel-pause-${channel}`}>
        {paused ? (
          <>
            <Badge className="bg-amber-100 text-amber-700 border border-amber-200" data-testid={`channel-paused-${channel}`}>
              <Pause size={11} className="mr-1" /> Paused
              {state?.pausedUntil && (
                <span className="ml-1 text-[10px]">
                  · until {new Date(state.pausedUntil).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                </span>
              )}
            </Badge>
            {state?.reason && (
              <span className="text-[11px] text-gray-500 flex items-center gap-1">
                <AlertTriangle size={11} /> {state.reason}
              </span>
            )}
            <Button size="sm" variant="outline" onClick={resume} data-testid={`channel-resume-${channel}`}>
              <Play size={12} className="mr-1" /> Resume
            </Button>
          </>
        ) : (
          <>
            <Badge className="bg-emerald-100 text-emerald-700 border border-emerald-200" data-testid={`channel-active-${channel}`}>
              <Play size={11} className="mr-1" /> Live
            </Badge>
            <Button size="sm" variant="outline" onClick={() => openPause('pause')} data-testid={`channel-pause-btn-${channel}`}>
              <Pause size={12} className="mr-1" /> Pause
            </Button>
            <Button size="sm" variant="ghost" onClick={() => openPause('schedule')} data-testid={`channel-schedule-btn-${channel}`}>
              <Zap size={12} className="mr-1" /> Pause until…
            </Button>
          </>
        )}
        <Button size="sm" variant="ghost" onClick={openSchedule} data-testid={`channel-hours-btn-${channel}`}>
          <CalendarClock size={12} className="mr-1" /> Hours
        </Button>
        {statusBadge}
      </div>

      {/* Pause / pause-until dialog */}
      <Dialog open={pauseDialog} onOpenChange={setPauseDialog}>
        <DialogContent className="max-w-sm" data-testid={`channel-pause-dialog-${channel}`}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {mode === 'schedule' ? <Clock size={16} /> : <Pause size={16} />}
              {mode === 'schedule' ? 'Pause until…' : 'Pause channel'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            {mode === 'schedule' && (
              <div>
                <label className="text-xs font-medium text-gray-500 mb-1 block">Resume automatically at</label>
                <Input type="datetime-local" value={pausedUntil} onChange={e => setPausedUntil(e.target.value)}
                  data-testid={`channel-until-${channel}`} />
              </div>
            )}
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Reason (visible to staff)</label>
              <Textarea rows={2} value={reason} onChange={e => setReason(e.target.value)}
                placeholder="e.g. Kitchen slammed, out of X, staff-short…" data-testid={`channel-reason-${channel}`} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPauseDialog(false)}>Cancel</Button>
            <Button onClick={submitPause} style={{ background: theme?.primary || '#f97316' }} className="text-white"
              data-testid={`channel-pause-confirm-${channel}`}>
              {mode === 'schedule' ? 'Pause until' : 'Pause now'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Hours / weekly schedule dialog */}
      <Dialog open={scheduleDialog} onOpenChange={setScheduleDialog}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto" data-testid={`channel-schedule-dialog-${channel}`}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CalendarClock size={16} /> Channel hours — {channel}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={schedule.enabled}
                onChange={e => setSchedule({ ...schedule, enabled: e.target.checked })}
                data-testid={`schedule-enabled-${channel}`} />
              <span>Enable scheduled hours</span>
              <span className="text-[11px] text-gray-500">(if off, the channel is always live except when manually paused)</span>
            </label>

            {schedule.enabled && (
              <>
                <div className="flex items-center gap-2 text-sm">
                  <span className="font-medium">Mode:</span>
                  <button
                    onClick={() => setSchedule({ ...schedule, mode: 'simple' })}
                    className={`px-3 py-1 rounded-full text-xs ${schedule.mode === 'simple' ? 'text-white' : 'bg-gray-100 text-gray-700'}`}
                    style={schedule.mode === 'simple' ? { background: theme?.primary || '#f97316' } : {}}
                    data-testid={`mode-simple-${channel}`}>
                    Simple (daily)
                  </button>
                  <button
                    onClick={() => setSchedule({ ...schedule, mode: 'weekly' })}
                    className={`px-3 py-1 rounded-full text-xs ${schedule.mode === 'weekly' ? 'text-white' : 'bg-gray-100 text-gray-700'}`}
                    style={schedule.mode === 'weekly' ? { background: theme?.primary || '#f97316' } : {}}
                    data-testid={`mode-weekly-${channel}`}>
                    Weekly (per day)
                  </button>
                </div>

                {schedule.mode === 'simple' ? (
                  <div className="border rounded p-3 bg-amber-50/30">
                    <p className="text-xs font-bold uppercase text-gray-500 mb-2">Every day</p>
                    <div className="flex items-center gap-2">
                      <label className="flex items-center gap-1 text-xs">
                        <input type="checkbox" checked={!!schedule.simpleHours?.closed}
                          onChange={e => setSchedule({ ...schedule, simpleHours: { ...schedule.simpleHours, closed: e.target.checked } })}
                          data-testid={`simple-closed-${channel}`} />
                        Closed
                      </label>
                      <Input type="time" className="w-28" disabled={!!schedule.simpleHours?.closed}
                        value={schedule.simpleHours?.open || ''}
                        onChange={e => setSchedule({ ...schedule, simpleHours: { ...schedule.simpleHours, open: e.target.value } })}
                        data-testid={`simple-open-${channel}`} />
                      <span className="text-xs">to</span>
                      <Input type="time" className="w-28" disabled={!!schedule.simpleHours?.closed}
                        value={schedule.simpleHours?.close || ''}
                        onChange={e => setSchedule({ ...schedule, simpleHours: { ...schedule.simpleHours, close: e.target.value } })}
                        data-testid={`simple-close-${channel}`} />
                    </div>
                  </div>
                ) : (
                  <div className="border rounded p-3 bg-amber-50/30 space-y-1">
                    <p className="text-xs font-bold uppercase text-gray-500 mb-2">Weekly hours</p>
                    {WEEK_DAYS.map(d => {
                      const h = schedule.weeklyHours[d.key] || emptyDayHours();
                      return (
                        <div key={d.key} className="flex items-center gap-2" data-testid={`weekly-row-${d.key}`}>
                          <span className="w-10 text-xs font-medium">{d.label}</span>
                          <label className="flex items-center gap-1 text-xs">
                            <input type="checkbox" checked={!!h.closed}
                              onChange={e => setWeekly(d.key, { closed: e.target.checked })}
                              data-testid={`weekly-closed-${d.key}`} />
                            Closed
                          </label>
                          <Input type="time" className="w-24 h-8" disabled={h.closed}
                            value={h.open || ''} onChange={e => setWeekly(d.key, { open: e.target.value })}
                            data-testid={`weekly-open-${d.key}`} />
                          <span className="text-xs">to</span>
                          <Input type="time" className="w-24 h-8" disabled={h.closed}
                            value={h.close || ''} onChange={e => setWeekly(d.key, { close: e.target.value })}
                            data-testid={`weekly-close-${d.key}`} />
                        </div>
                      );
                    })}
                  </div>
                )}

                <div className="border rounded p-3 bg-purple-50/30">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs font-bold uppercase text-gray-500">Date overrides (holidays, one-offs)</p>
                    <Button size="sm" variant="outline" onClick={addOverride} data-testid={`add-override-${channel}`}>
                      <Plus size={12} className="mr-1" /> Add date
                    </Button>
                  </div>
                  {schedule.overrides.length === 0 ? (
                    <p className="text-[11px] text-gray-500">No overrides. Add one to close a specific date or set custom hours.</p>
                  ) : (
                    <div className="space-y-1">
                      {schedule.overrides.map((o, idx) => (
                        <div key={idx} className="flex items-center gap-2 text-xs flex-wrap" data-testid={`override-row-${idx}`}>
                          <Input type="date" className="w-36 h-8" value={o.date || ''}
                            onChange={e => updateOverride(idx, { date: e.target.value })}
                            data-testid={`override-date-${idx}`} />
                          <label className="flex items-center gap-1">
                            <input type="checkbox" checked={!!o.closed}
                              onChange={e => updateOverride(idx, { closed: e.target.checked })}
                              data-testid={`override-closed-${idx}`} />
                            Closed
                          </label>
                          {!o.closed && (
                            <>
                              <Input type="time" className="w-24 h-8" value={o.open || ''}
                                onChange={e => updateOverride(idx, { open: e.target.value })}
                                data-testid={`override-open-${idx}`} />
                              <span>to</span>
                              <Input type="time" className="w-24 h-8" value={o.close || ''}
                                onChange={e => updateOverride(idx, { close: e.target.value })}
                                data-testid={`override-close-${idx}`} />
                            </>
                          )}
                          <Input className="flex-1 h-8 min-w-[120px]" placeholder="Reason (optional)"
                            value={o.reason || ''} onChange={e => updateOverride(idx, { reason: e.target.value })}
                            data-testid={`override-reason-${idx}`} />
                          <Button size="sm" variant="ghost" onClick={() => removeOverride(idx)}
                            data-testid={`override-remove-${idx}`}>
                            <Trash2 size={12} className="text-red-500" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setScheduleDialog(false)} data-testid={`schedule-cancel-${channel}`}>Cancel</Button>
            <Button onClick={saveSchedule} disabled={saving}
              style={{ background: theme?.primary || '#f97316' }} className="text-white"
              data-testid={`schedule-save-${channel}`}>
              {saving ? 'Saving…' : 'Save schedule'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
