import React, { useEffect, useState } from 'react';
import { finalizeAPI } from '../../services/api';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../ui/dialog';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { toast } from 'sonner';
import { Pause, Play, Clock, AlertTriangle } from 'lucide-react';

/**
 * Per-channel pause/resume/schedule control. Reads its state from
 * /api/channels/state and mutates via POST /api/channels/state.
 */
export default function ChannelPauseControl({ channel, theme }) {
  const [state, setState] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [reason, setReason] = useState('');
  const [pausedUntil, setPausedUntil] = useState('');
  const [mode, setMode] = useState('pause'); // pause | schedule

  const load = async () => {
    try {
      const r = await finalizeAPI.channelStates();
      const s = (r.data || []).find(x => x.channel === channel);
      setState(s || { channel, status: 'active' });
    } catch { /* ignore */ }
  };

  useEffect(() => { load(); }, [channel]);

  const openPause = (m) => {
    setMode(m);
    setReason('');
    setPausedUntil('');
    setDialogOpen(true);
  };

  const submit = async () => {
    try {
      await finalizeAPI.updateChannelState({
        channel,
        action: mode,
        pausedUntil: mode === 'schedule' ? pausedUntil : null,
        reason: reason || null,
      });
      toast.success(mode === 'schedule' ? 'Channel paused until scheduled resume' : 'Channel paused');
      setDialogOpen(false);
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Failed'); }
  };

  const resume = async () => {
    try {
      await finalizeAPI.updateChannelState({ channel, action: 'resume', pausedUntil: null, reason: null });
      toast.success('Channel resumed');
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Failed'); }
  };

  const paused = state?.status === 'paused';

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
              <Clock size={12} className="mr-1" /> Schedule
            </Button>
          </>
        )}
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-sm" data-testid={`channel-pause-dialog-${channel}`}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {mode === 'schedule' ? <Clock size={16} /> : <Pause size={16} />}
              {mode === 'schedule' ? 'Schedule pause' : 'Pause channel'}
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
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button onClick={submit} style={{ background: theme?.primary || '#f97316' }} className="text-white"
              data-testid={`channel-pause-confirm-${channel}`}>
              {mode === 'schedule' ? 'Schedule pause' : 'Pause now'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
