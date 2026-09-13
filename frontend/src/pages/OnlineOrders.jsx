import React, { useEffect, useState } from 'react';
import { Clock, ChefHat, Bike, CheckCircle, Phone, MapPin, RefreshCw, X, Sparkles } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { useTheme } from '../contexts/ThemeContext';
import { onlineAPI } from '../services/api';
import { useToast } from '../hooks/use-toast';

const STAGES = [
  { key: 'pending', label: 'New', color: '#f59e0b', icon: Clock },
  { key: 'accepted', label: 'Accepted', color: '#3b82f6', icon: CheckCircle },
  { key: 'preparing', label: 'Preparing', color: '#8b5cf6', icon: ChefHat },
  { key: 'ready', label: 'Ready', color: '#10b981', icon: CheckCircle },
  { key: 'out_for_delivery', label: 'Out for Delivery', color: '#ec4899', icon: Bike },
  { key: 'completed', label: 'Completed', color: '#6b7280', icon: CheckCircle },
];

const STAGE_NEXT = {
  pending: 'accepted', accepted: 'preparing', preparing: 'ready',
  ready: 'completed',  // pickup/dine-in
  out_for_delivery: 'completed',
};

const colorFor = (status) => STAGES.find(s => s.key === status)?.color || '#6b7280';

export default function OnlineOrders() {
  const { theme } = useTheme();
  const { toast } = useToast();
  const [orders, setOrders] = useState([]);
  const [filter, setFilter] = useState('open');
  const [kitchenLoad, setKitchenLoad] = useState({});
  const [opened, setOpened] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const [a, b] = await Promise.all([onlineAPI.listOrders(), onlineAPI.kitchenLoad()]);
      setOrders(a.data || []);
      setKitchenLoad(b.data || {});
    } catch {}
  };
  useEffect(() => { load(); const t = setInterval(load, 8000); return () => clearInterval(t); }, []);

  const filtered = orders.filter(o => {
    if (filter === 'all') return true;
    if (filter === 'open') return !['completed', 'cancelled'].includes(o.status);
    return o.status === filter;
  });

  const grouped = STAGES.reduce((acc, s) => {
    acc[s.key] = filtered.filter(o => o.status === s.key);
    return acc;
  }, {});

  const advance = async (order, nextStatus, extras = {}) => {
    setBusy(true);
    try {
      const r = await onlineAPI.updateStatus(order.id, { status: nextStatus, ...extras });
      toast({ title: 'Status updated', description: `${order.id} → ${nextStatus}` });
      setOpened(r.data);
      load();
    } catch (e) { toast({ title: 'Failed', description: e?.response?.data?.detail, variant: 'destructive' }); }
    setBusy(false);
  };

  const recompute = async (order) => {
    setBusy(true);
    try {
      const r = await onlineAPI.recomputeEta(order.id);
      toast({ title: 'ETA recomputed', description: `${r.data.eta?.etaMinutes} min` });
      load();
      if (opened?.id === order.id) setOpened({ ...opened, eta: r.data.eta, etaMessage: r.data.etaMessage });
    } catch {} finally { setBusy(false); }
  };

  return (
    <div className="space-y-5" data-testid="online-orders-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
            <Sparkles size={28} className="text-purple-600" /> Online Orders
          </h1>
          <p className="text-sm text-gray-500">Real-time order pipeline with AI ETA</p>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-gray-500">Kitchen load:</span>
          <Badge variant="outline" className="font-mono">
            {kitchenLoad.pending || 0} pending · {kitchenLoad.preparing || 0} prepping · +{kitchenLoad.queuePenaltyMins || 0} min penalty
          </Badge>
          <Button variant="outline" size="sm" onClick={load} data-testid="refresh-online-orders"><RefreshCw size={14} /></Button>
        </div>
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1">
        {['open', 'all', ...STAGES.map(s => s.key)].map(k => (
          <button key={k} onClick={() => setFilter(k)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition ${filter === k ? 'text-white shadow-sm' : 'bg-white border hover:border-gray-400'}`}
            style={filter === k ? { background: theme.primary } : {}}
            data-testid={`filter-${k}`}>
            {k === 'open' ? 'Open' : k === 'all' ? 'All' : STAGES.find(s => s.key === k)?.label || k}
            <span className="ml-1 opacity-60">({k === 'open' ? orders.filter(o => !['completed','cancelled'].includes(o.status)).length : (k === 'all' ? orders.length : grouped[k]?.length || 0)})</span>
          </button>
        ))}
      </div>

      <div className="grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(280px,1fr))]" data-testid="online-orders-pipeline">
        {STAGES.filter(s => filter === 'all' || filter === 'open' ? s.key !== 'completed' || filter === 'all' : s.key === filter).map(stage => (
          <div key={stage.key} className="bg-gray-50 rounded-xl p-3" data-testid={`stage-${stage.key}`}>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full" style={{ background: stage.color }} />
                <span className="font-bold text-sm">{stage.label}</span>
              </div>
              <span className="text-xs text-gray-400">{grouped[stage.key]?.length || 0}</span>
            </div>
            <div className="space-y-2">
              {(grouped[stage.key] || []).map(o => (
                <Card key={o.id} className="cursor-pointer hover:shadow-md transition" onClick={() => setOpened(o)} data-testid={`order-card-${o.id}`}>
                  <CardContent className="p-3 space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="font-mono font-bold">{o.id}</span>
                      <span className="font-bold" style={{ color: stage.color }}>${o.total.toFixed(2)}</span>
                    </div>
                    <p className="text-sm font-medium truncate">{(o.customer || {}).name}</p>
                    <p className="text-xs text-gray-500 capitalize">{o.channel} · {o.items.length} items</p>
                    <div className="flex gap-1 flex-wrap">
                      {/* Order/payment colours per NUA_POS_DESIGN_TOKENS.md §6. */}
                      {o.paymentStatus === 'paid' && (
                        <Badge className="bg-[#047857] text-white border-0 text-[9px]" data-testid={`order-paid-badge-${o.id}`}>Paid</Badge>
                      )}
                      {o.paymentStatus === 'refunded' && (
                        <Badge variant="outline" className="bg-[rgba(176,27,27,0.10)] text-[#B01B1B] border-0 line-through text-[9px]" data-testid={`order-refunded-badge-${o.id}`}>Refunded</Badge>
                      )}
                      {o.paymentStatus === 'refund_failed' && (
                        <Badge className="bg-[#B01B1B] text-white border-0 text-[9px]" data-testid={`order-refund-failed-badge-${o.id}`}>Refund failed</Badge>
                      )}
                      {o.voucherDiscount > 0 && (
                        <Badge variant="outline" className="text-emerald-700 border-emerald-300 text-[9px]" data-testid={`order-voucher-badge-${o.id}`}>
                          Voucher −${o.voucherDiscount.toFixed(2)}
                        </Badge>
                      )}
                    </div>
                    {o.eta && (
                      <div className="flex items-center gap-1 text-[11px] text-gray-600 mt-1">
                        <Clock size={11} /> {o.eta.etaMinutes} min
                        {o.eta.surge > 1.1 && <Badge variant="outline" className="text-orange-600 border-orange-300 text-[9px] ml-1">surge {o.eta.surge}x</Badge>}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
              {(grouped[stage.key] || []).length === 0 && (
                <p className="text-center text-gray-300 text-xs py-4">Empty</p>
              )}
            </div>
          </div>
        ))}
      </div>

      {opened && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-end md:items-center justify-center p-4" onClick={() => setOpened(null)} data-testid="order-detail-overlay">
          <div className="bg-white rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-mono font-bold text-lg" style={{ color: colorFor(opened.status) }}>{opened.id}</p>
                  <p className="text-xs text-gray-500 uppercase tracking-wider">{opened.channel} · {opened.status}</p>
                </div>
                <div className="flex items-center gap-2">
                  {opened.paymentStatus === 'paid' && (
                    <Badge className="bg-[#047857] text-white border-0" data-testid="order-paid-badge">Paid online</Badge>
                  )}
                  {opened.paymentStatus === 'refunded' && (
                    <Badge variant="outline" className="bg-[rgba(176,27,27,0.10)] text-[#B01B1B] border-0 line-through" data-testid="order-refunded-badge">Refunded</Badge>
                  )}
                  {opened.paymentStatus === 'refund_failed' && (
                    <Badge className="bg-[#B01B1B] text-white border-0" data-testid="order-refund-failed-badge">Refund failed — refund manually</Badge>
                  )}
                  {(!opened.paymentStatus || opened.paymentStatus === 'unpaid') && (
                    <Badge variant="outline" className="text-gray-500" data-testid="order-unpaid-badge">Unpaid</Badge>
                  )}
                  <Button variant="ghost" size="sm" onClick={() => setOpened(null)}><X size={16} /></Button>
                </div>
              </div>

              <Card><CardContent className="p-3 space-y-1.5">
                <div className="flex items-center gap-2 text-sm"><span className="font-bold">Customer:</span> {opened.customer.name}</div>
                {opened.customer.phone && <div className="flex items-center gap-2 text-sm"><Phone size={12} /> {opened.customer.phone}</div>}
                {opened.customer.address && <div className="flex items-start gap-2 text-sm"><MapPin size={12} className="mt-0.5" /> {opened.customer.address}</div>}
                {opened.customer.notes && <div className="text-xs italic text-gray-600">"{opened.customer.notes}"</div>}
              </CardContent></Card>

              <div className="bg-purple-50 border border-purple-200 rounded-lg p-3" data-testid="order-eta-card">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs font-bold uppercase tracking-wider text-purple-700">AI ETA</span>
                  <Button size="sm" variant="ghost" className="h-6 px-2 text-xs text-purple-700" onClick={() => recompute(opened)} disabled={busy} data-testid="recompute-eta-btn">
                    <RefreshCw size={11} className="mr-1" /> Recompute
                  </Button>
                </div>
                <p className="text-3xl font-bold text-purple-900">{opened.eta?.etaMinutes ?? '—'} min</p>
                {opened.etaMessage && <p className="text-sm text-gray-700 mt-1">{opened.etaMessage}</p>}
                {opened.eta && (
                  <div className="grid grid-cols-3 gap-1 mt-2 text-[10px]">
                    <span className="bg-white rounded px-1.5 py-1">Base: {opened.eta.baseMinutes}m</span>
                    <span className="bg-white rounded px-1.5 py-1">Surge: {opened.eta.surge}x</span>
                    <span className="bg-white rounded px-1.5 py-1">Queue: +{opened.eta.queuePenaltyMins}m</span>
                  </div>
                )}
              </div>

              <div>
                <p className="text-xs uppercase font-bold tracking-wider text-gray-500 mb-1">Items ({opened.items.length})</p>
                {opened.items.map((it, i) => (
                  <div key={i} className="flex justify-between text-sm py-1 border-b last:border-0">
                    <span>{it.quantity}× {it.name} <span className="text-[10px] text-gray-400">{it.category}</span></span>
                    <span className="font-mono">${(it.price * it.quantity).toFixed(2)}</span>
                  </div>
                ))}
                {opened.voucherDiscount > 0 && (
                  <div className="pt-2 space-y-0.5" data-testid="order-voucher-line">
                    <div className="flex justify-between text-sm text-gray-500">
                      <span>Subtotal</span><span>${opened.subtotal.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between text-sm text-emerald-700">
                      <span>Voucher {opened.voucherCode ? `(${opened.voucherCode})` : ''} {opened.voucherLabel ? `— ${opened.voucherLabel}` : ''}</span>
                      <span>−${opened.voucherDiscount.toFixed(2)}</span>
                    </div>
                  </div>
                )}
                <div className="flex justify-between text-sm pt-2 font-bold"><span>Total</span><span>${opened.total.toFixed(2)}</span></div>
                {opened.paymentStatus === 'paid' ? (
                  <p className="text-[10px] text-emerald-700 bg-emerald-50 border border-emerald-200 rounded px-2 py-1 mt-1">
                    Already paid online — nothing to collect at pickup/delivery.
                  </p>
                ) : opened.voucherDiscount > 0 && (
                  <p className="text-[10px] text-amber-600 bg-amber-50 border border-amber-200 rounded px-2 py-1 mt-1">
                    Voucher already deducted above — charge exactly ${opened.total.toFixed(2)} when you process payment for this order.
                  </p>
                )}
              </div>

              {STAGE_NEXT[opened.status] && (
                <div className="flex gap-2">
                  {opened.channel === 'delivery' && opened.status === 'ready' ? (
                    <Button className="flex-1" style={{ background: colorFor('out_for_delivery') }} onClick={() => advance(opened, 'out_for_delivery', { driver: 'Auto-assigned' })} disabled={busy} data-testid="dispatch-driver-btn">
                      🛵 Dispatch driver
                    </Button>
                  ) : (
                    <Button className="flex-1 text-white" style={{ background: colorFor(STAGE_NEXT[opened.status]) }} onClick={() => advance(opened, STAGE_NEXT[opened.status])} disabled={busy} data-testid="advance-status-btn">
                      → Mark {STAGES.find(s => s.key === STAGE_NEXT[opened.status])?.label}
                    </Button>
                  )}
                  {opened.status !== 'completed' && (
                    <Button variant="outline" className="text-red-600" onClick={() => advance(opened, 'cancelled', { reason: 'Cancelled by staff' })} disabled={busy} data-testid="cancel-order-btn">
                      Cancel
                    </Button>
                  )}
                </div>
              )}

              {opened.events?.length > 0 && (
                <div className="pt-2 border-t">
                  <p className="text-xs uppercase font-bold tracking-wider text-gray-500 mb-1">Timeline</p>
                  <div className="space-y-1 text-xs">
                    {opened.events.slice().reverse().map((e, i) => (
                      <div key={i} className="flex justify-between text-gray-600">
                        <span>{e.message || e.kind}</span>
                        <span className="text-gray-400">{new Date(e.at).toLocaleTimeString()}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
