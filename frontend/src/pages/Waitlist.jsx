import React, { useState, useEffect, useCallback } from 'react';
import {
  Clock, Users, Plus, Phone, UserCheck, X, ArrowUp, ArrowDown,
  Bell, ChevronRight, MessageSquare
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter
} from '../components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import { useTheme } from '../contexts/ThemeContext';
import { waitlistAPI } from '../services/api';
import { toast } from 'sonner';

const WAIT_PRESETS = [5, 10, 15, 20, 30, 45, 60];

export default function WaitlistPage() {
  const { theme } = useTheme();
  const [entries, setEntries] = useState([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({ guestName: '', guestPhone: '', partySize: 2, quotedWait: 15, notes: '', preferences: '' });

  const fetchWaitlist = useCallback(async () => {
    try {
      const res = await waitlistAPI.getAll();
      setEntries(res.data);
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => { fetchWaitlist(); }, [fetchWaitlist]);

  const handleAdd = async () => {
    if (!form.guestName) { toast.error('Guest name is required'); return; }
    try {
      await waitlistAPI.add(form);
      toast.success(`${form.guestName} added to waitlist`);
      setDialogOpen(false);
      setForm({ guestName: '', guestPhone: '', partySize: 2, quotedWait: 15, notes: '', preferences: '' });
      fetchWaitlist();
    } catch (e) { toast.error('Failed to add'); }
  };

  const handleSeat = async (id) => {
    try {
      await waitlistAPI.seat(id);
      toast.success('Guest seated');
      fetchWaitlist();
    } catch (e) { toast.error('Failed to seat guest'); }
  };

  const handleRemove = async (id) => {
    try {
      await waitlistAPI.remove(id);
      fetchWaitlist();
    } catch (e) { toast.error('Failed to remove'); }
  };

  const handleNotify = async (id) => {
    try {
      await waitlistAPI.update(id, { status: 'notified' });
      toast.success('Guest notified');
      fetchWaitlist();
    } catch (e) { toast.error('Failed'); }
  };

  const getWaitDisplay = (entry) => {
    const checkIn = new Date(entry.checkInTime);
    const now = new Date();
    const waited = Math.round((now - checkIn) / 60000);
    return { waited, quoted: entry.quotedWait, overdue: waited > entry.quotedWait };
  };

  const waiting = entries.filter(e => e.status === 'waiting');
  const notified = entries.filter(e => e.status === 'notified');

  return (
    <div className="space-y-6" data-testid="waitlist-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: theme.text }}>Waitlist</h1>
          <p className="text-sm text-gray-500 mt-1">Manage walk-in queue & estimated wait times</p>
        </div>
        <Button onClick={() => setDialogOpen(true)} style={{ background: theme.primary }} data-testid="add-waitlist-btn">
          <Plus size={16} className="mr-2" /> Add to Waitlist
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Waiting', val: waiting.length, icon: Clock, color: '#F59E0B' },
          { label: 'Notified', val: notified.length, icon: Bell, color: '#3B82F6' },
          { label: 'Total Covers', val: entries.reduce((s, e) => s + e.partySize, 0), icon: Users, color: theme.primary },
        ].map((s, i) => (
          <Card key={i} className="border-0 shadow-sm">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: `${s.color}15` }}>
                <s.icon size={20} style={{ color: s.color }} />
              </div>
              <div>
                <p className="text-2xl font-bold" style={{ color: theme.text }}>{s.val}</p>
                <p className="text-xs text-gray-500">{s.label}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Waitlist Queue */}
      <div className="space-y-3">
        {entries.length === 0 ? (
          <Card className="border-0 shadow-sm">
            <CardContent className="py-16 text-center text-gray-400">
              <Users size={40} className="mx-auto mb-3 opacity-30" />
              <p className="text-lg font-medium">No one on the waitlist</p>
              <p className="text-sm mt-1">Add walk-in guests to track their wait time</p>
            </CardContent>
          </Card>
        ) : entries.map((entry, idx) => {
          const wait = getWaitDisplay(entry);
          const isNotified = entry.status === 'notified';
          return (
            <Card key={entry.id} className={`border-0 shadow-sm transition-all ${isNotified ? 'ring-2 ring-blue-200' : ''}`}
              data-testid={`waitlist-entry-${entry.id}`}>
              <CardContent className="p-4">
                <div className="flex items-center gap-4">
                  {/* Position */}
                  <div className="w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg shrink-0"
                    style={{ background: `${theme.primary}15`, color: theme.primary }}>
                    {idx + 1}
                  </div>

                  {/* Guest info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold" style={{ color: theme.text }}>{entry.guestName}</h3>
                      {isNotified && <Badge className="bg-blue-100 text-blue-700 text-xs">Notified</Badge>}
                      {wait.overdue && !isNotified && <Badge className="bg-red-100 text-red-700 text-xs">Overdue</Badge>}
                    </div>
                    <div className="flex items-center gap-3 text-sm text-gray-500 mt-0.5">
                      <span className="flex items-center gap-1"><Users size={12} />{entry.partySize} guests</span>
                      {entry.guestPhone && <span className="flex items-center gap-1"><Phone size={12} />{entry.guestPhone}</span>}
                      {entry.preferences && <span className="text-xs italic">{entry.preferences}</span>}
                    </div>
                    {entry.notes && <p className="text-xs text-gray-400 mt-1">{entry.notes}</p>}
                  </div>

                  {/* Wait time */}
                  <div className="text-center shrink-0">
                    <p className={`text-xl font-bold ${wait.overdue ? 'text-red-500' : ''}`} style={!wait.overdue ? { color: theme.text } : {}}>
                      {wait.waited}m
                    </p>
                    <p className="text-xs text-gray-400">of {wait.quoted}m</p>
                    <div className="w-16 h-1.5 bg-gray-200 rounded-full mt-1">
                      <div className={`h-full rounded-full transition-all ${wait.overdue ? 'bg-red-500' : 'bg-green-500'}`}
                        style={{ width: `${Math.min(100, (wait.waited / wait.quoted) * 100)}%` }} />
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1 shrink-0">
                    {!isNotified && (
                      <Button variant="outline" size="sm" onClick={() => handleNotify(entry.id)}
                        className="h-8 px-2" data-testid={`notify-btn-${entry.id}`}>
                        <Bell size={14} className="mr-1" /> Notify
                      </Button>
                    )}
                    <Button size="sm" onClick={() => handleSeat(entry.id)}
                      className="h-8 px-3 bg-green-600 hover:bg-green-700 text-white" data-testid={`seat-waitlist-btn-${entry.id}`}>
                      <UserCheck size={14} className="mr-1" /> Seat
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleRemove(entry.id)}
                      className="h-8 px-2 text-red-500 hover:bg-red-50" data-testid={`remove-waitlist-btn-${entry.id}`}>
                      <X size={14} />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Add to waitlist dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md" data-testid="add-waitlist-dialog">
          <DialogHeader>
            <DialogTitle>Add to Waitlist</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Guest Name *</label>
              <Input data-testid="wl-guest-name" value={form.guestName}
                onChange={e => setForm(f => ({ ...f, guestName: e.target.value }))} placeholder="Guest name" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-gray-500 mb-1 block">Phone</label>
                <Input data-testid="wl-guest-phone" value={form.guestPhone}
                  onChange={e => setForm(f => ({ ...f, guestPhone: e.target.value }))} placeholder="+61 400 000 000" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500 mb-1 block">Party Size</label>
                <Input type="number" min={1} max={20} data-testid="wl-party-size" value={form.partySize}
                  onChange={e => setForm(f => ({ ...f, partySize: parseInt(e.target.value) || 1 }))} />
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 mb-2 block">Estimated Wait</label>
              <div className="flex flex-wrap gap-2">
                {WAIT_PRESETS.map(w => (
                  <Button key={w} size="sm" variant={form.quotedWait === w ? 'default' : 'outline'}
                    style={form.quotedWait === w ? { background: theme.primary } : {}}
                    onClick={() => setForm(f => ({ ...f, quotedWait: w }))}
                    data-testid={`wait-preset-${w}`}>
                    {w}m
                  </Button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Seating Preference</label>
              <Select value={form.preferences || 'any'} onValueChange={v => setForm(f => ({ ...f, preferences: v === 'any' ? '' : v }))}>
                <SelectTrigger data-testid="wl-preference-select"><SelectValue placeholder="Any" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="any">Any</SelectItem>
                  <SelectItem value="indoor">Indoor</SelectItem>
                  <SelectItem value="outdoor">Outdoor</SelectItem>
                  <SelectItem value="bar">Bar</SelectItem>
                  <SelectItem value="window">Window</SelectItem>
                  <SelectItem value="booth">Booth</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Notes</label>
              <Input data-testid="wl-notes" value={form.notes}
                onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} placeholder="Special notes..." />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleAdd} style={{ background: theme.primary }} data-testid="confirm-add-waitlist-btn">
              Add to Queue
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
