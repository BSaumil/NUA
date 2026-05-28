import React, { useState, useEffect } from 'react';
import { Truck, Plus, Package, RefreshCw } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { useTheme } from '../contexts/ThemeContext';
import { phaseEFAPI } from '../services/api';
import { toast } from 'sonner';

const STATUS_COLORS = { draft: 'bg-gray-100 text-gray-700', approved: 'bg-blue-100 text-blue-700', sent: 'bg-amber-100 text-amber-700', received: 'bg-green-100 text-green-700', cancelled: 'bg-red-100 text-red-700' };

export default function PurchaseOrders() {
  const { theme } = useTheme();
  const [pos, setPos] = useState([]);
  const [loading, setLoading] = useState(false);

  const refresh = async () => { try { const r = await phaseEFAPI.getPOs(); setPos(r.data || []); } catch {} };
  useEffect(() => { refresh(); }, []);

  const generate = async () => {
    setLoading(true);
    try {
      const r = await phaseEFAPI.generatePOs();
      toast.success(`Generated ${r.data?.created || 0} purchase orders`);
      refresh();
    } catch { toast.error('PO generation failed'); }
    setLoading(false);
  };
  const act = async (id, action) => { try { await phaseEFAPI.updatePO(id, action); toast.success(`PO ${action}d`); refresh(); } catch (e) { toast.error('Failed'); } };

  return (
    <div className="space-y-6" data-testid="po-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Truck size={22} /> Purchase Orders</h1>
          <p className="text-sm text-gray-500">Auto-generated from low-stock products, grouped by supplier.</p>
        </div>
        <Button onClick={generate} disabled={loading} style={{ backgroundColor: theme.primary }} data-testid="generate-po-btn">
          {loading ? <RefreshCw size={14} className="mr-1 animate-spin" /> : <Plus size={14} className="mr-1" />} Auto-Generate POs
        </Button>
      </div>

      <div className="space-y-3">
        {pos.map(po => (
          <Card key={po.id} data-testid={`po-${po.id}`}>
            <CardContent className="p-5">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-bold">{po.supplier}</h3>
                    <Badge className={STATUS_COLORS[po.status] || 'bg-gray-100'}>{po.status}</Badge>
                  </div>
                  <p className="text-xs text-gray-500 font-mono">{po.id} · {new Date(po.createdAt).toLocaleString()}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-gray-500 uppercase">Total</p>
                  <p className="text-xl font-bold" style={{ color: theme.primary }}>${(po.totalCost || 0).toFixed(2)}</p>
                </div>
              </div>
              <div className="bg-gray-50 rounded-lg p-3 space-y-1.5 mb-3">
                {(po.items || []).map((it, i) => (
                  <div key={i} className="flex justify-between text-sm" data-testid={`po-item-${po.id}-${i}`}>
                    <span className="flex items-center gap-1.5"><Package size={12} className="text-gray-400" /> {it.productName} <span className="text-gray-400 text-xs">(stock: {it.currentStock})</span></span>
                    <span className="font-mono">{it.orderQty}x @ ${(it.unitCost || 0).toFixed(2)}</span>
                  </div>
                ))}
              </div>
              <div className="flex gap-2">
                {po.status === 'draft' && <Button size="sm" onClick={() => act(po.id, 'approve')} data-testid={`approve-po-${po.id}`}>Approve</Button>}
                {po.status === 'approved' && <Button size="sm" onClick={() => act(po.id, 'send')} data-testid={`send-po-${po.id}`}>Send to Supplier</Button>}
                {po.status === 'sent' && <Button size="sm" style={{ backgroundColor: theme.primary }} onClick={() => act(po.id, 'receive')} data-testid={`receive-po-${po.id}`}>Mark Received (+ stock)</Button>}
                {po.status !== 'received' && po.status !== 'cancelled' && <Button size="sm" variant="outline" className="text-red-500" onClick={() => act(po.id, 'cancel')}>Cancel</Button>}
              </div>
            </CardContent>
          </Card>
        ))}
        {pos.length === 0 && <Card className="border-dashed"><CardContent className="py-12 text-center text-gray-400"><Truck size={40} className="mx-auto mb-3 opacity-30" /><p>No purchase orders yet. Click "Auto-Generate POs" to create from low-stock items.</p></CardContent></Card>}
      </div>
    </div>
  );
}
