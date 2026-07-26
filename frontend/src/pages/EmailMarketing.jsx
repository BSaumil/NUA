import React, { useState, useEffect } from 'react';
import {
  Mail, Send, Plus, Users, Trash2, Clock, CheckCircle, Edit2, Sparkles, Ticket, Wand2, LayoutTemplate
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { useTheme } from '../contexts/ThemeContext';
import { toast } from 'sonner';
import { advancedAPI } from '../services/api';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;
const authHeader = () => ({ Authorization: `Bearer ${localStorage.getItem('nuva_token')}` });

const EMPTY_FORM = {
  name: '', subject: '', body: '', targetTier: '',
  voucherEnabled: false, voucherValueType: 'percent', voucherValue: 15,
  voucherExpiresInDays: 30, voucherMinSpend: 0,
};

export default function EmailMarketing() {
  const { theme } = useTheme();
  const [campaigns, setCampaigns] = useState([]);
  const [memberStats, setMemberStats] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [brief, setBrief] = useState('');
  const [drafting, setDrafting] = useState(false);
  const [improving, setImproving] = useState(false);
  const [creating, setCreating] = useState(false);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [camp, stats] = await Promise.all([
        advancedAPI.getCampaigns(),
        axios.get(`${API}/api/members/stats`, { headers: authHeader() }).catch(() => ({ data: null })),
      ]);
      setCampaigns(camp.data);
      setMemberStats(stats.data);
    } catch {}
  };

  const openCreate = async () => {
    setForm(EMPTY_FORM);
    setBrief('');
    setShowCreate(true);
    if (templates.length === 0) {
      try {
        const r = await advancedAPI.getCampaignTemplates();
        setTemplates(r.data || []);
      } catch {}
    }
  };

  const applyTemplate = (t) => {
    setForm(f => ({ ...f, name: t.label, subject: t.subject, body: t.body, targetTier: t.targetTier || f.targetTier }));
  };

  const handleAiDraft = async () => {
    setDrafting(true);
    try {
      const r = await advancedAPI.draftCampaign({ brief, targetTier: form.targetTier });
      setForm(f => ({ ...f, name: r.data.name || f.name, subject: r.data.subject || f.subject, body: r.data.body || f.body }));
      toast.success('AI draft ready — review and tweak before sending');
    } catch { toast.error('Could not generate a draft'); }
    finally { setDrafting(false); }
  };

  const handleImproveWording = async () => {
    if (!form.body) { toast.error('Write or generate a draft first'); return; }
    setImproving(true);
    try {
      const r = await advancedAPI.improveCampaignCopy({ subject: form.subject, body: form.body });
      setForm(f => ({ ...f, subject: r.data.subject || f.subject, body: r.data.body || f.body }));
      toast.success('Wording improved');
    } catch { toast.error('Could not improve wording'); }
    finally { setImproving(false); }
  };

  const handleCreate = async () => {
    setCreating(true);
    try {
      await advancedAPI.createCampaign({
        name: form.name, subject: form.subject, body: form.body, targetTier: form.targetTier,
        voucher: form.voucherEnabled ? {
          enabled: true, valueType: form.voucherValueType, value: Number(form.voucherValue) || 0,
          expiresInDays: Number(form.voucherExpiresInDays) || 30, minSpend: Number(form.voucherMinSpend) || 0,
        } : undefined,
      });
      toast.success('Campaign created');
      setShowCreate(false);
      setForm(EMPTY_FORM);
      fetchData();
    } catch (e) { toast.error('Failed to create campaign'); }
    finally { setCreating(false); }
  };

  const handleSend = async (id) => {
    try {
      const res = await advancedAPI.sendCampaign(id);
      toast.success(res.data.message);
      fetchData();
    } catch { toast.error('Failed to send'); }
  };

  const handleDelete = async (id) => {
    try {
      await advancedAPI.deleteCampaign(id);
      toast.success('Campaign deleted');
      fetchData();
    } catch {}
  };

  return (
    <div data-testid="email-marketing-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold" style={{ color: theme.text }}>Email Marketing</h1>
          <p className="text-gray-500 mt-1">
            {memberStats?.totalMembers || 0} members &middot; {campaigns.length} campaigns
          </p>
        </div>
        <Button onClick={openCreate} style={{ backgroundColor: theme.primary }}
          data-testid="create-campaign-btn">
          <Plus size={18} className="mr-1" /> New Campaign
        </Button>
      </div>

      {/* Stats */}
      {memberStats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <Card><CardContent className="p-4 text-center">
            <p className="text-sm text-gray-500">Total Members</p>
            <p className="text-2xl font-bold" style={{ color: theme.primary }}>{memberStats.totalMembers}</p>
          </CardContent></Card>
          <Card><CardContent className="p-4 text-center">
            <p className="text-sm text-gray-500">Avg Spend</p>
            <p className="text-2xl font-bold text-emerald-600">${memberStats.avgSpend}</p>
          </CardContent></Card>
          <Card><CardContent className="p-4 text-center">
            <p className="text-sm text-gray-500">Campaigns Sent</p>
            <p className="text-2xl font-bold text-blue-600">{campaigns.filter(c => c.status === 'sent').length}</p>
          </CardContent></Card>
          <Card><CardContent className="p-4 text-center">
            <p className="text-sm text-gray-500">Total Spent</p>
            <p className="text-2xl font-bold text-amber-600">${memberStats.totalSpent}</p>
          </CardContent></Card>
        </div>
      )}

      {/* Campaigns List */}
      <div className="space-y-3">
        {campaigns.map(c => (
          <Card key={c.id} data-testid={`campaign-${c.id}`}>
            <CardContent className="p-5">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">{c.name}</h3>
                    <Badge className={c.status === 'sent' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}>
                      {c.status === 'sent' ? <><CheckCircle size={12} className="mr-0.5" /> Sent</> : <><Edit2 size={12} className="mr-0.5" /> Draft</>}
                    </Badge>
                    {c.targetTier && <Badge variant="outline">{c.targetTier} tier</Badge>}
                    {c.voucherCode && (
                      <Badge className="bg-amber-100 text-amber-700" data-testid={`campaign-voucher-${c.id}`}>
                        <Ticket size={12} className="mr-1" /> {c.voucherCode}
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm text-gray-500 mt-1">Subject: {c.subject}</p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    <Users size={12} className="inline mr-1" />{c.recipientCount} recipients
                    {c.sentAt && <> &middot; <Clock size={12} className="inline mx-1" />Sent {new Date(c.sentAt).toLocaleDateString()}</>}
                  </p>
                </div>
                <div className="flex gap-2">
                  {c.status === 'draft' && (
                    <Button size="sm" onClick={() => handleSend(c.id)} style={{ backgroundColor: theme.primary }}
                      data-testid={`send-${c.id}`}>
                      <Send size={14} className="mr-1" /> Send
                    </Button>
                  )}
                  <Button size="sm" variant="ghost" className="text-red-500" onClick={() => handleDelete(c.id)}>
                    <Trash2 size={14} />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
        {campaigns.length === 0 && (
          <Card className="border-dashed"><CardContent className="p-12 text-center">
            <Mail size={48} className="mx-auto mb-4 text-gray-300" />
            <h3 className="font-semibold text-gray-700">No campaigns yet</h3>
            <p className="text-sm text-gray-500 mt-1">Create your first email campaign to engage members</p>
          </CardContent></Card>
        )}
      </div>

      {/* Create Dialog */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto" data-testid="create-campaign-dialog">
          <DialogHeader><DialogTitle>New Email Campaign</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">

            {/* Predrafted templates */}
            {templates.length > 0 && (
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-1.5 flex items-center gap-1">
                  <LayoutTemplate size={12} /> Start from a template
                </p>
                <div className="flex gap-1.5 overflow-x-auto pb-1" data-testid="campaign-templates">
                  {templates.map(t => (
                    <button key={t.key} onClick={() => applyTemplate(t)} data-testid={`template-${t.key}`}
                      className="shrink-0 text-xs px-2.5 py-1.5 rounded-full border hover:bg-amber-50 hover:border-amber-300 transition whitespace-nowrap">
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* AI draft-from-brief */}
            <div className="rounded-lg border border-violet-200 bg-violet-50/60 p-3 space-y-2">
              <p className="text-xs font-bold uppercase tracking-wider text-violet-700 flex items-center gap-1">
                <Sparkles size={12} /> AI draft
              </p>
              <div className="flex gap-2">
                <Input value={brief} onChange={e => setBrief(e.target.value)}
                  placeholder="e.g. promote our new summer menu to Gold members" className="text-sm" data-testid="campaign-brief" />
                <Button size="sm" onClick={handleAiDraft} disabled={drafting} className="bg-violet-600 hover:bg-violet-700 text-white shrink-0" data-testid="ai-draft-btn">
                  {drafting ? '…' : 'Generate'}
                </Button>
              </div>
              <p className="text-[11px] text-violet-600/80">Describe the offer in plain English, or just pick a template above — NUA writes the subject + body for you.</p>
            </div>

            <Input placeholder="Campaign name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} data-testid="campaign-name" />
            <Input placeholder="Email subject line" value={form.subject} onChange={e => setForm({ ...form, subject: e.target.value })} data-testid="campaign-subject" />

            <div>
              <textarea className="w-full min-h-[140px] p-3 border rounded-md text-sm resize-none" placeholder="Email body (supports HTML)..."
                value={form.body} onChange={e => setForm({ ...form, body: e.target.value })} data-testid="campaign-body" />
              <Button size="sm" variant="outline" className="mt-1.5" onClick={handleImproveWording} disabled={improving || !form.body} data-testid="improve-wording-btn">
                <Wand2 size={14} className="mr-1" /> {improving ? 'Improving…' : 'Improve wording with AI'}
              </Button>
            </div>

            <select className="w-full p-2 border rounded-md text-sm" value={form.targetTier}
              onChange={e => setForm({ ...form, targetTier: e.target.value })} data-testid="campaign-tier">
              <option value="">All Members</option>
              <option value="Bronze">Bronze Only</option>
              <option value="Silver">Silver Only</option>
              <option value="Gold">Gold Only</option>
              <option value="Platinum">Platinum Only</option>
            </select>

            {/* Voucher code */}
            <div className="rounded-lg border border-amber-200 bg-amber-50/60 p-3 space-y-2">
              <label className="flex items-center gap-2 text-sm font-semibold text-amber-800">
                <input type="checkbox" checked={form.voucherEnabled}
                  onChange={e => setForm({ ...form, voucherEnabled: e.target.checked })} data-testid="voucher-enable-toggle" />
                <Ticket size={14} /> Attach a redeemable voucher code to this email
              </label>
              {form.voucherEnabled && (
                <div className="grid grid-cols-2 gap-2 pt-1">
                  <select className="p-2 border rounded-md text-sm" value={form.voucherValueType}
                    onChange={e => setForm({ ...form, voucherValueType: e.target.value })} data-testid="voucher-value-type">
                    <option value="percent">% off</option>
                    <option value="fixed">$ off</option>
                  </select>
                  <Input type="number" placeholder="Value" value={form.voucherValue}
                    onChange={e => setForm({ ...form, voucherValue: e.target.value })} data-testid="voucher-value" />
                  <Input type="number" placeholder="Expires in (days)" value={form.voucherExpiresInDays}
                    onChange={e => setForm({ ...form, voucherExpiresInDays: e.target.value })} data-testid="voucher-expires" />
                  <Input type="number" placeholder="Min spend ($, optional)" value={form.voucherMinSpend}
                    onChange={e => setForm({ ...form, voucherMinSpend: e.target.value })} data-testid="voucher-min-spend" />
                  <p className="col-span-2 text-[11px] text-amber-700/80">
                    One shared code goes out with every email in this campaign. Staff can type it, scan it, or ask NUA to check it — redemption happens right at POS like any other voucher.
                  </p>
                </div>
              )}
            </div>

            <Button className="w-full" style={{ backgroundColor: theme.primary }} onClick={handleCreate} disabled={creating}
              data-testid="confirm-create-campaign">{creating ? 'Creating…' : 'Create Campaign'}</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
