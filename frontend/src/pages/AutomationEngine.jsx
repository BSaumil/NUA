import React, { useState, useEffect, useCallback } from 'react';
import {
  Zap, Plus, Trash2, Power, PowerOff, AlertTriangle, Package,
  ChefHat, Users, DollarSign, Bell, Settings, ArrowRight, Activity
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
import { Switch } from '../components/ui/switch';
import { useTheme } from '../contexts/ThemeContext';
import { automationAPI } from '../services/api';
import { toast } from 'sonner';

const TRIGGER_OPTIONS = [
  { value: 'low_stock', label: 'Low Stock Alert', icon: Package, color: '#F59E0B' },
  { value: 'kitchen_backlog', label: 'Kitchen Backlog', icon: ChefHat, color: '#EF4444' },
  { value: 'no_show_pattern', label: 'Frequent No-Show', icon: Users, color: '#8B5CF6' },
  { value: 'margin_drop', label: 'Margin Drop', icon: DollarSign, color: '#EC4899' },
  { value: 'busy_period', label: 'Busy Period', icon: Activity, color: '#3B82F6' },
  { value: 'wastage_spike', label: 'Wastage Spike', icon: AlertTriangle, color: '#EF4444' },
];

const ACTION_OPTIONS = [
  { value: 'create_purchase_order', label: 'Create Purchase Order' },
  { value: 'notify_manager', label: 'Notify Manager' },
  { value: 'flag_customer', label: 'Flag Customer' },
  { value: 'adjust_pricing', label: 'Suggest Price Adjustment' },
  { value: 'increase_staff', label: 'Suggest Staff Increase' },
  { value: 'send_alert', label: 'Send Alert' },
];

const SEVERITY_CONFIG = {
  high: { color: '#EF4444', bg: '#FEF2F2' },
  warning: { color: '#F59E0B', bg: '#FFFBEB' },
  info: { color: '#3B82F6', bg: '#EFF6FF' },
};

export default function AutomationEngine() {
  const { theme } = useTheme();
  const [rules, setRules] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [ruleForm, setRuleForm] = useState({ name: '', trigger: '', condition: '', action: '' });

  const fetchData = useCallback(async () => {
    try {
      const [rulesRes, alertsRes] = await Promise.all([
        automationAPI.getRules(),
        automationAPI.getAlerts(),
      ]);
      setRules(rulesRes.data);
      setAlerts(alertsRes.data);
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleCreateRule = async () => {
    if (!ruleForm.name || !ruleForm.trigger || !ruleForm.action) {
      toast.error('Name, trigger, and action are required'); return;
    }
    try {
      await automationAPI.createRule(ruleForm);
      toast.success('Automation rule created');
      setDialogOpen(false);
      setRuleForm({ name: '', trigger: '', condition: '', action: '' });
      fetchData();
    } catch (e) { toast.error('Failed'); }
  };

  const handleToggle = async (id) => {
    try {
      await automationAPI.toggleRule(id);
      fetchData();
    } catch (e) { toast.error('Failed'); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this rule?')) return;
    try { await automationAPI.deleteRule(id); fetchData(); }
    catch (e) { toast.error('Failed'); }
  };

  return (
    <div className="space-y-6" data-testid="automation-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #F59E0B, #EF4444)' }}>
            <Zap size={24} className="text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold" style={{ color: theme.text }}>Automation Engine</h1>
            <p className="text-sm text-gray-500">Live threshold alerts, plus a reference checklist of rules to action manually</p>
          </div>
        </div>
        <Button onClick={() => setDialogOpen(true)} style={{ background: theme.primary }} data-testid="create-rule-btn">
          <Plus size={16} className="mr-1" /> New Rule
        </Button>
      </div>

      {/* Live Alerts */}
      {alerts.length > 0 && (
        <Card className="border-0 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Bell size={16} className="text-red-500 animate-pulse" />
              Live Alerts ({alerts.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {alerts.map((alert, i) => {
              const sev = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.info;
              const triggerConfig = TRIGGER_OPTIONS.find(t => t.value === alert.type);
              const Icon = triggerConfig?.icon || AlertTriangle;
              return (
                <div key={i} className="flex items-start gap-3 p-3 rounded-lg" style={{ background: sev.bg }}
                  data-testid={`alert-${i}`}>
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ background: `${sev.color}20` }}>
                    <Icon size={16} style={{ color: sev.color }} />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold" style={{ color: theme.text }}>{alert.title}</p>
                      <Badge style={{ background: `${sev.color}20`, color: sev.color }} className="text-[10px]">{alert.severity}</Badge>
                    </div>
                    <p className="text-xs text-gray-600 mt-0.5">{alert.message}</p>
                  </div>
                  {alert.action && (
                    <Badge variant="outline" className="text-[10px] shrink-0 capitalize">
                      {alert.action.replace(/_/g, ' ')}
                    </Badge>
                  )}
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}

      {/* Automation Rules — these are saved as a reference checklist only;
          see the note below for why (nothing here auto-fires). Live Alerts
          above IS real — recomputed from current data on every load. */}
      <Card className="border-0 shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Settings size={16} style={{ color: theme.primary }} /> Automation Rules
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-start gap-2 text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4" data-testid="rules-not-live-notice">
            <AlertTriangle size={14} className="mt-0.5 flex-shrink-0" />
            <p>
              Rules saved here are a reference checklist, not live automation — nothing
              executes automatically when a condition is met. For rules that actually
              fire on real events (sales, refunds, bookings, inventory), use{' '}
              <a href="/automation-triggers" className="underline font-medium">Automation Brain</a> instead.
            </p>
          </div>
          {rules.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <Zap size={40} className="mx-auto mb-3 opacity-30" />
              <p className="font-medium">No rules saved yet</p>
              <p className="text-xs mt-1">Save a reference checklist of conditions worth watching for</p>
            </div>
          ) : (
            <div className="space-y-3">
              {rules.map(rule => {
                const triggerConfig = TRIGGER_OPTIONS.find(t => t.value === rule.trigger);
                const Icon = triggerConfig?.icon || Zap;
                return (
                  <div key={rule.id} className={`flex items-center gap-4 p-4 rounded-lg border transition-all ${rule.enabled ? 'bg-white' : 'bg-gray-50 opacity-60'}`}
                    data-testid={`rule-${rule.id}`}>
                    <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: `${triggerConfig?.color || theme.primary}15` }}>
                      <Icon size={18} style={{ color: triggerConfig?.color || theme.primary }} />
                    </div>
                    <div className="flex-1">
                      <p className="font-medium" style={{ color: theme.text }}>{rule.name}</p>
                      <div className="flex items-center gap-2 text-xs text-gray-500 mt-0.5">
                        <Badge variant="outline" className="text-[10px] capitalize">{rule.trigger?.replace(/_/g, ' ')}</Badge>
                        <ArrowRight size={10} />
                        <Badge variant="outline" className="text-[10px] capitalize">{rule.action?.replace(/_/g, ' ')}</Badge>
                        {rule.condition && <span className="ml-1 italic">when: {rule.condition}</span>}
                      </div>
                    </div>
                    {rule.triggerCount > 0 && (
                      <Badge variant="outline" className="text-xs">{rule.triggerCount}x triggered</Badge>
                    )}
                    <Switch checked={rule.enabled} onCheckedChange={() => handleToggle(rule.id)}
                      data-testid={`toggle-rule-${rule.id}`} />
                    <Button variant="ghost" size="sm" className="text-red-400 hover:text-red-600 h-8 px-2"
                      onClick={() => handleDelete(rule.id)} data-testid={`delete-rule-${rule.id}`}>
                      <Trash2 size={14} />
                    </Button>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Rule Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md" data-testid="create-rule-dialog">
          <DialogHeader>
            <DialogTitle>Create Automation Rule</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Rule Name *</label>
              <Input data-testid="rule-name-input" value={ruleForm.name}
                onChange={e => setRuleForm(f => ({ ...f, name: e.target.value }))}
                placeholder="e.g., Auto-reorder coffee beans" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 mb-2 block">When this happens (Trigger) *</label>
              <div className="grid grid-cols-2 gap-2">
                {TRIGGER_OPTIONS.map(t => {
                  const Icon = t.icon;
                  const selected = ruleForm.trigger === t.value;
                  return (
                    <button key={t.value}
                      className={`flex items-center gap-2 p-2.5 rounded-lg border text-left text-xs transition-all ${selected ? 'ring-2' : 'hover:bg-gray-50'}`}
                      style={selected ? { borderColor: t.color, background: `${t.color}08`, ringColor: t.color } : {}}
                      onClick={() => setRuleForm(f => ({ ...f, trigger: t.value }))}
                      data-testid={`trigger-${t.value}`}>
                      <Icon size={14} style={{ color: t.color }} />
                      <span className="font-medium">{t.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Condition (optional)</label>
              <Input value={ruleForm.condition}
                onChange={e => setRuleForm(f => ({ ...f, condition: e.target.value }))}
                placeholder="e.g., stock < 5, backlog > 10" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Then do this (Action) *</label>
              <Select value={ruleForm.action} onValueChange={v => setRuleForm(f => ({ ...f, action: v }))}>
                <SelectTrigger data-testid="action-select"><SelectValue placeholder="Select action" /></SelectTrigger>
                <SelectContent>
                  {ACTION_OPTIONS.map(a => <SelectItem key={a.value} value={a.value}>{a.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleCreateRule} style={{ background: theme.primary }} data-testid="save-rule-btn">Create Rule</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
