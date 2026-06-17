import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { useToast } from '../../hooks/use-toast';
import { useTheme } from '../../contexts/ThemeContext';
import { v26API } from '../../services/api';
import { Sparkles, Save, Trash2 } from 'lucide-react';

export default function MarketingEmails() {
  const { theme } = useTheme(); const { toast } = useToast();
  const [rows, setRows] = useState([]);
  const [generating, setGenerating] = useState(false);
  const [form, setForm] = useState({ audience: 'all', tone: 'friendly', horizonDays: 14 });
  const [opened, setOpened] = useState(null);

  const load = () => v26API.listMarketingEmails().then(r => setRows(r.data || []));
  useEffect(() => { load(); }, []);

  const generate = async () => {
    setGenerating(true);
    try {
      const r = await v26API.generateMarketingEmail(form);
      setOpened(r.data);
      toast({ title: 'Draft generated', description: r.data?.subject || 'Ready to review' });
      load();
    } catch (e) {
      toast({ title: 'Generation failed', description: e?.response?.data?.detail, variant: 'destructive' });
    } finally { setGenerating(false); }
  };

  const save = async () => {
    try {
      await v26API.updateMarketingEmail(opened.id, opened);
      toast({ title: 'Saved' }); load();
    } catch { toast({ title: 'Save failed', variant: 'destructive' }); }
  };

  const remove = async (id) => {
    if (!window.confirm('Delete this draft?')) return;
    await v26API.deleteMarketingEmail(id);
    if (opened?.id === id) setOpened(null);
    load();
  };

  return (
    <div className="space-y-6" data-testid="marketing-emails-page">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
          <Sparkles className="text-purple-600" /> AI Marketing Emails
        </h1>
      </div>

      <Card><CardContent className="p-5 space-y-3" data-testid="generate-email-form">
        <p className="text-sm text-gray-600">Generate an email featuring upcoming events, active vouchers and tier perks.</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div><label className="text-xs uppercase text-gray-500">Audience</label>
            <select className="w-full p-2 border rounded text-sm" value={form.audience} onChange={e => setForm({ ...form, audience: e.target.value })} data-testid="mkt-audience">
              <option value="all">All customers</option>
              <option value="tier:Gold">Tier · Gold</option>
              <option value="tier:Silver">Tier · Silver</option>
              <option value="tier:Bronze">Tier · Bronze</option>
              <option value="segment:lapsed">Lapsed (30d+)</option>
              <option value="segment:new">New (≤14d)</option>
            </select></div>
          <div><label className="text-xs uppercase text-gray-500">Tone</label>
            <select className="w-full p-2 border rounded text-sm" value={form.tone} onChange={e => setForm({ ...form, tone: e.target.value })} data-testid="mkt-tone">
              <option value="friendly">Friendly</option><option value="elegant">Elegant</option>
              <option value="urgent">Urgent</option><option value="playful">Playful</option>
            </select></div>
          <div><label className="text-xs uppercase text-gray-500">Horizon (days)</label>
            <Input type="number" value={form.horizonDays} onChange={e => setForm({ ...form, horizonDays: parseInt(e.target.value) || 14 })} data-testid="mkt-horizon" /></div>
        </div>
        <Button onClick={generate} disabled={generating} style={{ background: theme.primary }} data-testid="generate-email-btn">
          {generating ? 'Generating…' : <><Sparkles size={14} className="mr-1.5" /> Generate Draft</>}
        </Button>
      </CardContent></Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-1"><CardContent className="p-0">
          <div className="px-4 py-3 border-b font-bold text-sm">Drafts ({rows.length})</div>
          <div className="max-h-[60vh] overflow-y-auto">
            {rows.length === 0 ? <p className="text-center text-gray-400 py-8 text-sm">No drafts yet</p> :
              rows.map(m => (
                <button key={m.id} onClick={() => setOpened(m)} className={`w-full text-left px-4 py-3 border-b hover:bg-gray-50 ${opened?.id === m.id ? 'bg-purple-50' : ''}`} data-testid={`email-row-${m.id}`}>
                  <p className="font-medium text-sm truncate">{m.subject || '(no subject)'}</p>
                  <p className="text-xs text-gray-500 truncate">{m.audience} · {m.tone}</p>
                  <p className="text-[10px] text-gray-400 mt-1">{new Date(m.createdAt).toLocaleString()}</p>
                </button>
              ))}
          </div>
        </CardContent></Card>

        <Card className="lg:col-span-2"><CardContent className="p-5">
          {!opened ? <p className="text-center text-gray-400 py-12">Pick a draft or generate a new one</p> : (
            <div className="space-y-3" data-testid="email-editor">
              <div><label className="text-xs uppercase text-gray-500">Subject</label>
                <Input value={opened.subject || ''} onChange={e => setOpened({ ...opened, subject: e.target.value })} data-testid="mkt-subject" /></div>
              <div><label className="text-xs uppercase text-gray-500">Preheader</label>
                <Input value={opened.preheader || ''} onChange={e => setOpened({ ...opened, preheader: e.target.value })} /></div>
              <div><label className="text-xs uppercase text-gray-500">Body</label>
                <Textarea rows={10} value={opened.emailBody || ''} onChange={e => setOpened({ ...opened, emailBody: e.target.value })} data-testid="mkt-body" /></div>
              <div><label className="text-xs uppercase text-gray-500">SMS Version</label>
                <Textarea rows={2} value={opened.sms || ''} onChange={e => setOpened({ ...opened, sms: e.target.value })} /></div>
              <div><label className="text-xs uppercase text-gray-500">CTA Label</label>
                <Input value={opened.cta || ''} onChange={e => setOpened({ ...opened, cta: e.target.value })} /></div>
              {opened.highlights && opened.highlights.length > 0 && (
                <div className="bg-purple-50 border border-purple-200 rounded p-3 text-xs">
                  <p className="font-bold uppercase tracking-widest text-purple-700 mb-1">Highlights</p>
                  <ul>{opened.highlights.map((h, i) => <li key={i}>· {h}</li>)}</ul>
                </div>
              )}
              <div className="flex gap-2">
                <Button onClick={save} style={{ background: theme.primary }} data-testid="save-email-btn"><Save size={14} className="mr-1.5" /> Save</Button>
                <Button variant="outline" onClick={() => remove(opened.id)} className="text-red-600" data-testid="delete-email-btn"><Trash2 size={14} className="mr-1.5" /> Delete</Button>
                <Button variant="ghost" onClick={() => setOpened(null)}>Close</Button>
              </div>
            </div>
          )}
        </CardContent></Card>
      </div>
    </div>
  );
}
