import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  ChefHat, Clock, Flame, Bell, Check, X, Plus, Users, User, Monitor,
  UtensilsCrossed, RotateCcw, Zap, Timer, Pause, PlayCircle, Settings2,
} from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger,
} from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import { Switch } from '../components/ui/switch';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import { useTheme } from '../contexts/ThemeContext';
import { kitchenAPI, productsAPI } from '../services/api';
import { toast } from 'sonner';

const PRIORITY_CONFIG = {
  normal: { label: 'Normal', color: '#6B7280' },
  rush:   { label: 'RUSH',   color: '#EF4444' },
  vip:    { label: 'VIP',    color: '#F59E0B' },
};

const COURSE_LABEL = { 1: 'Starter', 2: 'Main', 3: 'Dessert', 4: 'Coffee', 5: 'Extra' };

const COURSE_STATUS_TONE = {
  queued: 'bg-slate-200 text-slate-600',
  held:   'bg-purple-100 text-purple-700',
  fired:  'bg-amber-100 text-amber-800',
  served: 'bg-emerald-100 text-emerald-700',
};

const FONT_SIZE_CLASS = { small: 'text-xs', medium: 'text-sm', large: 'text-base' };

function timeSince(iso) {
  if (!iso) return null;
  const diff = Math.round((new Date() - new Date(iso)) / 60000);
  if (diff < 1) return '<1m';
  return `${diff}m`;
}

function fmtHHMM(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
  } catch { return '—'; }
}

export default function Kitchen() {
  const { theme } = useTheme();
  const [orders, setOrders] = useState([]);
  const [filter, setFilter] = useState('active');
  const [newOrderDialog, setNewOrderDialog] = useState(false);
  const [products, setProducts] = useState([]);
  const [config, setConfig] = useState({});
  const [configDialog, setConfigDialog] = useState(false);
  const [configDraft, setConfigDraft] = useState({});
  const [role, setRole] = useState('cashier');
  const [avgOrderTime, setAvgOrderTime] = useState(null);
  const [orderForm, setOrderForm] = useState({
    tableNumber: '', orderType: 'dine_in', items: [], notes: '', priority: 'normal',
    covers: '', deviceLabel: '',
  });
  const [selectedProduct, setSelectedProduct] = useState('');
  const [selectedCourse, setSelectedCourse] = useState(1);

  useEffect(() => {
    try {
      const u = JSON.parse(localStorage.getItem('nuva_user') || '{}');
      setRole(u.role || 'cashier');
    } catch { /* ignore */ }
  }, []);

  const fetchOrders = useCallback(async () => {
    try {
      const params = {};
      if (filter !== 'active' && filter !== 'all') params.status = filter;
      const res = await kitchenAPI.getOrders(params);
      setOrders(res.data);
    } catch (e) { console.error(e); }
  }, [filter]);

  const fetchConfig = useCallback(async () => {
    try {
      const r = await kitchenAPI.getDocketConfig();
      setConfig(r.data);
    } catch { /* ignore */ }
  }, []);

  const fetchAvgOrderTime = useCallback(async () => {
    try {
      const r = await kitchenAPI.getAvgOrderTime();
      setAvgOrderTime(r.data);
    } catch { /* ignore — this is a rough gauge, not critical */ }
  }, []);

  useEffect(() => { fetchOrders(); fetchConfig(); fetchAvgOrderTime(); }, [fetchOrders, fetchConfig, fetchAvgOrderTime]);
  useEffect(() => {
    const interval = setInterval(() => { fetchOrders(); fetchAvgOrderTime(); }, 10000);
    return () => clearInterval(interval);
  }, [fetchOrders, fetchAvgOrderTime]);

  const fetchProducts = async () => {
    try { const res = await productsAPI.getAll(); setProducts(res.data); }
    catch (e) { console.error(e); }
  };

  const openNewOrder = () => {
    fetchProducts();
    setOrderForm({ tableNumber: '', orderType: 'dine_in', items: [], notes: '', priority: 'normal', covers: '', deviceLabel: '' });
    setNewOrderDialog(true);
  };

  const openConfigDialog = () => {
    setConfigDraft({ ...config });
    setConfigDialog(true);
  };

  const saveConfig = async () => {
    try {
      const r = await kitchenAPI.updateDocketConfig(configDraft);
      setConfig(r.data);
      toast.success('Docket display updated');
      setConfigDialog(false);
    } catch { toast.error('Save failed'); }
  };

  const handle = {
    start:   async (id) => { try { await kitchenAPI.startOrder(id); toast.success('Order started'); fetchOrders(); } catch { toast.error('Failed'); } },
    ready:   async (id) => { try { await kitchenAPI.readyOrder(id); toast.success('Ready'); fetchOrders(); } catch { toast.error('Failed'); } },
    served:  async (id) => { try { await kitchenAPI.servedOrder(id); toast.success('Served'); fetchOrders(); } catch { toast.error('Failed'); } },
    cancel:  async (id) => { try { await kitchenAPI.cancelOrder(id); toast.warning('Cancelled'); fetchOrders(); } catch { toast.error('Failed'); } },
    prio:    async (id, p) => { try { await kitchenAPI.setPriority(id, p); toast.success(`Priority ${p}`); fetchOrders(); } catch { toast.error('Failed'); } },
    fire:    async (id, c) => { try { await kitchenAPI.fireCourse(id, c); toast.success(`${COURSE_LABEL[c] || 'C'+c} fired`); fetchOrders(); } catch { toast.error('Failed'); } },
    hold:    async (id, c) => { try { await kitchenAPI.holdCourse(id, c); toast(`${COURSE_LABEL[c] || 'C'+c} held`); fetchOrders(); } catch { toast.error('Failed'); } },
    serveC:  async (id, c) => { try { await kitchenAPI.serveCourse(id, c); toast.success(`${COURSE_LABEL[c] || 'C'+c} served`); fetchOrders(); } catch { toast.error('Failed'); } },
  };

  const addItemToOrder = () => {
    if (!selectedProduct) return;
    const product = products.find(p => p.id === selectedProduct);
    if (!product) return;
    setOrderForm(f => ({
      ...f,
      items: [...f.items, { productId: product.id, productName: product.name, quantity: 1, course: selectedCourse, status: 'pending', notes: '' }],
    }));
    setSelectedProduct('');
  };

  const removeItemFromOrder = (idx) => {
    setOrderForm(f => ({ ...f, items: f.items.filter((_, i) => i !== idx) }));
  };

  const handleCreateOrder = async () => {
    if (orderForm.items.length === 0) { toast.error('Add at least one item'); return; }
    try {
      const payload = { ...orderForm };
      if (payload.covers) payload.covers = parseInt(payload.covers, 10);
      else delete payload.covers;
      await kitchenAPI.createOrder(payload);
      toast.success('Order sent to kitchen');
      setNewOrderDialog(false);
      fetchOrders();
    } catch { toast.error('Failed to create order'); }
  };

  const displayed = filter === 'active'
    ? orders.filter(o => ['new', 'preparing', 'ready'].includes(o.status))
    : filter === 'all' ? orders : orders.filter(o => o.status === filter);

  const sorted = [...displayed].sort((a, b) => {
    if (a.priority === 'rush' && b.priority !== 'rush') return -1;
    if (b.priority === 'rush' && a.priority !== 'rush') return 1;
    if (a.priority === 'vip' && b.priority === 'normal') return -1;
    if (b.priority === 'vip' && a.priority === 'normal') return 1;
    return new Date(a.createdAt) - new Date(b.createdAt);
  });

  const newOrders = sorted.filter(o => o.status === 'new');
  const preparing = sorted.filter(o => o.status === 'preparing');
  const ready = sorted.filter(o => o.status === 'ready');

  const stats = useMemo(() => ({
    total: orders.filter(o => ['new', 'preparing', 'ready'].includes(o.status)).length,
    newCount: newOrders.length,
    prepCount: preparing.length,
    readyCount: ready.length,
  }), [orders, newOrders, preparing, ready]);

  const fontClass = FONT_SIZE_CLASS[config.fontSize] || FONT_SIZE_CLASS.medium;

  const renderCourseRow = (order, courseNum, courseItems) => {
    const meta = order.courses?.[String(courseNum)] || { status: 'queued' };
    const label = COURSE_LABEL[courseNum] || `Course ${courseNum}`;
    const canHold = meta.status === 'queued';
    const canFire = ['queued', 'held'].includes(meta.status);
    const canServe = meta.status === 'fired';
    return (
      <div key={courseNum} className="border rounded-lg overflow-hidden mb-2" data-testid={`course-block-${order.id}-${courseNum}`}>
        <div className={`flex items-center justify-between px-3 py-1.5 ${COURSE_STATUS_TONE[meta.status] || 'bg-slate-100'}`}>
          <div className="flex items-center gap-2">
            <span className="font-semibold text-xs uppercase tracking-wide">{label}</span>
            <Badge variant="outline" className="text-[9px] uppercase bg-white/80">{meta.status}</Badge>
            {config.showFireTime !== false && meta.firedAt && (
              <span className="text-[10px] text-slate-600 flex items-center gap-1">
                <Flame size={10} /> fired {fmtHHMM(meta.firedAt)}
                {meta.firedBy && <span className="opacity-70">by {meta.firedBy}</span>}
              </span>
            )}
            {meta.status === 'held' && meta.heldAt && (
              <span className="text-[10px] text-slate-600 flex items-center gap-1">
                <Pause size={10} /> held {fmtHHMM(meta.heldAt)}
              </span>
            )}
          </div>
          <div className="flex gap-1">
            {canHold && (
              <button className="text-[10px] px-2 py-0.5 bg-white rounded border hover:bg-purple-50 flex items-center gap-1"
                onClick={() => handle.hold(order.id, courseNum)}
                data-testid={`hold-c${courseNum}-${order.id}`}>
                <Pause size={10} /> Hold
              </button>
            )}
            {canFire && (
              <button className="text-[10px] px-2 py-0.5 bg-amber-500 text-white rounded hover:bg-amber-600 flex items-center gap-1"
                onClick={() => handle.fire(order.id, courseNum)}
                data-testid={`fire-c${courseNum}-${order.id}`}>
                <Flame size={10} /> Fire
              </button>
            )}
            {canServe && (
              <button className="text-[10px] px-2 py-0.5 bg-emerald-500 text-white rounded hover:bg-emerald-600 flex items-center gap-1"
                onClick={() => handle.serveC(order.id, courseNum)}
                data-testid={`serve-c${courseNum}-${order.id}`}>
                <Check size={10} /> Serve
              </button>
            )}
          </div>
        </div>
        <div className="px-3 py-1.5 space-y-1 bg-white">
          {courseItems.map((item, idx) => (
            <div key={idx} className={`flex items-start justify-between ${fontClass}`}>
              <div className="flex items-start gap-2">
                <span className="font-mono font-bold text-slate-400 w-5 text-center">{item.quantity}x</span>
                <div>
                  <span className="font-medium">{item.productName}</span>
                  {config.showModifiers !== false && item.modifiers?.length > 0 && (
                    <div className="text-[10px] text-slate-500 italic">+ {item.modifiers.map(m => m.name || m).join(', ')}</div>
                  )}
                  {config.showItemNotes !== false && item.notes && (
                    <div className="text-[10px] text-orange-600 italic">&ldquo;{item.notes}&rdquo;</div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderOrderCard = (order) => {
    const isRush = order.priority === 'rush';
    const isVip = order.priority === 'vip';
    const elapsed = Math.round((new Date() - new Date(order.createdAt)) / 60000);
    const warnMin = config.warnMinutes ?? 15;
    const critMin = config.criticalMinutes ?? 25;
    const elapsedTone = elapsed >= critMin ? 'bg-rose-100 text-rose-700'
                       : elapsed >= warnMin ? 'bg-amber-100 text-amber-700'
                       : 'bg-slate-100 text-slate-600';

    // Group items by course
    const byCourse = {};
    (order.items || []).forEach(it => {
      const c = it.course || 1;
      byCourse[c] = byCourse[c] || [];
      byCourse[c].push(it);
    });
    const courseNums = Object.keys(byCourse).map(n => parseInt(n, 10)).sort((a, b) => a - b);

    return (
      <Card key={order.id} className={`shadow-sm mb-3 ${isRush ? 'ring-2 ring-red-300' : ''} ${isVip ? 'ring-2 ring-amber-300' : ''}`}
        data-testid={`kitchen-order-${order.id}`}>
        <CardContent className="p-3">
          {/* Header row 1: table, id, priority, elapsed */}
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 flex-wrap">
              {config.showTable !== false && order.tableNumber && (
                <Badge variant="outline" className="font-mono font-bold text-sm">T{order.tableNumber}</Badge>
              )}
              <span className="text-[10px] font-mono text-slate-400">{(order.id || '').slice(0, 11)}</span>
              {(isRush || isVip) && (
                <Badge style={{ background: PRIORITY_CONFIG[order.priority].color, color: 'white' }} className="text-[9px] animate-pulse">
                  {PRIORITY_CONFIG[order.priority].label}
                </Badge>
              )}
              <Badge variant="outline" className="text-[9px] capitalize">{(order.orderType || '').replace('_', ' ')}</Badge>
            </div>
            {config.showElapsedTimer !== false && (
              <div className={`flex items-center gap-1 text-[10px] px-2 py-0.5 rounded ${elapsedTone}`}>
                <Timer size={10} /> {elapsed}m
              </div>
            )}
          </div>

          {/* Docket meta row */}
          <div className="flex flex-wrap gap-2 text-[10px] text-slate-500 mb-2 pb-2 border-b">
            {config.showStaffName !== false && order.createdByName && (
              <span className="flex items-center gap-1" data-testid={`meta-staff-${order.id}`}>
                <User size={10} /> {order.createdByName}
              </span>
            )}
            {config.showDevice !== false && order.deviceLabel && (
              <span className="flex items-center gap-1" data-testid={`meta-device-${order.id}`}>
                <Monitor size={10} /> {order.deviceLabel}
              </span>
            )}
            {config.showCovers !== false && order.covers ? (
              <span className="flex items-center gap-1" data-testid={`meta-covers-${order.id}`}>
                <Users size={10} /> {order.covers} covers
              </span>
            ) : null}
            {config.showGuestName !== false && order.guestName && (
              <span className="flex items-center gap-1 italic" data-testid={`meta-guest-${order.id}`}>{order.guestName}</span>
            )}
            <span className="flex items-center gap-1">
              <Clock size={10} /> in {fmtHHMM(order.createdAt)}
            </span>
          </div>

          {/* Courses */}
          {courseNums.length > 0
            ? courseNums.map(c => renderCourseRow(order, c, byCourse[c]))
            : (order.items || []).length > 0 && (
              <div className="text-xs italic text-slate-500 py-2">No course assigned</div>
            )
          }

          {/* Order-level notes */}
          {config.showOrderNotes !== false && order.notes && (
            <div className="text-xs text-orange-700 bg-orange-50 px-2 py-1 rounded mt-2 border border-orange-100">
              {order.notes}
            </div>
          )}

          {/* Order-level actions */}
          <div className="flex gap-1.5 flex-wrap mt-2 pt-2 border-t">
            {order.status === 'new' && (
              <>
                <Button size="sm" className="h-7 text-xs bg-amber-500 hover:bg-amber-600" onClick={() => handle.start(order.id)}
                  data-testid={`start-order-${order.id}`}>
                  <Flame size={12} className="mr-1" /> Start
                </Button>
                <Button size="sm" variant="outline" className="h-7 text-xs text-red-500" onClick={() => handle.prio(order.id, 'rush')}
                  data-testid={`rush-order-${order.id}`}>
                  <Zap size={12} className="mr-1" /> Rush
                </Button>
              </>
            )}
            {order.status === 'preparing' && (
              <Button size="sm" className="h-7 text-xs bg-green-600 hover:bg-green-700" onClick={() => handle.ready(order.id)}
                data-testid={`ready-order-${order.id}`}>
                <Check size={12} className="mr-1" /> All Ready
              </Button>
            )}
            {order.status === 'ready' && (
              <Button size="sm" className="h-7 text-xs" style={{ background: theme.primary }} onClick={() => handle.served(order.id)}
                data-testid={`served-order-${order.id}`}>
                <UtensilsCrossed size={12} className="mr-1" /> Served
              </Button>
            )}
            <Button size="sm" variant="ghost" className="h-7 text-xs text-red-400 hover:text-red-600" onClick={() => handle.cancel(order.id)}
              data-testid={`cancel-kitchen-${order.id}`}>
              <X size={12} />
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  };

  const canConfigure = role === 'owner' || role === 'manager';

  return (
    <div className="space-y-6" data-testid="kitchen-page">
      {/* Average order time — a rough live gauge in the corner so the chef
          can judge pace mid-service without digging into a report. */}
      {avgOrderTime !== null && (
        <div
          className="fixed top-3 right-3 z-40 rounded-lg shadow-md px-3 py-2 flex items-center gap-2 bg-white border"
          data-testid="avg-order-time-badge"
          title={`Based on ${avgOrderTime.ordersCompletedToday} order(s) completed today`}
        >
          <Timer size={16} style={{ color: theme.primary }} />
          <div className="leading-tight">
            <p className="text-[9px] uppercase tracking-wide text-gray-400">Avg Order Time</p>
            <p className="text-sm font-bold" style={{ color: theme.text }}>
              {avgOrderTime.ordersCompletedToday > 0 ? `${avgOrderTime.avgOrderMinutes}m` : '—'}
            </p>
          </div>
        </div>
      )}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: `${theme.primary}15` }}>
            <ChefHat size={22} style={{ color: theme.primary }} />
          </div>
          <div>
            <h1 className="text-2xl font-bold" style={{ color: theme.text }}>Kitchen Display</h1>
            <p className="text-sm text-gray-500">Course lifecycle + docket detail | Auto-refresh 10s</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={fetchOrders} data-testid="refresh-kitchen-btn">
            <RotateCcw size={14} className="mr-1" /> Refresh
          </Button>
          {canConfigure && (
            <Dialog open={configDialog} onOpenChange={setConfigDialog}>
              <DialogTrigger asChild>
                <Button variant="outline" onClick={openConfigDialog} data-testid="docket-config-btn">
                  <Settings2 size={14} className="mr-1" /> Docket
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-lg">
                <DialogHeader><DialogTitle>Docket Display Settings</DialogTitle></DialogHeader>
                <div className="space-y-3 text-sm">
                  <p className="text-xs text-slate-500">Owner controls for what appears on every kitchen docket.</p>
                  {[
                    ['showStaffName', 'Show staff who put through the order'],
                    ['showDevice', 'Show device / tablet the order came from'],
                    ['showCovers', 'Show number of covers'],
                    ['showGuestName', 'Show guest name (from reservation)'],
                    ['showTable', 'Show table number'],
                    ['showFireTime', 'Show fire time per course'],
                    ['showElapsedTimer', 'Show elapsed timer since docket landed'],
                    ['showItemNotes', 'Show item-level notes'],
                    ['showOrderNotes', 'Show order-level notes'],
                    ['showModifiers', 'Show modifiers under each item'],
                    ['colourByCourse', 'Colour-code by course status'],
                  ].map(([key, label]) => (
                    <div key={key} className="flex items-center justify-between border-b pb-2">
                      <label htmlFor={`cfg-${key}`}>{label}</label>
                      <Switch
                        id={`cfg-${key}`}
                        checked={configDraft[key] !== false}
                        onCheckedChange={v => setConfigDraft(d => ({ ...d, [key]: v }))}
                        data-testid={`cfg-${key}`}
                      />
                    </div>
                  ))}
                  <div className="grid grid-cols-3 gap-3 pt-2">
                    <div>
                      <label className="text-xs text-slate-500">Font size</label>
                      <Select value={configDraft.fontSize || 'medium'} onValueChange={v => setConfigDraft(d => ({ ...d, fontSize: v }))}>
                        <SelectTrigger data-testid="cfg-fontSize"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="small">Small</SelectItem>
                          <SelectItem value="medium">Medium</SelectItem>
                          <SelectItem value="large">Large</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <label className="text-xs text-slate-500">Warn at (min)</label>
                      <Input type="number" value={configDraft.warnMinutes ?? 15}
                        onChange={e => setConfigDraft(d => ({ ...d, warnMinutes: parseInt(e.target.value, 10) || 0 }))}
                        data-testid="cfg-warnMinutes" />
                    </div>
                    <div>
                      <label className="text-xs text-slate-500">Critical at (min)</label>
                      <Input type="number" value={configDraft.criticalMinutes ?? 25}
                        onChange={e => setConfigDraft(d => ({ ...d, criticalMinutes: parseInt(e.target.value, 10) || 0 }))}
                        data-testid="cfg-criticalMinutes" />
                    </div>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setConfigDialog(false)}>Cancel</Button>
                  <Button onClick={saveConfig} data-testid="save-docket-config">Save</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          )}
          <Button onClick={openNewOrder} style={{ background: theme.primary }} data-testid="new-kitchen-order-btn">
            <Plus size={16} className="mr-1" /> New Order
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Active Orders', val: stats.total, color: theme.primary },
          { label: 'New', val: stats.newCount, color: '#3B82F6' },
          { label: 'Preparing', val: stats.prepCount, color: '#F59E0B' },
          { label: 'Ready to Serve', val: stats.readyCount, color: '#10B981' },
        ].map((s, i) => (
          <Card key={i} className="border-0 shadow-sm">
            <CardContent className="p-4">
              <p className="text-3xl font-bold" style={{ color: s.color }}>{s.val}</p>
              <p className="text-xs text-gray-500 mt-1">{s.label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Kanban */}
      <div className="grid grid-cols-3 gap-4" data-testid="kitchen-kanban">
        <div>
          <div className="flex items-center gap-2 mb-3 px-1">
            <Bell size={16} className="text-blue-500" />
            <h2 className="font-semibold text-sm">New Orders</h2>
            <Badge className="bg-blue-100 text-blue-700 text-xs ml-auto">{newOrders.length}</Badge>
          </div>
          <div className="space-y-0 min-h-[200px]">
            {newOrders.length === 0 && <p className="text-xs text-gray-400 text-center py-8">No new orders</p>}
            {newOrders.map(renderOrderCard)}
          </div>
        </div>
        <div>
          <div className="flex items-center gap-2 mb-3 px-1">
            <Flame size={16} className="text-amber-500" />
            <h2 className="font-semibold text-sm">Preparing</h2>
            <Badge className="bg-amber-100 text-amber-700 text-xs ml-auto">{preparing.length}</Badge>
          </div>
          <div className="space-y-0 min-h-[200px]">
            {preparing.length === 0 && <p className="text-xs text-gray-400 text-center py-8">Nothing in progress</p>}
            {preparing.map(renderOrderCard)}
          </div>
        </div>
        <div>
          <div className="flex items-center gap-2 mb-3 px-1">
            <Check size={16} className="text-green-500" />
            <h2 className="font-semibold text-sm">Ready to Serve</h2>
            <Badge className="bg-green-100 text-green-700 text-xs ml-auto">{ready.length}</Badge>
          </div>
          <div className="space-y-0 min-h-[200px]">
            {ready.length === 0 && <p className="text-xs text-gray-400 text-center py-8">No orders ready</p>}
            {ready.map(renderOrderCard)}
          </div>
        </div>
      </div>

      {/* New Order Dialog */}
      <Dialog open={newOrderDialog} onOpenChange={setNewOrderDialog}>
        <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto" data-testid="new-kitchen-order-dialog">
          <DialogHeader>
            <DialogTitle>Send to Kitchen</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-gray-500 mb-1 block">Table #</label>
                <Input value={orderForm.tableNumber} onChange={e => setOrderForm(f => ({ ...f, tableNumber: e.target.value }))}
                  placeholder="e.g. 4" data-testid="ko-table-input" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500 mb-1 block">Covers</label>
                <Input type="number" value={orderForm.covers} onChange={e => setOrderForm(f => ({ ...f, covers: e.target.value }))}
                  placeholder="# guests" data-testid="ko-covers-input" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500 mb-1 block">Type</label>
                <Select value={orderForm.orderType} onValueChange={v => setOrderForm(f => ({ ...f, orderType: v }))}>
                  <SelectTrigger data-testid="ko-type-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="dine_in">Dine In</SelectItem>
                    <SelectItem value="takeaway">Takeaway</SelectItem>
                    <SelectItem value="delivery">Delivery</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500 mb-1 block">Priority</label>
                <Select value={orderForm.priority} onValueChange={v => setOrderForm(f => ({ ...f, priority: v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="normal">Normal</SelectItem>
                    <SelectItem value="rush">Rush</SelectItem>
                    <SelectItem value="vip">VIP</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Device label (optional)</label>
              <Input value={orderForm.deviceLabel} onChange={e => setOrderForm(f => ({ ...f, deviceLabel: e.target.value }))}
                placeholder="Front POS / Tablet 3 / Online" data-testid="ko-device-input" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Add Item</label>
              <div className="flex gap-2">
                <Select value={selectedProduct} onValueChange={setSelectedProduct}>
                  <SelectTrigger className="flex-1" data-testid="ko-product-select"><SelectValue placeholder="Select product" /></SelectTrigger>
                  <SelectContent>
                    {products.map(p => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
                  </SelectContent>
                </Select>
                <Select value={String(selectedCourse)} onValueChange={v => setSelectedCourse(parseInt(v, 10))}>
                  <SelectTrigger className="w-28" data-testid="ko-course-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">Starter</SelectItem>
                    <SelectItem value="2">Main</SelectItem>
                    <SelectItem value="3">Dessert</SelectItem>
                    <SelectItem value="4">Coffee</SelectItem>
                  </SelectContent>
                </Select>
                <Button variant="outline" onClick={addItemToOrder} data-testid="ko-add-item-btn"><Plus size={14} /></Button>
              </div>
            </div>
            {orderForm.items.length > 0 && (
              <div className="space-y-1">
                <label className="text-xs font-medium text-gray-500">Items</label>
                {orderForm.items.map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between bg-gray-50 rounded px-3 py-2 text-sm">
                    <span>{item.quantity}x {item.productName} <Badge variant="outline" className="ml-1 text-[9px]">{COURSE_LABEL[item.course] || `C${item.course}`}</Badge></span>
                    <Button variant="ghost" size="sm" className="h-6 px-1" onClick={() => removeItemFromOrder(idx)}>
                      <X size={12} />
                    </Button>
                  </div>
                ))}
              </div>
            )}
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Kitchen Notes</label>
              <Input value={orderForm.notes} onChange={e => setOrderForm(f => ({ ...f, notes: e.target.value }))}
                placeholder="Special instructions..." data-testid="ko-notes-input" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setNewOrderDialog(false)}>Cancel</Button>
            <Button onClick={handleCreateOrder} style={{ background: theme.primary }} data-testid="send-to-kitchen-btn">
              <ChefHat size={14} className="mr-1" /> Send to Kitchen
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
