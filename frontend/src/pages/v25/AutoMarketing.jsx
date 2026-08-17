import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { v25API } from '../../services/api';
import { useTheme } from '../../contexts/ThemeContext';
import { useToast } from '../../hooks/use-toast';
import { Sparkles, Send, Pause, Play, Pencil, CheckCircle2 } from 'lucide-react';

const STATUS_STYLE = {
  draft: { label: 'Draft — needs review', className: 'bg-amber-100 text-amber-700' },
  held: { label: 'On hold', className: 'bg-slate-200 text-slate-600' },
  sent: { label: 'Sent', className: 'bg-emerald-100 text-emerald-700' },
};

export default function AutoMarketing() {
  const { theme } = useTheme(); const { toast } = useToast();
  const [campaigns, setCampaigns] = useState([]);
  const [running, setRunning] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [editing, setEditing] = useState(null); // campaign being edited before send
  const [editForm, setEditForm] = useState({ emailSubject: '', emailBody: '', sms: '' });

  const load = () => v25API.listMarketing().then(r => setCampaigns(r.data || []));
  useEffect(() => { load(); }, []);

  const run = async (aud) => {
    setRunning(true);
    try { await v25API.autoMarketing(aud); toast({ title: 'Campaign drafted — review it before sending' }); await load(); }
    catch { toast({ title: 'Error', variant: 'destructive' }); }
    finally { setRunning(false); }
  };

  const send = async (c, edits) => {
    setBusyId(c.id);
    try {
      const r = await v25API.sendMarketing(c.id, edits);
      toast({ title: `Sent to ${r.data.recipients} customers`, description: `${r.data.vouchersIssued} vouchers issued · ${r.data.emailsDelivered} emails delivered` });
      setEditing(null);
      await load();
    } catch (e) {
      toast({ title: e.response?.data?.detail || 'Send failed', variant: 'destructive' });
    } finally { setBusyId(null); }
  };

  const toggleHold = async (c) => {
    setBusyId(c.id);
    try {
      await v25API.holdMarketing(c.id, c.status !== 'held');
      toast({ title: c.status === 'held' ? 'Taken off hold' : 'Put on hold' });
      await load();
    } catch { toast({ title: 'Error', variant: 'destructive' }); }
    finally { setBusyId(null); }
  };

  const openEdit = (c) => {
    setEditForm({ emailSubject: c.emailSubject || '', emailBody: c.emailBody || '', sms: c.sms || '' });
    setEditing(c);
  };

  return (
    <div className="space-y-6" data-testid="auto-marketing-page">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Sparkles className="text-pink-600" /> Autonomous Marketing</h1>
        <p className="text-sm text-gray-500 mt-1">AI drafts a promotional email + SMS. Nothing goes to a customer until you Send it — hold it back or edit the copy first if you want.</p>
      </div>
      <div className="flex gap-2 flex-wrap">
        {['all', 'VIP', 'Gold', 'Silver'].map(a => (
          <Button key={a} onClick={() => run(a)} disabled={running} variant="outline" data-testid={`run-${a}`}>{running ? 'Drafting…' : `Run for ${a}`}</Button>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="campaigns-list">
        {campaigns.map(c => {
          const status = STATUS_STYLE[c.status] || STATUS_STYLE.draft;
          const busy = busyId === c.id;
          return (
            <Card key={c.id} data-testid={`campaign-${c.id}`}>
              <CardContent className="p-5">
                <div className="flex items-center justify-between mb-2 gap-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{c.audience}</Badge>
                    <Badge className={`text-[10px] ${status.className}`} data-testid={`campaign-status-${c.id}`}>{status.label}</Badge>
                  </div>
                  <span className="text-xs text-gray-500">{c.recipients ?? c.sent ?? 0} recipients</span>
                </div>
                <p className="font-semibold">{c.emailSubject}</p>
                <p className="text-sm text-gray-600 mt-1">{c.emailBody}</p>
                <p className="text-xs text-gray-500 mt-2 italic">SMS: {c.sms}</p>

                {c.status === 'sent' ? (
                  <div className="mt-3 flex items-center gap-1.5 text-xs text-emerald-700">
                    <CheckCircle2 size={13} /> {c.vouchersIssued || 0} vouchers issued · {c.sent || 0} delivered
                  </div>
                ) : (
                  <div className="mt-3 flex gap-2">
                    <Button size="sm" style={{ backgroundColor: theme.primary }} disabled={busy || c.status === 'held'}
                      onClick={() => send(c, null)} data-testid={`send-${c.id}`}>
                      <Send size={13} className="mr-1" /> Send
                    </Button>
                    <Button size="sm" variant="outline" disabled={busy} onClick={() => openEdit(c)} data-testid={`edit-${c.id}`}>
                      <Pencil size={13} className="mr-1" /> Edit
                    </Button>
                    <Button size="sm" variant="outline" disabled={busy} onClick={() => toggleHold(c)} data-testid={`hold-${c.id}`}>
                      {c.status === 'held' ? <><Play size={13} className="mr-1" /> Take off hold</> : <><Pause size={13} className="mr-1" /> Hold</>}
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
        {campaigns.length === 0 && (
          <p className="text-sm text-gray-400 col-span-full text-center py-10">No campaigns yet — run one above.</p>
        )}
      </div>

      <Dialog open={!!editing} onOpenChange={o => !o && setEditing(null)}>
        <DialogContent data-testid="campaign-edit-dialog">
          <DialogHeader><DialogTitle>Edit before sending</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Email subject</label>
              <Input value={editForm.emailSubject} onChange={e => setEditForm({ ...editForm, emailSubject: e.target.value })} data-testid="edit-email-subject" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Email body</label>
              <Textarea rows={5} value={editForm.emailBody} onChange={e => setEditForm({ ...editForm, emailBody: e.target.value })} data-testid="edit-email-body" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">SMS</label>
              <Textarea rows={2} value={editForm.sms} onChange={e => setEditForm({ ...editForm, sms: e.target.value })} data-testid="edit-sms" />
            </div>
            <Button className="w-full" style={{ backgroundColor: theme.primary }} disabled={busyId === editing?.id}
              onClick={() => send(editing, editForm)} data-testid="edit-send-btn">
              <Send size={14} className="mr-1.5" /> Save & Send
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
