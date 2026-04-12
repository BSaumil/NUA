import React, { useState, useEffect } from 'react';
import {
  Mail, Send, Plus, Users, Trash2, Clock, CheckCircle, Eye, Edit2
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { useTheme } from '../contexts/ThemeContext';
import { toast } from 'sonner';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;
const authHeader = () => ({ Authorization: `Bearer ${localStorage.getItem('nuva_token')}` });

export default function EmailMarketing() {
  const { theme } = useTheme();
  const [campaigns, setCampaigns] = useState([]);
  const [memberStats, setMemberStats] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', subject: '', body: '', targetTier: '' });

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [camp, stats] = await Promise.all([
        axios.get(`${API}/api/marketing/campaigns`, { headers: authHeader() }),
        axios.get(`${API}/api/members/stats`).catch(() => ({ data: null })),
      ]);
      setCampaigns(camp.data);
      setMemberStats(stats.data);
    } catch {}
  };

  const handleCreate = async () => {
    try {
      await axios.post(`${API}/api/marketing/campaigns`, form, { headers: authHeader() });
      toast.success('Campaign created');
      setShowCreate(false);
      setForm({ name: '', subject: '', body: '', targetTier: '' });
      fetchData();
    } catch (e) { toast.error('Failed to create campaign'); }
  };

  const handleSend = async (id) => {
    try {
      const res = await axios.post(`${API}/api/marketing/campaigns/${id}/send`, {}, { headers: authHeader() });
      toast.success(res.data.message);
      fetchData();
    } catch { toast.error('Failed to send'); }
  };

  const handleDelete = async (id) => {
    try {
      await axios.delete(`${API}/api/marketing/campaigns/${id}`, { headers: authHeader() });
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
        <Button onClick={() => setShowCreate(true)} style={{ backgroundColor: theme.primary }}
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
        <DialogContent className="max-w-md" data-testid="create-campaign-dialog">
          <DialogHeader><DialogTitle>New Email Campaign</DialogTitle></DialogHeader>
          <div className="space-y-3 py-2">
            <Input placeholder="Campaign name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} data-testid="campaign-name" />
            <Input placeholder="Email subject line" value={form.subject} onChange={e => setForm({ ...form, subject: e.target.value })} data-testid="campaign-subject" />
            <textarea className="w-full min-h-[120px] p-3 border rounded-md text-sm resize-none" placeholder="Email body (supports HTML)..."
              value={form.body} onChange={e => setForm({ ...form, body: e.target.value })} data-testid="campaign-body" />
            <select className="w-full p-2 border rounded-md text-sm" value={form.targetTier}
              onChange={e => setForm({ ...form, targetTier: e.target.value })} data-testid="campaign-tier">
              <option value="">All Members</option>
              <option value="Bronze">Bronze Only</option>
              <option value="Silver">Silver Only</option>
              <option value="Gold">Gold Only</option>
              <option value="Platinum">Platinum Only</option>
            </select>
            <Button className="w-full" style={{ backgroundColor: theme.primary }} onClick={handleCreate}
              data-testid="confirm-create-campaign">Create Campaign</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
