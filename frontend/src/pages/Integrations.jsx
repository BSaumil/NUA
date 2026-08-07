import React, { useState, useEffect } from 'react';
import {
  Plug, Search, ExternalLink, Check, X, RefreshCw,
  Truck, CreditCard, Calculator, Users, CalendarDays, UtensilsCrossed, Award, Layers,
  Building2, Wallet
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

export default function Integrations() {
  const { theme } = useTheme();
  const [integrations, setIntegrations] = useState([]);
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState('All');
  const [connectDialog, setConnectDialog] = useState(null);
  const [apiKey, setApiKey] = useState('');
  const [loading, setLoading] = useState(false);

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

  const handleConnect = async () => {
    if (!apiKey.trim()) return;
    setLoading(true);
    try {
      await integrationsAPI.connect(connectDialog.slug, { apiKey });
      toast.success(`${connectDialog.name} connected!`);
      setConnectDialog(null);
      setApiKey('');
      fetchIntegrations();
    } catch { toast.error('Connection failed'); }
    finally { setLoading(false); }
  };

  const handleDisconnect = async (slug, name) => {
    try {
      await integrationsAPI.disconnect(slug);
      toast.success(`${name} disconnected`);
      fetchIntegrations();
    } catch { toast.error('Failed to disconnect'); }
  };

  const handleSync = async (slug, name) => {
    try {
      await integrationsAPI.sync(slug);
      toast.success(`${name} sync triggered`);
      fetchIntegrations();
    } catch { toast.error('Sync failed'); }
  };

  const connectedCount = integrations.filter(i => i.status === 'connected').length;

  return (
    <div data-testid="integrations-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold" style={{ color: theme.text }}>Integrations Hub</h1>
          <p className="text-gray-500 mt-1">{connectedCount} connected &middot; {integrations.length} available</p>
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
                    {connected ? (
                      <Badge className="bg-emerald-100 text-emerald-700 border-emerald-300 text-[10px]">
                        <Check size={10} className="mr-0.5" /> Connected
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-gray-400 text-[10px]">Inactive</Badge>
                    )}
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
                <p className="text-sm text-gray-500 mb-4 line-clamp-2">{integration.description}</p>
                <div className="flex gap-2">
                  {connected ? (
                    <>
                      <Button size="sm" variant="outline" className="flex-1 text-xs"
                        onClick={() => handleSync(integration.slug, integration.name)}
                        data-testid={`sync-${integration.slug}`}>
                        <RefreshCw size={12} className="mr-1" /> Sync
                      </Button>
                      <Button size="sm" variant="outline" className="text-xs text-red-500 border-red-200 hover:bg-red-50"
                        onClick={() => handleDisconnect(integration.slug, integration.name)}
                        data-testid={`disconnect-${integration.slug}`}>
                        <X size={12} className="mr-1" /> Disconnect
                      </Button>
                    </>
                  ) : integration.preconfigured ? (
                    <Badge className="bg-blue-100 text-blue-700 border-blue-300 text-xs">
                      <Check size={12} className="mr-1" /> Pre-configured
                    </Badge>
                  ) : (
                    <Button size="sm" className="flex-1 text-xs" style={{ backgroundColor: theme.primary }}
                      onClick={() => setConnectDialog(integration)}
                      data-testid={`connect-${integration.slug}`}>
                      <Plug size={12} className="mr-1" /> Connect
                    </Button>
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
            <div>
              <label className="text-sm font-medium mb-1 block">{connectDialog?.keyLabel || 'API Key'}</label>
              <Input placeholder={`Enter your ${connectDialog?.keyLabel || 'API Key'}...`}
                value={apiKey} onChange={e => setApiKey(e.target.value)}
                type="password" data-testid="api-key-input" />
            </div>
            {connectDialog?.website && (
              <p className="text-xs text-gray-400">
                Get your key from <a href={connectDialog.website} target="_blank" rel="noopener noreferrer"
                  className="text-blue-500 hover:underline">{connectDialog.website}</a>
              </p>
            )}
            <div className="flex gap-2">
              <Button className="flex-1" style={{ backgroundColor: theme.primary }}
                onClick={handleConnect} disabled={loading || !apiKey.trim()}
                data-testid="confirm-connect-btn">
                {loading ? 'Connecting...' : 'Connect'}
              </Button>
              <Button variant="outline" onClick={() => setConnectDialog(null)}>Cancel</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
