import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { useToast } from '../hooks/use-toast';
import { useTheme } from '../contexts/ThemeContext';
import { bookingsInboxAPI } from '../services/api';
import { Inbox, MessageSquare, Phone, Mail, AtSign, Globe, User, CheckCircle, X, Sparkles, Plus } from 'lucide-react';

const CHANNEL_META = {
  instagram_dm: { icon: AtSign, label: 'Instagram DM', color: '#ec4899' },
  facebook_dm: { icon: MessageSquare, label: 'Facebook Messenger', color: '#3b82f6' },
  whatsapp: { icon: MessageSquare, label: 'WhatsApp', color: '#22c55e' },
  sms: { icon: MessageSquare, label: 'SMS', color: '#8b5cf6' },
  phone: { icon: Phone, label: 'Phone Call', color: '#f59e0b' },
  email: { icon: Mail, label: 'Email', color: '#6366f1' },
  web_form: { icon: Globe, label: 'Web Form', color: '#0ea5e9' },
  walkin: { icon: User, label: 'Walk-in', color: '#64748b' },
};

export default function BookingsInbox() {
  const { theme } = useTheme();
  const { toast } = useToast();
  const [rows, setRows] = useState([]);
  const [filterStatus, setFilterStatus] = useState('new');
  const [filterChannel, setFilterChannel] = useState('');
  const [composeOpen, setComposeOpen] = useState(false);
  const [draft, setDraft] = useState({ channel: 'phone', fromHandle: '', rawMessage: '' });
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const params = {};
      if (filterStatus) params.status = filterStatus;
      if (filterChannel) params.channel = filterChannel;
      const r = await bookingsInboxAPI.list(params);
      setRows(r.data || []);
    } catch { toast({ title: 'Failed to load inbox', variant: 'destructive' }); }
  };

  useEffect(() => { load(); }, [filterStatus, filterChannel]); // eslint react-hooks/exhaustive-deps: load is stable
  useEffect(() => {
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, [filterStatus, filterChannel]);

  const ingest = async () => {
    if (!draft.rawMessage.trim()) return toast({ title: 'Paste a message first', variant: 'destructive' });
    setBusy(true);
    try {
      await bookingsInboxAPI.ingest(draft);
      toast({ title: 'Captured — AI is parsing' });
      setDraft({ channel: 'phone', fromHandle: '', rawMessage: '' });
      setComposeOpen(false);
      setFilterStatus('new');
      load();
    } catch (e) {
      toast({ title: 'Failed', description: e?.response?.data?.detail, variant: 'destructive' });
    } finally { setBusy(false); }
  };

  const acknowledge = async (item, convert = false) => {
    try {
      await bookingsInboxAPI.ack(item.id, { convertToReservation: convert });
      toast({ title: convert ? 'Reservation booked' : 'Acknowledged' });
      load();
    } catch (e) { toast({ title: 'Failed', description: e?.response?.data?.detail, variant: 'destructive' }); }
  };

  const dismiss = async (item) => {
    try { await bookingsInboxAPI.dismiss(item.id); toast({ title: 'Dismissed' }); load(); }
    catch { toast({ title: 'Failed', variant: 'destructive' }); }
  };

  return (
    <div className="space-y-6" data-testid="bookings-inbox-page">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
          <Inbox style={{ color: theme.primary }} /> AI Bookings Inbox
        </h1>
        <Button onClick={() => setComposeOpen(true)} style={{ background: theme.primary }} className="text-white" data-testid="compose-btn">
          <Plus size={14} className="mr-1.5" /> Capture Inbound
        </Button>
      </div>

      <p className="text-sm text-gray-500 -mt-3">
        Every inbound booking — social DM, phone, email, web form — is parsed by NUA AI then drops here for one-tap acknowledgment.
      </p>

      <div className="flex items-center gap-2 flex-wrap" data-testid="inbox-filters">
        {['new', 'acknowledged', 'converted', 'dismissed', ''].map(s => (
          <button
            key={s}
            onClick={() => setFilterStatus(s)}
            className={`px-3 py-1 text-xs rounded-full font-medium transition-colors ${filterStatus === s ? 'text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
            style={filterStatus === s ? { background: theme.primary } : {}}
            data-testid={`filter-status-${s || 'all'}`}
          >
            {s ? s[0].toUpperCase() + s.slice(1) : 'All'}
          </button>
        ))}
        <span className="text-gray-300 mx-1">·</span>
        <select className="text-xs border rounded px-2 py-1" value={filterChannel} onChange={e => setFilterChannel(e.target.value)} data-testid="filter-channel">
          <option value="">All channels</option>
          {Object.entries(CHANNEL_META).map(([k, v]) => (
            <option key={k} value={k}>{v.label}</option>
          ))}
        </select>
      </div>

      {composeOpen && (
        <Card className="border-amber-300"><CardContent className="p-5 space-y-3" data-testid="compose-card">
          <div className="flex items-center justify-between">
            <p className="font-bold flex items-center gap-1.5"><Sparkles size={14} style={{ color: theme.secondary }} /> Capture inbound message</p>
            <button onClick={() => setComposeOpen(false)} className="text-gray-400 hover:text-red-600"><X size={16} /></button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="text-xs uppercase text-gray-500 mb-1 block">Channel</label>
              <select className="w-full p-2 border rounded text-sm" value={draft.channel} onChange={e => setDraft({ ...draft, channel: e.target.value })} data-testid="compose-channel">
                {Object.entries(CHANNEL_META).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="text-xs uppercase text-gray-500 mb-1 block">From (handle / phone / email)</label>
              <Input value={draft.fromHandle} onChange={e => setDraft({ ...draft, fromHandle: e.target.value })} placeholder="@theirhandle or +61..." data-testid="compose-from" />
            </div>
          </div>
          <div>
            <label className="text-xs uppercase text-gray-500 mb-1 block">Message</label>
            <Textarea
              rows={4}
              value={draft.rawMessage}
              onChange={e => setDraft({ ...draft, rawMessage: e.target.value })}
              placeholder="e.g. 'Hi, want a table for 6 this Saturday at 7:30pm, one vegan'"
              data-testid="compose-message"
            />
          </div>
          <Button onClick={ingest} disabled={busy} style={{ background: theme.primary }} className="text-white" data-testid="compose-ingest">
            {busy ? 'Capturing…' : 'Capture & Parse'}
          </Button>
        </CardContent></Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3" data-testid="inbox-list">
        {rows.length === 0 ? (
          <Card className="lg:col-span-2"><CardContent className="p-12 text-center text-gray-400">
            <Inbox className="mx-auto mb-2" size={40} />
            No messages in this view
          </CardContent></Card>
        ) : rows.map(item => {
          const meta = CHANNEL_META[item.channel] || { icon: MessageSquare, label: item.channel, color: '#64748b' };
          const Icon = meta.icon;
          return (
            <Card key={item.id} className="hover:shadow-md transition-all" data-testid={`inbox-${item.id}`}>
              <CardContent className="p-4 space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <Icon size={14} style={{ color: meta.color }} />
                    <span className="text-xs font-medium" style={{ color: meta.color }}>{meta.label}</span>
                    {item.fromHandle && <span className="text-xs text-gray-500 truncate">{item.fromHandle}</span>}
                  </div>
                  <Badge className={
                    item.status === 'converted' ? 'bg-emerald-100 text-emerald-700' :
                    item.status === 'acknowledged' ? 'bg-blue-100 text-blue-700' :
                    item.status === 'dismissed' ? 'bg-gray-200 text-gray-600' :
                    'bg-amber-100 text-amber-700'
                  } data-testid={`status-${item.id}`}>{item.status}</Badge>
                </div>
                <p className="text-sm text-gray-800 italic line-clamp-2">“{item.rawMessage}”</p>
                {item.aiSummary && (
                  <p className="text-xs text-gray-600 flex items-start gap-1"><Sparkles size={12} className="shrink-0 mt-0.5" style={{ color: theme.secondary }} /> {item.aiSummary}</p>
                )}
                {item.parsed && (
                  <div className="text-xs grid grid-cols-2 gap-1 bg-amber-50/50 rounded p-2 border border-amber-100">
                    {item.parsed.date && <div><span className="text-gray-400">Date:</span> <span className="font-medium">{item.parsed.date}</span></div>}
                    {item.parsed.time && <div><span className="text-gray-400">Time:</span> <span className="font-medium">{item.parsed.time}</span></div>}
                    {item.parsed.partySize && <div><span className="text-gray-400">Party:</span> <span className="font-medium">{item.parsed.partySize}</span></div>}
                    {item.parsed.name && <div><span className="text-gray-400">Name:</span> <span className="font-medium">{item.parsed.name}</span></div>}
                    {item.parsed.phone && <div className="col-span-2"><span className="text-gray-400">Phone:</span> <span className="font-medium">{item.parsed.phone}</span></div>}
                    {item.parsed.notes && <div className="col-span-2"><span className="text-gray-400">Notes:</span> <span className="font-medium">{item.parsed.notes}</span></div>}
                  </div>
                )}
                {item.suggestedReply && (
                  <div className="text-xs bg-gray-50 rounded p-2 border">
                    <p className="text-gray-400 uppercase tracking-widest text-[10px] mb-0.5">Suggested reply</p>
                    <p className="text-gray-700">{item.suggestedReply}</p>
                  </div>
                )}
                {item.status === 'new' && (
                  <div className="flex flex-wrap gap-1 pt-1">
                    <Button size="sm" onClick={() => acknowledge(item, true)} style={{ background: theme.primary }} className="text-white" data-testid={`convert-${item.id}`}>
                      <CheckCircle size={12} className="mr-1" /> Book it
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => acknowledge(item, false)} data-testid={`ack-${item.id}`}>Acknowledge</Button>
                    <Button size="sm" variant="ghost" onClick={() => dismiss(item)} className="text-gray-500" data-testid={`dismiss-${item.id}`}>Dismiss</Button>
                  </div>
                )}
                {item.reservationId && (
                  <p className="text-xs text-emerald-700">→ Reservation {item.reservationId}</p>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
