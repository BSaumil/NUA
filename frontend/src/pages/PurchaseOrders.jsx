import React, { useState, useEffect } from 'react';
import { Truck, Plus, Package, RefreshCw, Mail, MailWarning, FileDown, Pencil, Save, X } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { phaseEFAPI } from '../services/api';
import { toast } from 'sonner';

const STATUS_COLORS = { draft: 'bg-gray-100 text-gray-700', approved: 'bg-blue-100 text-blue-700', sent: 'bg-amber-100 text-amber-700', received: 'bg-green-100 text-green-700', cancelled: 'bg-red-100 text-red-700' };

// Groups a PO's flat item list by category so it reads like an order sheet
// a supplier can actually pack from, not an alphabetical dump.
function groupByCategory(items) {
  const groups = {};
  for (const it of items || []) {
    const cat = it.category || 'Uncategorised';
    (groups[cat] = groups[cat] || []).push(it);
  }
  return Object.keys(groups).sort().map(cat => ({ category: cat, items: groups[cat] }));
}

export default function PurchaseOrders() {
  const { theme } = useTheme();
  const { user } = useAuth();
  const isOwner = user?.role === 'owner';
  const [pos, setPos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [draftItems, setDraftItems] = useState([]);
  const [saving, setSaving] = useState(false);

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
  const act = async (id, action) => {
    try {
      const r = await phaseEFAPI.updatePO(id, action);
      if (action === 'send') {
        const er = r.data?.emailResult;
        if (er?.delivered) toast.success('PO emailed to the supplier');
        else if (er?.reason === 'no_supplier_email_on_file') toast.warning('PO marked sent — but this supplier has no email on file, so nothing actually went out');
        else toast.warning('PO marked sent — but email isn’t configured, so nothing actually went out');
      } else {
        toast.success(`PO ${action}d`);
      }
      refresh();
    } catch (e) { toast.error('Failed'); }
  };

  const startEdit = (po) => { setEditingId(po.id); setDraftItems((po.items || []).map(it => ({ ...it }))); };
  const cancelEdit = () => { setEditingId(null); setDraftItems([]); };
  const updateDraftItem = (idx, field, value) => {
    setDraftItems(prev => prev.map((it, i) => i === idx ? { ...it, [field]: value } : it));
  };
  const saveEdit = async (poId) => {
    setSaving(true);
    try {
      const items = draftItems.map(it => ({ ...it, orderQty: Number(it.orderQty), unitCost: Number(it.unitCost) }));
      await phaseEFAPI.editPO(poId, items);
      toast.success('Purchase order updated');
      setEditingId(null);
      refresh();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Could not save changes');
    } finally { setSaving(false); }
  };

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
        {pos.map(po => {
          const editable = isOwner && (po.status === 'draft' || po.status === 'approved');
          const isEditing = editingId === po.id;
          const groups = groupByCategory(isEditing ? draftItems : po.items);
          return (
            <Card key={po.id} data-testid={`po-${po.id}`}>
              <CardContent className="p-5">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-bold">{po.supplier}</h3>
                      <Badge className={STATUS_COLORS[po.status] || 'bg-gray-100'}>{po.status}</Badge>
                    </div>
                    <p className="text-xs text-gray-500 font-mono">{po.id} · {new Date(po.createdAt).toLocaleString()}</p>
                    {po.emailResult && (
                      <p className={`text-xs mt-1 flex items-center gap-1 ${po.emailResult.delivered ? 'text-emerald-600' : 'text-amber-600'}`}
                        data-testid={`po-email-status-${po.id}`}>
                        {po.emailResult.delivered
                          ? <><Mail size={11} /> Emailed to supplier</>
                          : <><MailWarning size={11} /> {po.emailResult.reason === 'no_supplier_email_on_file'
                              ? 'No supplier email on file — not actually sent'
                              : 'Email not configured — not actually sent'}</>}
                      </p>
                    )}
                  </div>
                  <div className="flex items-start gap-3">
                    <a href={phaseEFAPI.poPdfUrl(po.id)} target="_blank" rel="noreferrer"
                       className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-800 border rounded px-2 py-1"
                       data-testid={`po-pdf-${po.id}`}>
                      <FileDown size={13} /> PDF
                    </a>
                    <div className="text-right">
                      <p className="text-xs text-gray-500 uppercase">Total</p>
                      <p className="text-xl font-bold" style={{ color: theme.primary }}>${(po.totalCost || 0).toFixed(2)}</p>
                    </div>
                  </div>
                </div>

                <div className="bg-gray-50 rounded-lg p-3 space-y-3 mb-3">
                  {groups.map(g => (
                    <div key={g.category}>
                      <p className="text-[11px] font-bold uppercase tracking-wide text-gray-400 mb-1">{g.category}</p>
                      <div className="space-y-1.5">
                        {g.items.map((it) => {
                          const idx = draftItems.indexOf(it);
                          return (
                            <div key={it.productId} className="flex justify-between items-center text-sm" data-testid={`po-item-${po.id}-${it.productId}`}>
                              <span className="flex items-center gap-1.5"><Package size={12} className="text-gray-400" /> {it.productName} <span className="text-gray-400 text-xs">(stock: {it.currentStock})</span></span>
                              {isEditing ? (
                                <span className="flex items-center gap-1.5 font-mono">
                                  <Input type="number" min="1" value={it.orderQty} onChange={e => updateDraftItem(idx, 'orderQty', e.target.value)}
                                         className="w-16 h-7 text-xs" data-testid={`po-edit-qty-${po.id}-${it.productId}`} />
                                  x @ $
                                  <Input type="number" min="0" step="0.01" value={it.unitCost} onChange={e => updateDraftItem(idx, 'unitCost', e.target.value)}
                                         className="w-20 h-7 text-xs" data-testid={`po-edit-cost-${po.id}-${it.productId}`} />
                                </span>
                              ) : (
                                <span className="font-mono">{it.orderQty}x @ ${(it.unitCost || 0).toFixed(2)}</span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="flex gap-2">
                  {isEditing ? (
                    <>
                      <Button size="sm" onClick={() => saveEdit(po.id)} disabled={saving} style={{ backgroundColor: theme.primary }} data-testid={`po-save-${po.id}`}>
                        <Save size={13} className="mr-1" /> Save
                      </Button>
                      <Button size="sm" variant="outline" onClick={cancelEdit} data-testid={`po-cancel-edit-${po.id}`}>
                        <X size={13} className="mr-1" /> Cancel
                      </Button>
                    </>
                  ) : (
                    <>
                      {editable && (
                        <Button size="sm" variant="outline" onClick={() => startEdit(po)} data-testid={`po-edit-${po.id}`}>
                          <Pencil size={13} className="mr-1" /> Edit
                        </Button>
                      )}
                      {po.status === 'draft' && <Button size="sm" onClick={() => act(po.id, 'approve')} data-testid={`approve-po-${po.id}`}>Approve</Button>}
                      {po.status === 'approved' && <Button size="sm" onClick={() => act(po.id, 'send')} data-testid={`send-po-${po.id}`}>Send to Supplier</Button>}
                      {po.status === 'sent' && <Button size="sm" style={{ backgroundColor: theme.primary }} onClick={() => act(po.id, 'receive')} data-testid={`receive-po-${po.id}`}>Mark Received (+ stock)</Button>}
                      {po.status !== 'received' && po.status !== 'cancelled' && <Button size="sm" variant="outline" className="text-red-500" onClick={() => act(po.id, 'cancel')}>Cancel</Button>}
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
        {pos.length === 0 && <Card className="border-dashed"><CardContent className="py-12 text-center text-gray-400"><Truck size={40} className="mx-auto mb-3 opacity-30" /><p>No purchase orders yet. Click "Auto-Generate POs" to create from low-stock items.</p></CardContent></Card>}
      </div>
    </div>
  );
}
