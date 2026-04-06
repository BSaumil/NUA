import React, { useState, useEffect, useCallback } from 'react';
import {
  ChefHat, Clock, Flame, Bell, Check, X, AlertTriangle, Plus,
  UtensilsCrossed, ArrowRight, RotateCcw, Zap, Timer
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter
} from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import { useTheme } from '../contexts/ThemeContext';
import { kitchenAPI, productsAPI } from '../services/api';
import { toast } from 'sonner';

const STATUS_CONFIG = {
  new: { label: 'New', color: '#3B82F6', bg: '#EFF6FF', icon: Bell },
  preparing: { label: 'Preparing', color: '#F59E0B', bg: '#FFFBEB', icon: Flame },
  ready: { label: 'Ready', color: '#10B981', bg: '#ECFDF5', icon: Check },
  served: { label: 'Served', color: '#6B7280', bg: '#F3F4F6', icon: UtensilsCrossed },
};

const PRIORITY_CONFIG = {
  normal: { label: 'Normal', color: '#6B7280' },
  rush: { label: 'RUSH', color: '#EF4444' },
  vip: { label: 'VIP', color: '#F59E0B' },
};

export default function Kitchen() {
  const { theme } = useTheme();
  const [orders, setOrders] = useState([]);
  const [filter, setFilter] = useState('active'); // active, new, preparing, ready, all
  const [newOrderDialog, setNewOrderDialog] = useState(false);
  const [products, setProducts] = useState([]);
  const [orderForm, setOrderForm] = useState({
    tableNumber: '', orderType: 'dine_in', items: [], notes: '', priority: 'normal'
  });
  const [selectedProduct, setSelectedProduct] = useState('');

  const fetchOrders = useCallback(async () => {
    try {
      const params = {};
      if (filter !== 'active' && filter !== 'all') params.status = filter;
      const res = await kitchenAPI.getOrders(params);
      setOrders(res.data);
    } catch (e) { console.error(e); }
  }, [filter]);

  useEffect(() => { fetchOrders(); }, [fetchOrders]);
  // Auto-refresh every 10 seconds
  useEffect(() => {
    const interval = setInterval(fetchOrders, 10000);
    return () => clearInterval(interval);
  }, [fetchOrders]);

  const fetchProducts = async () => {
    try {
      const res = await productsAPI.getAll();
      setProducts(res.data);
    } catch (e) { console.error(e); }
  };

  const handleStart = async (id) => {
    try { await kitchenAPI.startOrder(id); toast.success('Order started'); fetchOrders(); }
    catch (e) { toast.error('Failed'); }
  };

  const handleReady = async (id) => {
    try { await kitchenAPI.readyOrder(id); toast.success('Order marked ready'); fetchOrders(); }
    catch (e) { toast.error('Failed'); }
  };

  const handleServed = async (id) => {
    try { await kitchenAPI.servedOrder(id); toast.success('Order served'); fetchOrders(); }
    catch (e) { toast.error('Failed'); }
  };

  const handleCancel = async (id) => {
    try { await kitchenAPI.cancelOrder(id); toast.warning('Order cancelled'); fetchOrders(); }
    catch (e) { toast.error('Failed'); }
  };

  const handlePriority = async (id, priority) => {
    try { await kitchenAPI.setPriority(id, priority); toast.success(`Priority set to ${priority}`); fetchOrders(); }
    catch (e) { toast.error('Failed'); }
  };

  const handleFireCourse = async (id, course) => {
    try { await kitchenAPI.fireCourse(id, course); toast.success(`Course ${course} fired`); fetchOrders(); }
    catch (e) { toast.error('Failed'); }
  };

  const openNewOrder = () => {
    fetchProducts();
    setOrderForm({ tableNumber: '', orderType: 'dine_in', items: [], notes: '', priority: 'normal' });
    setNewOrderDialog(true);
  };

  const addItemToOrder = () => {
    if (!selectedProduct) return;
    const product = products.find(p => p.id === selectedProduct);
    if (!product) return;
    setOrderForm(f => ({
      ...f,
      items: [...f.items, { productId: product.id, productName: product.name, quantity: 1, course: 1, status: 'pending', notes: '' }]
    }));
    setSelectedProduct('');
  };

  const removeItemFromOrder = (idx) => {
    setOrderForm(f => ({ ...f, items: f.items.filter((_, i) => i !== idx) }));
  };

  const handleCreateOrder = async () => {
    if (orderForm.items.length === 0) { toast.error('Add at least one item'); return; }
    try {
      await kitchenAPI.createOrder(orderForm);
      toast.success('Order sent to kitchen');
      setNewOrderDialog(false);
      fetchOrders();
    } catch (e) { toast.error('Failed to create order'); }
  };

  const getTimeSince = (isoStr) => {
    if (!isoStr) return '—';
    const diff = Math.round((new Date() - new Date(isoStr)) / 60000);
    if (diff < 1) return '<1m';
    return `${diff}m`;
  };

  // Filter
  const displayed = filter === 'active'
    ? orders.filter(o => ['new', 'preparing', 'ready'].includes(o.status))
    : filter === 'all' ? orders : orders.filter(o => o.status === filter);

  // Sort: rush first, then by time
  const sorted = [...displayed].sort((a, b) => {
    if (a.priority === 'rush' && b.priority !== 'rush') return -1;
    if (b.priority === 'rush' && a.priority !== 'rush') return 1;
    if (a.priority === 'vip' && b.priority === 'normal') return -1;
    if (b.priority === 'vip' && a.priority === 'normal') return 1;
    return new Date(a.createdAt) - new Date(b.createdAt);
  });

  // Column view
  const newOrders = sorted.filter(o => o.status === 'new');
  const preparing = sorted.filter(o => o.status === 'preparing');
  const ready = sorted.filter(o => o.status === 'ready');

  const stats = {
    total: orders.filter(o => ['new', 'preparing', 'ready'].includes(o.status)).length,
    newCount: newOrders.length,
    prepCount: preparing.length,
    readyCount: ready.length,
  };

  const renderOrderCard = (order) => {
    const sc = STATUS_CONFIG[order.status] || STATUS_CONFIG.new;
    const pc = PRIORITY_CONFIG[order.priority] || PRIORITY_CONFIG.normal;
    const isRush = order.priority === 'rush';
    const isVip = order.priority === 'vip';

    return (
      <Card key={order.id} className={`border-0 shadow-sm mb-3 ${isRush ? 'ring-2 ring-red-300' : ''} ${isVip ? 'ring-2 ring-amber-300' : ''}`}
        data-testid={`kitchen-order-${order.id}`}>
        <CardContent className="p-4">
          {/* Header */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              {order.tableNumber && (
                <Badge variant="outline" className="font-mono font-bold">T{order.tableNumber}</Badge>
              )}
              <span className="text-xs font-mono text-gray-400">{order.id.slice(0, 11)}</span>
              {(isRush || isVip) && (
                <Badge style={{ background: pc.color, color: 'white' }} className="text-[10px] animate-pulse">
                  {pc.label}
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-1 text-xs text-gray-400">
              <Timer size={12} />
              {getTimeSince(order.createdAt)}
            </div>
          </div>

          {/* Items */}
          <div className="space-y-1.5 mb-3">
            {(order.items || []).map((item, idx) => (
              <div key={idx} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-xs w-5 text-center" style={{ color: theme.primary }}>
                    {item.quantity}x
                  </span>
                  <span className="font-medium" style={{ color: theme.text }}>{item.productName}</span>
                </div>
                {item.course > 1 && <Badge variant="outline" className="text-[10px]">C{item.course}</Badge>}
              </div>
            ))}
          </div>

          {/* Notes */}
          {order.notes && (
            <div className="text-xs text-orange-600 bg-orange-50 px-2 py-1 rounded mb-3">
              {order.notes}
            </div>
          )}

          {/* Order type */}
          <div className="flex items-center gap-2 mb-3">
            <Badge variant="outline" className="text-[10px] capitalize">{order.orderType?.replace('_', ' ')}</Badge>
            {order.currentCourse > 1 && (
              <Badge className="bg-purple-100 text-purple-700 text-[10px]">Course {order.currentCourse}</Badge>
            )}
          </div>

          {/* Actions */}
          <div className="flex gap-1.5 flex-wrap">
            {order.status === 'new' && (
              <>
                <Button size="sm" className="h-7 text-xs bg-amber-500 hover:bg-amber-600" onClick={() => handleStart(order.id)}
                  data-testid={`start-order-${order.id}`}>
                  <Flame size={12} className="mr-1" /> Start
                </Button>
                <Button size="sm" variant="outline" className="h-7 text-xs text-red-500" onClick={() => handlePriority(order.id, 'rush')}
                  data-testid={`rush-order-${order.id}`}>
                  <Zap size={12} className="mr-1" /> Rush
                </Button>
              </>
            )}
            {order.status === 'preparing' && (
              <>
                <Button size="sm" className="h-7 text-xs bg-green-600 hover:bg-green-700" onClick={() => handleReady(order.id)}
                  data-testid={`ready-order-${order.id}`}>
                  <Check size={12} className="mr-1" /> Ready
                </Button>
                <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => handleFireCourse(order.id, (order.currentCourse || 1) + 1)}
                  data-testid={`fire-course-${order.id}`}>
                  <ArrowRight size={12} className="mr-1" /> Fire C{(order.currentCourse || 1) + 1}
                </Button>
              </>
            )}
            {order.status === 'ready' && (
              <Button size="sm" className="h-7 text-xs" style={{ background: theme.primary }} onClick={() => handleServed(order.id)}
                data-testid={`served-order-${order.id}`}>
                <UtensilsCrossed size={12} className="mr-1" /> Served
              </Button>
            )}
            <Button size="sm" variant="ghost" className="h-7 text-xs text-red-400 hover:text-red-600" onClick={() => handleCancel(order.id)}
              data-testid={`cancel-kitchen-${order.id}`}>
              <X size={12} />
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="space-y-6" data-testid="kitchen-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: `${theme.primary}15` }}>
            <ChefHat size={22} style={{ color: theme.primary }} />
          </div>
          <div>
            <h1 className="text-2xl font-bold" style={{ color: theme.text }}>Kitchen Display</h1>
            <p className="text-sm text-gray-500">Real-time order management | Auto-refresh 10s</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={fetchOrders} data-testid="refresh-kitchen-btn">
            <RotateCcw size={14} className="mr-1" /> Refresh
          </Button>
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

      {/* Kanban Columns */}
      <div className="grid grid-cols-3 gap-4" data-testid="kitchen-kanban">
        {/* New */}
        <div>
          <div className="flex items-center gap-2 mb-3 px-1">
            <Bell size={16} className="text-blue-500" />
            <h2 className="font-semibold text-sm" style={{ color: theme.text }}>New Orders</h2>
            <Badge className="bg-blue-100 text-blue-700 text-xs ml-auto">{newOrders.length}</Badge>
          </div>
          <div className="space-y-0 min-h-[200px]">
            {newOrders.length === 0 && <p className="text-xs text-gray-400 text-center py-8">No new orders</p>}
            {newOrders.map(renderOrderCard)}
          </div>
        </div>
        {/* Preparing */}
        <div>
          <div className="flex items-center gap-2 mb-3 px-1">
            <Flame size={16} className="text-amber-500" />
            <h2 className="font-semibold text-sm" style={{ color: theme.text }}>Preparing</h2>
            <Badge className="bg-amber-100 text-amber-700 text-xs ml-auto">{preparing.length}</Badge>
          </div>
          <div className="space-y-0 min-h-[200px]">
            {preparing.length === 0 && <p className="text-xs text-gray-400 text-center py-8">Nothing in progress</p>}
            {preparing.map(renderOrderCard)}
          </div>
        </div>
        {/* Ready */}
        <div>
          <div className="flex items-center gap-2 mb-3 px-1">
            <Check size={16} className="text-green-500" />
            <h2 className="font-semibold text-sm" style={{ color: theme.text }}>Ready to Serve</h2>
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
                  placeholder="Table number" data-testid="ko-table-input" />
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
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Add Item</label>
              <div className="flex gap-2">
                <Select value={selectedProduct} onValueChange={setSelectedProduct}>
                  <SelectTrigger className="flex-1" data-testid="ko-product-select"><SelectValue placeholder="Select product" /></SelectTrigger>
                  <SelectContent>
                    {products.map(p => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
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
                    <span>{item.quantity}x {item.productName}</span>
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
