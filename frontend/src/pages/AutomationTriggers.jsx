import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { Switch } from '../components/ui/switch';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import { useTheme } from '../contexts/ThemeContext';
import { finalizeAPI } from '../services/api';
import { toast } from 'sonner';
import { Zap, Plus, Trash2, Sparkles, Play, Pause, AlertTriangle } from 'lucide-react';

const EVENT_META = {
  low_stock: { label: 'Low stock', color: '#f59e0b', desc: 'Any product falls under threshold' },
  temperature_abnormal: { label: 'Temperature abnormal', color: '#ef4444', desc: 'Fridge/freezer temp out of range' },
  booking_created: { label: 'New booking', color: '#3b82f6', desc: 'A reservation is created' },
  staff_late: { label: 'Staff late', color: '#a855f7', desc: 'A rostered staff member is late' },
  customer_birthday: { label: 'Customer birthday', color: '#ec4899', desc: 'Loyalty guest birthday today' },
  dish_86: { label: 'Dish 86’d', color: '#f97316', desc: 'A menu item is 86’d' },
  high_wait_time: { label: 'High wait time', color: '#eab308', desc: 'Kitchen wait exceeds threshold' },
  no_show: { label: 'No-show', color: '#64748b', desc: 'A booking is marked no-show' },
};

const ACTION_TYPES = [
  { value: 'send_email', label: 'Send email' },
  { value: 'send_sms', label: 'Send SMS' },
  { value: 'dock_notify', label: 'Dock notification' },
  { value: 'dispatch_task', label: 'Dispatch task' },
  { value: 'apply_discount', label: 'Apply discount' },
];

const emptyForm = {
  name: '', event: 'low_stock', conditions: {}, actions: [{ type: 'dock_notify', params: {} }],
  active: true, aiGenerated: false, aiPrompt: '',
};

export default function AutomationTriggers() {
  const { theme } = useTheme();
  const [rows, setRows] = useState([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [aiDialogOpen, setAiDialogOpen] = useState(false);
  const [aiPrompt, setAiPrompt] = useState('');
  const [aiBusy, setAiBusy] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [conditionsJson, setConditionsJson] = useState('{}');

  const load = async () => {
    try { const r = await finalizeAPI.listTriggers(); setRows(r.data || []); }
    catch { toast.error('Failed to load triggers'); }
  };
  useEffect(() => { load(); }, []);

  const openNew = () => {
    setForm(emptyForm);
    setConditionsJson('{}');
    setDialogOpen(true);
  };

  const save = async () => {
    if (!form.name.trim()) return toast.error('Name is required');
    let conds = {};
    try { conds = conditionsJson ? JSON.parse(conditionsJson) : {}; }
    catch { return toast.error('Conditions must be valid JSON'); }
    try {
      await finalizeAPI.createTrigger({ ...form, conditions: conds });
      toast.success('Automation created');
      setDialogOpen(false);
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Failed'); }
  };

  const toggleActive = async (t) => {
    try {
      await finalizeAPI.updateTrigger(t.id, { active: !t.active });
      load();
    } catch { toast.error('Failed'); }
  };

  const remove = async (t) => {
    if (!window.confirm(`Delete "${t.name}"?`)) return;
    try { await finalizeAPI.deleteTrigger(t.id); toast.success('Deleted'); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || 'Failed'); }
  };

  const aiSuggest = async () => {
    if (!aiPrompt.trim()) return toast.error('Describe the automation');
    setAiBusy(true);
    try {
      const r = await finalizeAPI.aiSuggestAutomation(aiPrompt);
      setForm({
        name: r.data.name || 'AI Automation',
        event: r.data.event || 'low_stock',
        conditions: r.data.conditions || {},
        actions: r.data.actions?.length ? r.data.actions : [{ type: 'dock_notify', params: {} }],
        active: true, aiGenerated: true, aiPrompt,
      });
      setConditionsJson(JSON.stringify(r.data.conditions || {}, null, 2));
      setAiDialogOpen(false);
      setDialogOpen(true);
    } catch (e) { toast.error(e?.response?.data?.detail || 'AI suggestion failed'); }
    finally { setAiBusy(false); }
  };

  const addAction = () => setForm(f => ({ ...f, actions: [...f.actions, { type: 'dock_notify', params: {} }] }));
  const updateAction = (i, patch) => setForm(f => ({ ...f, actions: f.actions.map((a, idx) => idx === i ? { ...a, ...patch } : a) }));
  const removeAction = (i) => setForm(f => ({ ...f, actions: f.actions.filter((_, idx) => idx !== i) }));

  return (
    <div className="space-y-6" data-testid="automations-page">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
            <Zap style={{ color: theme.primary }} /> Automation Engine
          </h1>
          <p className="text-sm text-gray-500 mt-1">Create custom triggers that fire on events — with AI-suggested templates.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setAiDialogOpen(true)} data-testid="ai-suggest-btn">
            <Sparkles size={14} className="mr-1.5" /> AI Suggest
          </Button>
          <Button onClick={openNew} style={{ background: theme.primary }} className="text-white" data-testid="new-trigger-btn">
            <Plus size={14} className="mr-1.5" /> New Automation
          </Button>
        </div>
      </div>

      {rows.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="p-12 text-center">
            <Zap size={40} className="mx-auto mb-3 text-gray-300" />
            <p className="text-gray-500 mb-4">No automations yet. Create your first trigger.</p>
            <Button onClick={openNew} style={{ background: theme.primary }} className="text-white" data-testid="empty-new-trigger-btn">
              <Plus size={14} className="mr-1.5" /> New Automation
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="triggers-grid">
          {rows.map(t => {
            const meta = EVENT_META[t.event] || { label: t.event, color: '#64748b', desc: '' };
            return (
              <Card key={t.id} className="border-0 shadow-sm" data-testid={`trigger-card-${t.id}`}>
                <CardContent className="p-5 space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="font-bold text-lg truncate" style={{ color: theme.text }}>{t.name}</h3>
                        {t.aiGenerated && (
                          <Badge className="bg-purple-100 text-purple-700 text-[10px]" data-testid={`ai-badge-${t.id}`}>
                            <Sparkles size={10} className="mr-1" /> AI
                          </Badge>
                        )}
                      </div>
                      <Badge className="text-xs mt-1" style={{ background: `${meta.color}15`, color: meta.color, border: `1px solid ${meta.color}40` }}>
                        {meta.label}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <Switch checked={!!t.active} onCheckedChange={() => toggleActive(t)} data-testid={`toggle-${t.id}`} />
                      <Button variant="ghost" size="sm" onClick={() => remove(t)} className="text-red-500" data-testid={`delete-${t.id}`}>
                        <Trash2 size={14} />
                      </Button>
                    </div>
                  </div>

                  <div className="text-xs text-gray-500">{meta.desc}</div>

                  {t.conditions && Object.keys(t.conditions).length > 0 && (
                    <div className="text-xs bg-gray-50 rounded p-2 border" data-testid={`conditions-${t.id}`}>
                      <p className="text-gray-400 uppercase tracking-widest text-[10px] mb-1">Conditions</p>
                      <pre className="whitespace-pre-wrap font-mono text-[11px]">{JSON.stringify(t.conditions, null, 2)}</pre>
                    </div>
                  )}

                  <div className="space-y-1">
                    <p className="text-gray-400 uppercase tracking-widest text-[10px]">Actions ({(t.actions || []).length})</p>
                    {(t.actions || []).map((a, i) => (
                      <div key={i} className="text-xs flex items-center gap-1.5 bg-blue-50 rounded px-2 py-1 border border-blue-100">
                        <Play size={10} className="text-blue-500" />
                        <span className="font-medium">{a.type}</span>
                        {a.params && Object.keys(a.params).length > 0 && (
                          <span className="text-gray-500 truncate">— {JSON.stringify(a.params)}</span>
                        )}
                      </div>
                    ))}
                  </div>

                  <div className="flex items-center gap-1 text-[10px] text-gray-400">
                    {t.active ? <Play size={10} /> : <Pause size={10} />}
                    <span>{t.active ? 'Active' : 'Paused'}</span>
                    {t.updatedAt && <span>· updated {new Date(t.updatedAt).toLocaleDateString()}</span>}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="trigger-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Zap size={16} /> {form.aiGenerated ? 'AI-generated Automation' : 'New Automation'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            {form.aiGenerated && form.aiPrompt && (
              <div className="text-xs bg-purple-50 border border-purple-100 rounded p-2 flex items-start gap-1.5">
                <Sparkles size={12} className="text-purple-500 shrink-0 mt-0.5" />
                <span className="text-purple-800">AI prompt: &ldquo;{form.aiPrompt}&rdquo;</span>
              </div>
            )}
            <Input placeholder="Automation name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} data-testid="trigger-name" />

            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">When this happens…</label>
              <Select value={form.event} onValueChange={v => setForm({ ...form, event: v })}>
                <SelectTrigger data-testid="trigger-event"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(EVENT_META).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-[11px] text-gray-500 mt-1">{EVENT_META[form.event]?.desc}</p>
            </div>

            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Conditions (JSON — optional)</label>
              <Textarea rows={3} value={conditionsJson} onChange={e => setConditionsJson(e.target.value)}
                placeholder='e.g. {"threshold": 5, "category": "Wine"}' className="font-mono text-xs" data-testid="trigger-conditions" />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-medium text-gray-500">Actions</label>
                <Button size="sm" variant="ghost" onClick={addAction} data-testid="add-action-btn"><Plus size={12} /> Add action</Button>
              </div>
              <div className="space-y-2">
                {form.actions.map((a, i) => (
                  <div key={i} className="border rounded p-2 space-y-2 bg-gray-50/60" data-testid={`action-row-${i}`}>
                    <div className="flex items-center gap-2">
                      <Select value={a.type} onValueChange={v => updateAction(i, { type: v })}>
                        <SelectTrigger className="flex-1" data-testid={`action-type-${i}`}><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {ACTION_TYPES.map(x => <SelectItem key={x.value} value={x.value}>{x.label}</SelectItem>)}
                        </SelectContent>
                      </Select>
                      <Button size="sm" variant="ghost" onClick={() => removeAction(i)} className="text-red-500" data-testid={`remove-action-${i}`}>
                        <Trash2 size={12} />
                      </Button>
                    </div>
                    <Input placeholder='Params JSON e.g. {"template": "low_stock"}'
                      value={JSON.stringify(a.params || {})}
                      onChange={e => {
                        try { updateAction(i, { params: JSON.parse(e.target.value || '{}') }); }
                        catch { /* ignore mid-typing */ }
                      }}
                      className="font-mono text-xs" data-testid={`action-params-${i}`} />
                  </div>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Switch checked={form.active} onCheckedChange={v => setForm({ ...form, active: v })} data-testid="trigger-active" />
              <span className="text-sm text-gray-600">Active on save</span>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button onClick={save} style={{ background: theme.primary }} className="text-white" data-testid="save-trigger-btn">
              Create automation
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* AI Suggest Dialog */}
      <Dialog open={aiDialogOpen} onOpenChange={setAiDialogOpen}>
        <DialogContent className="max-w-md" data-testid="ai-suggest-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles size={16} /> Describe your automation
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <Textarea rows={4} value={aiPrompt} onChange={e => setAiPrompt(e.target.value)}
              placeholder='e.g. "When any wine goes under 3 bottles, alert the manager and email the supplier"'
              data-testid="ai-prompt" />
            <p className="text-[11px] text-gray-500 flex items-start gap-1">
              <AlertTriangle size={11} className="shrink-0 mt-0.5" />
              AI produces a template you can review/edit before saving.
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAiDialogOpen(false)}>Cancel</Button>
            <Button onClick={aiSuggest} disabled={aiBusy} style={{ background: theme.primary }} className="text-white" data-testid="ai-generate-btn">
              {aiBusy ? 'Thinking…' : 'Generate'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
