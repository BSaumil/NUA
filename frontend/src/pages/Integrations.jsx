import React, { useState, useEffect } from 'react';
import {
  Plug, Search, ExternalLink, Check, X, RefreshCw, AlertTriangle, Clock, ShieldAlert,
  Truck, CreditCard, Calculator, Users, CalendarDays, UtensilsCrossed, Award, Layers,
  Building2, Wallet, History, ChevronDown, ChevronRight
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle
} from '../components/ui/dialog';
import { useTheme } from '../contexts/ThemeContext';
import { integrationsAPI } from '../services/api';
import { toast } from 'sonner';

const CATEGORY_ICONS = {
  'Delivery': Truck,
  'Middleware': Layers,
  'Payments': CreditCard,
  'Payment Terminals': Wallet,
  'Banks (AU)': Building2,
  'Accounting': Calculator,
  'Rostering': Users,
  'Reservations': CalendarDays,
  'In-Venue Ordering': UtensilsCrossed,
  'Loyalty & Marketing': Award,
};

// Friendly labels for the multi-field connectors (Square today). Anything
// not listed here falls back to the field name itself.
const FIELD_LABELS = {
  accessToken: 'Access Token',
  locationId: 'Location ID',
  environment: 'Environment (sandbox / production)',
  webhookSignatureKey: 'Webhook Signature Key',
  webhookNotificationUrl: 'Webhook Notification URL',
  cdrClientId: 'CDR Client ID',
  cdrClientSecret: 'CDR Client Secret',
  apiKey: 'API Key',
};

const STATUS_META = {
  connected: { label: 'Connected', badge: 'bg-emerald-100 text-emerald-700 border-emerald-300', icon: Check },
  preconfigured: { label: 'Pre-configured', badge: 'bg-blue-100 text-blue-700 border-blue-300', icon: Check },
  needs_credentials: { label: 'Not Connected', badge: 'bg-gray-100 text-gray-500 border-gray-200', icon: Plug },
  error: { label: 'Connection Error', badge: 'bg-red-100 text-red-700 border-red-300', icon: AlertTriangle },
  pending_accreditation: { label: 'Pending CDR Accreditation', badge: 'bg-amber-100 text-amber-700 border-amber-300', icon: ShieldAlert },
  not_implemented: { label: 'Not Available Yet', badge: 'bg-gray-100 text-gray-400 border-gray-200', icon: Clock },
};

function StatusBadge({ status }) {
  const meta = STATUS_META[status] || STATUS_META.needs_credentials;
  const Icon = meta.icon;
  return (
    <Badge className={`${meta.badge} text-[10px]`}>
      <Icon size={10} className="mr-0.5" /> {meta.label}
    </Badge>
  );
}

export default function Integrations() {
  const { theme } = useTheme();
  const [integrations, setIntegrations] = useState([]);
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState('All');
  const [connectDialog, setConnectDialog] = useState(null);
  const [fieldValues, setFieldValues] = useState({});
  const [loading, setLoading] = useState(false);
  const [historyDialog, setHistoryDialog] = useState(null);
  const [historyRuns, setHistoryRuns] = useState([]);
  const [expandedRun, setExpandedRun] = useState(null);
  const [runDetail, setRunDetail] = useState(null);

  useEffect(() => { fetchIntegrations(); }, []);

  const fetchIntegrations = async () => {
    try {
      const res = await integrationsAPI.getAll();
      setIntegrations(res.data);
    } catch { toast.error('Failed to load integrations'); }
  };

  const categories = ['All', ...new Set(integrations.map(i => i.category))];

  const filtered = integrations.filter(i =>
    (activeCategory === 'All' || i.category === activeCategory) &&
    (i.name.toLowerCase().includes(search.toLowerCase()) || i.category.toLowerCase().includes(search.toLowerCase()))
  );

  const openConnect = (integration) => {
    setConnectDialog(integration);
    const initial = {};
    (integration.credentialFields || ['apiKey']).forEach(f => { initial[f] = ''; });
    setFieldValues(initial);
  };

  const handleConnect = async () => {
    const fields = connectDialog.credentialFields || ['apiKey'];
    if (fields.some(f => !fieldValues[f]?.trim())) return;
    setLoading(true);
    try {
      const res = await integrationsAPI.connect(connectDialog.slug, fieldValues);
      if (res.data.status === 'pending_accreditation') {
        toast.info(`${connectDialog.name}: credentials saved, pending CDR accreditation`);
      } else {
        toast.success(`${connectDialog.name} connected!`);
      }
      setConnectDialog(null);
      setFieldValues({});
      fetchIntegrations();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Connection failed');
    } finally { setLoading(false); }
  };

  const handleDisconnect = async (slug, name) => {
    try {
      await integrationsAPI.disconnect(slug);
      toast.success(`${name} disconnected`);
      fetchIntegrations();
    } catch { toast.error('Failed to disconnect'); }
  };

  const handleSync = async (slug, name, syncType) => {
    try {
      const res = await integrationsAPI.sync(slug, syncType);
      const c = res.data.counts || {};
      toast.success(`${name} ${syncType} sync: ${c.fetched || 0} fetched, ${c.created || 0} created, ${c.updated || 0} updated`);
      fetchIntegrations();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Sync failed'); }
  };

  const openHistory = async (integration) => {
    setHistoryDialog(integration);
    setExpandedRun(null);
    setRunDetail(null);
    try {
      const res = await integrationsAPI.getSyncHistory(integration.slug);
      setHistoryRuns(res.data);
    } catch { toast.error('Failed to load sync history'); }
  };

  const toggleRunDetail = async (runId) => {
    if (expandedRun === runId) { setExpandedRun(null); setRunDetail(null); return; }
    setExpandedRun(runId);
    try {
      const res = await integrationsAPI.getSyncRunDetail(runId);
      setRunDetail(res.data);
    } catch { toast.error('Failed to load run detail'); }
  };

  const connectedCount = integrations.filter(i => i.status === 'connected' || i.status === 'preconfigured').length;

  return (
    <div data-testid="integrations-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold" style={{ color: theme.text }}>NUA Connect — Integrations Hub</h1>
          <p className="text-gray-500 mt-1">{connectedCount} connected &middot; {integrations.length} providers &middot; real, honest status — never faked</p>
        </div>
        <Badge className="bg-emerald-100 text-emerald-700 border-emerald-300 text-sm px-3 py-1">
          <Plug size={14} className="mr-1" /> {connectedCount} Active
        </Badge>
      </div>

      {/* Search & Filter */}
      <div className="flex gap-3 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <Input placeholder="Search integrations..." className="pl-10" value={search}
            onChange={e => setSearch(e.target.value)} data-testid="integrations-search" />
        </div>
      </div>

      {/* Category Tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-1">
        {categories.map(cat => (
          <button key={cat} onClick={() => setActiveCategory(cat)}
            className={`whitespace-nowrap px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              activeCategory === cat ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`} data-testid={`int-cat-${cat}`}>
            {cat}
          </button>
        ))}
      </div>

      {/* Integration Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map(integration => {
          const CatIcon = CATEGORY_ICONS[integration.category] || Plug;
          const connected = integration.status === 'connected';
          const capabilities = integration.capabilities || [];
          return (
            <Card key={integration.slug} className={`transition-all hover:shadow-md ${connected ? 'border-emerald-200 bg-emerald-50/30' : ''}`}
              data-testid={`integration-${integration.slug}`}>
              <CardContent className="p-5">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${connected ? 'bg-emerald-100 text-emerald-600' : 'bg-gray-100 text-gray-500'}`}>
                      <CatIcon size={20} />
                    </div>
                    <div>
                      <h3 className="font-semibold" style={{ color: theme.text }}>{integration.name}</h3>
                      <p className="text-xs text-gray-500">{integration.category}</p>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <StatusBadge status={integration.status} />
                    {/* Stripe secret keys are self-describing (sk_test_/sk_live_) — surface
                        which one is live so nobody discovers a venue is still on test-mode
                        payments (or accidentally live during a demo) by reading env vars. */}
                    {integration.mode && (
                      <Badge
                        className={`text-[10px] ${integration.mode === 'live'
                          ? 'bg-red-100 text-red-700 border-red-300'
                          : 'bg-amber-100 text-amber-700 border-amber-300'}`}
                        data-testid={`${integration.slug}-mode-badge`}
                      >
                        {integration.mode === 'live' ? 'Live mode' : 'Test mode'}
                      </Badge>
                    )}
                  </div>
                </div>
                <p className="text-sm text-gray-500 mb-2 line-clamp-2">{integration.description}</p>
                {integration.note && (
                  <p className="text-xs text-amber-600 mb-2 flex items-start gap-1">
                    <ShieldAlert size={12} className="mt-0.5 shrink-0" /> {integration.note}
                  </p>
                )}
                {integration.lastError && (
                  <p className="text-xs text-red-500 mb-2">{integration.lastError}</p>
                )}
                <div className="flex flex-wrap gap-2">
                  {connected ? (
                    <>
                      {capabilities.filter(c => ['catalog', 'sales', 'customers'].includes(c)).map(cap => (
                        <Button key={cap} size="sm" variant="outline" className="text-xs"
                          onClick={() => handleSync(integration.slug, integration.name, cap)}
                          data-testid={`sync-${integration.slug}-${cap}`}>
                          <RefreshCw size={12} className="mr-1" /> Sync {cap}
                        </Button>
                      ))}
                      <Button size="sm" variant="outline" className="text-xs"
                        onClick={() => openHistory(integration)} data-testid={`history-${integration.slug}`}>
                        <History size={12} className="mr-1" /> History
                      </Button>
                      <Button size="sm" variant="outline" className="text-xs text-red-500 border-red-200 hover:bg-red-50"
                        onClick={() => handleDisconnect(integration.slug, integration.name)}
                        data-testid={`disconnect-${integration.slug}`}>
                        <X size={12} className="mr-1" /> Disconnect
                      </Button>
                    </>
                  ) : integration.status === 'preconfigured' ? (
                    <Badge className="bg-blue-100 text-blue-700 border-blue-300 text-xs">
                      <Check size={12} className="mr-1" /> Pre-configured
                    </Badge>
                  ) : integration.status === 'not_implemented' ? (
                    <Badge variant="outline" className="text-gray-400 text-xs">No connector built yet</Badge>
                  ) : (
                    <>
                      <Button size="sm" className="flex-1 text-xs" style={{ backgroundColor: theme.primary }}
                        onClick={() => openConnect(integration)}
                        data-testid={`connect-${integration.slug}`}>
                        <Plug size={12} className="mr-1" /> Connect
                      </Button>
                      {integration.status === 'error' && (
                        <Button size="sm" variant="outline" className="text-xs" onClick={() => openHistory(integration)}
                          data-testid={`history-${integration.slug}`}>
                          <History size={12} className="mr-1" /> History
                        </Button>
                      )}
                    </>
                  )}
                  {integration.website && (
                    <a href={integration.website} target="_blank" rel="noopener noreferrer"
                      className="inline-flex items-center justify-center w-8 h-8 rounded-md border border-gray-200 text-gray-400 hover:text-gray-600 hover:bg-gray-50">
                      <ExternalLink size={14} />
                    </a>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Connect Dialog */}
      <Dialog open={!!connectDialog} onOpenChange={open => { if (!open) setConnectDialog(null); }}>
        <DialogContent className="max-w-sm" data-testid="connect-dialog">
          <DialogHeader>
            <DialogTitle>Connect {connectDialog?.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <p className="text-sm text-gray-500">{connectDialog?.description}</p>
            {(connectDialog?.credentialFields || ['apiKey']).map(field => (
              <div key={field}>
                <label className="text-sm font-medium mb-1 block">
                  {FIELD_LABELS[field] || field}
                </label>
                <Input placeholder={`Enter ${FIELD_LABELS[field] || field}...`}
                  value={fieldValues[field] || ''}
                  onChange={e => setFieldValues(v => ({ ...v, [field]: e.target.value }))}
                  type={field.toLowerCase().includes('secret') || field.toLowerCase().includes('token') || field.toLowerCase().includes('key') ? 'password' : 'text'}
                  data-testid={`field-${field}`} />
              </div>
            ))}
            {connectDialog?.website && (
              <p className="text-xs text-gray-400">
                Get your credentials from <a href={connectDialog.website} target="_blank" rel="noopener noreferrer"
                  className="text-blue-500 hover:underline">{connectDialog.website}</a>
              </p>
            )}
            <div className="flex gap-2">
              <Button className="flex-1" style={{ backgroundColor: theme.primary }}
                onClick={handleConnect} disabled={loading}
                data-testid="confirm-connect-btn">
                {loading ? 'Connecting...' : 'Connect'}
              </Button>
              <Button variant="outline" onClick={() => setConnectDialog(null)}>Cancel</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Sync History / Raw Data Dialog */}
      <Dialog open={!!historyDialog} onOpenChange={open => { if (!open) setHistoryDialog(null); }}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto" data-testid="history-dialog">
          <DialogHeader>
            <DialogTitle>{historyDialog?.name} — Sync History</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 py-2">
            {historyRuns.length === 0 && <p className="text-sm text-gray-400">No syncs yet.</p>}
            {historyRuns.map(run => (
              <div key={run.id} className="border rounded-lg overflow-hidden">
                <button
                  className="w-full flex items-center justify-between p-3 text-left hover:bg-gray-50"
                  onClick={() => toggleRunDetail(run.id)} data-testid={`run-${run.id}`}>
                  <div className="flex items-center gap-2">
                    {expandedRun === run.id ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    <Badge className={run.status === 'success' ? 'bg-emerald-100 text-emerald-700' : run.status === 'running' ? 'bg-blue-100 text-blue-700' : 'bg-red-100 text-red-700'}>
                      {run.status}
                    </Badge>
                    <span className="text-sm font-medium">{run.syncType}</span>
                    <span className="text-xs text-gray-400">{new Date(run.startedAt).toLocaleString()}</span>
                  </div>
                  <span className="text-xs text-gray-500">
                    {run.counts?.fetched || 0} fetched &middot; {run.counts?.created || 0} created &middot; {run.counts?.updated || 0} updated
                  </span>
                </button>
                {expandedRun === run.id && runDetail && (
                  <div className="p-3 bg-gray-50 border-t text-xs">
                    {runDetail.errorMessage && <p className="text-red-500 mb-2">{runDetail.errorMessage}</p>}
                    <p className="font-medium mb-1">Raw payload samples ({(runDetail.rawSamples || []).length}):</p>
                    <pre className="bg-white border rounded p-2 overflow-x-auto max-h-64 overflow-y-auto">
{JSON.stringify(runDetail.rawSamples, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
