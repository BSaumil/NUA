/* v26 admin pages — Vouchers Manager, Events & Experiences, Staff Availability,
 * Gift Card Sale form (rich), Subscription Editor.
 * Owner/manager editable, barcode-aware.
 */
import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { useToast } from '../hooks/use-toast';
import { useTheme } from '../contexts/ThemeContext';
import { v26API, customersAPI } from '../services/api';
import Barcode128 from '../components/Barcode128';
import {
  Ticket, Gift, Calendar, CalendarDays, Users2, Plus, Edit2, Trash2,
  Barcode, Save, Sparkles, CheckCircle,
} from 'lucide-react';

export { Barcode128 };

// =============================================================================
// VOUCHERS MANAGER
// =============================================================================
export function VoucherManager() {
  const { theme } = useTheme(); const { toast } = useToast();
  const [rows, setRows] = useState([]);
  const [editing, setEditing] = useState(null);
  const [showCode, setShowCode] = useState(null);

  const load = () => v26API.listVouchers().then(r => setRows(r.data || []));
  useEffect(() => { load(); }, []);

  const blank = () => ({
    name: '', kind: 'discount', discountType: 'percent', value: 10,
    appliesTo: 'cart', minSpend: 0, maxUses: 0,
    validFrom: null, validTo: null, termsAndConditions: '', active: true,
  });

  const save = async () => {
    try {
      let res;
      if (editing.id) {
        res = await v26API.updateVoucher(editing.id, editing);
        toast({ title: 'Saved' });
      } else {
        res = await v26API.createVoucher(editing);
        const gc = res?.data?.giftCard;
        if (gc) {
          toast({
            title: 'Gift voucher created',
            description: `Card ${gc.code} pending activation ($${gc.initialBalance.toFixed(2)}). Activates on POS sale.`,
          });
        } else {
          toast({ title: 'Saved' });
        }
      }
      setEditing(null); load();
    } catch (e) { toast({ title: 'Failed', description: e?.response?.data?.detail, variant: 'destructive' }); }
  };

  const remove = async (id) => {
    if (!window.confirm('Delete this voucher?')) return;
    try { await v26API.deleteVoucher(id); toast({ title: 'Deleted' }); load(); }
    catch (e) { toast({ title: 'Failed', variant: 'destructive' }); }
  };

  return (
    <div className="space-y-6" data-testid="voucher-manager-page">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
          <Ticket className="text-rose-600" /> Vouchers, Coupons & Marketing Codes
        </h1>
        <Button onClick={() => setEditing(blank())} style={{ background: theme.primary }} data-testid="new-voucher-btn">
          <Plus size={14} className="mr-1.5" /> New Code
        </Button>
      </div>

      {/* List */}
      <Card><CardContent className="p-0">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase tracking-wider text-gray-500">
            <tr>
              <th className="text-left px-5 py-3">Name</th>
              <th className="text-left px-5 py-3">Code</th>
              <th className="text-left px-5 py-3">Type</th>
              <th className="text-right px-5 py-3">Value</th>
              <th className="text-right px-5 py-3">Used</th>
              <th className="text-left px-5 py-3">Status</th>
              <th className="text-right px-5 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? <tr><td colSpan={7} className="text-center py-8 text-gray-400">No vouchers — create one</td></tr> :
              rows.map(v => (
                <tr key={v.id} className="border-t hover:bg-gray-50" data-testid={`voucher-row-${v.id}`}>
                  <td className="px-5 py-3 font-medium">{v.name}</td>
                  <td className="px-5 py-3 font-mono text-xs">{v.manualCode}</td>
                  <td className="px-5 py-3"><Badge variant="outline" className="text-[10px]">{v.kind} · {v.discountType}</Badge></td>
                  <td className="px-5 py-3 text-right">{v.discountType === 'percent' ? `${v.value}%` : `$${v.value}`}</td>
                  <td className="px-5 py-3 text-right">{v.usedCount}{v.maxUses > 0 ? `/${v.maxUses}` : ''}</td>
                  <td className="px-5 py-3"><Badge className={v.active ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-200 text-gray-700'}>{v.active ? 'active' : 'disabled'}</Badge></td>
                  <td className="px-5 py-3 text-right flex justify-end gap-1">
                    <Button size="sm" variant="ghost" onClick={() => setShowCode(v)} data-testid={`view-code-${v.id}`}><Barcode size={14} /></Button>
                    <Button size="sm" variant="ghost" onClick={() => setEditing(v)} data-testid={`edit-${v.id}`}><Edit2 size={14} /></Button>
                    <Button size="sm" variant="ghost" onClick={() => remove(v.id)} data-testid={`del-${v.id}`}><Trash2 size={14} /></Button>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </CardContent></Card>

      {/* Editor */}
      {editing && (
        <Card className="border-amber-300"><CardContent className="p-5 space-y-3" data-testid="voucher-editor">
          <h2 className="font-bold text-lg">{editing.id ? 'Edit' : 'New'} Code</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <div><label className="text-xs uppercase text-gray-500">Name</label>
              <Input value={editing.name} onChange={e => setEditing({ ...editing, name: e.target.value })} /></div>
            <div><label className="text-xs uppercase text-gray-500">Kind</label>
              <select className="w-full p-2 border rounded text-sm" value={editing.kind} onChange={e => setEditing({ ...editing, kind: e.target.value })}>
                <option>discount</option><option>freebie</option><option>bundle</option><option>gift</option><option>marketing</option>
              </select></div>
            <div><label className="text-xs uppercase text-gray-500">Discount Type</label>
              <select className="w-full p-2 border rounded text-sm" value={editing.discountType} onChange={e => setEditing({ ...editing, discountType: e.target.value })}>
                <option value="percent">% off</option><option value="fixed">$ off</option><option value="free_item">free cheapest item</option>
              </select></div>
            <div><label className="text-xs uppercase text-gray-500">Value</label>
              <Input type="number" value={editing.value} onChange={e => setEditing({ ...editing, value: parseFloat(e.target.value) || 0 })} /></div>
            <div><label className="text-xs uppercase text-gray-500">Min Spend $</label>
              <Input type="number" value={editing.minSpend} onChange={e => setEditing({ ...editing, minSpend: parseFloat(e.target.value) || 0 })} /></div>
            <div><label className="text-xs uppercase text-gray-500">Max Uses (0=∞)</label>
              <Input type="number" value={editing.maxUses} onChange={e => setEditing({ ...editing, maxUses: parseInt(e.target.value) || 0 })} /></div>
            <div><label className="text-xs uppercase text-gray-500">Valid From</label>
              <Input type="datetime-local" value={(editing.validFrom || '').slice(0, 16)} onChange={e => setEditing({ ...editing, validFrom: e.target.value })} /></div>
            <div><label className="text-xs uppercase text-gray-500">Valid To</label>
              <Input type="datetime-local" value={(editing.validTo || '').slice(0, 16)} onChange={e => setEditing({ ...editing, validTo: e.target.value })} /></div>
            <div><label className="text-xs uppercase text-gray-500">Active</label>
              <div className="flex items-center h-10"><input type="checkbox" checked={editing.active} onChange={e => setEditing({ ...editing, active: e.target.checked })} /></div></div>
          </div>
          <div><label className="text-xs uppercase text-gray-500">Terms & Conditions</label>
            <Textarea rows={3} value={editing.termsAndConditions} onChange={e => setEditing({ ...editing, termsAndConditions: e.target.value })} /></div>
          <div className="flex gap-2">
            <Button onClick={save} style={{ background: theme.primary }} data-testid="save-voucher"><Save size={14} className="mr-1.5" /> Save</Button>
            <Button variant="outline" onClick={() => setEditing(null)}>Cancel</Button>
          </div>
        </CardContent></Card>
      )}

      {/* Barcode preview modal */}
      {showCode && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-6" onClick={() => setShowCode(null)} data-testid="barcode-modal">
          <Card onClick={e => e.stopPropagation()} className="max-w-md w-full"><CardContent className="p-6 text-center space-y-4">
            <h3 className="font-bold">{showCode.name}</h3>
            <Barcode128 value={showCode.manualCode} />
            <p className="text-xs text-gray-500">Scan at POS or type code manually</p>
            <Button onClick={() => setShowCode(null)}>Close</Button>
          </CardContent></Card>
        </div>
      )}
    </div>
  );
}


// =============================================================================
// EVENTS & EXPERIENCES
// =============================================================================
export function EventsManager() {
  const { theme } = useTheme(); const { toast } = useToast();
  const [rows, setRows] = useState([]);
  const [editing, setEditing] = useState(null);
  const [aiPreview, setAiPreview] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);

  const load = () => v26API.listEvents().then(r => setRows(r.data || []));
  useEffect(() => { load(); }, []);

  const blank = () => ({
    title: '', description: '', date: new Date().toISOString().slice(0, 10),
    startTime: '18:00', endTime: '21:00', capacity: 30, pricePerGuest: 0,
    category: 'experience', termsAndConditions: '',
  });

  const save = async () => {
    try {
      if (editing.id) await v26API.updateEvent(editing.id, editing);
      else await v26API.createEvent(editing);
      toast({ title: 'Saved' }); setEditing(null); load();
    } catch (e) { toast({ title: 'Failed', description: e?.response?.data?.detail, variant: 'destructive' }); }
  };

  const previewMarketing = async (date) => {
    setAiLoading(true);
    try { const r = await v26API.eventAiPreview(date); setAiPreview(r.data); }
    catch { toast({ title: 'AI preview unavailable', variant: 'destructive' }); }
    finally { setAiLoading(false); }
  };

  const book = async (eid) => {
    const name = prompt('Guest name?'); if (!name) return;
    const party = parseInt(prompt('Party size?') || '1');
    try { await v26API.bookEvent(eid, { guestName: name, partySize: party }); toast({ title: 'Booked' }); load(); }
    catch (e) { toast({ title: 'Could not book', description: e?.response?.data?.detail, variant: 'destructive' }); }
  };

  return (
    <div className="space-y-6" data-testid="events-page">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
          <Calendar className="text-purple-600" /> Events & Experiences
        </h1>
        <Button onClick={() => setEditing(blank())} style={{ background: theme.primary }} data-testid="new-event-btn">
          <Plus size={14} className="mr-1.5" /> New Event
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="events-grid">
        {rows.length === 0 ? <Card className="col-span-full"><CardContent className="p-8 text-center text-gray-400">No events yet</CardContent></Card> :
          rows.map(e => {
            const booked = (e.bookings || []).reduce((s, b) => s + (b.partySize || 0), 0);
            const remaining = e.capacity - booked;
            return (
              <Card key={e.id} className="hover:shadow-lg transition" data-testid={`event-${e.id}`}>
                <CardContent className="p-5 space-y-2">
                  <div className="flex justify-between items-start">
                    <h3 className="font-bold">{e.title}</h3>
                    <Badge variant="outline">{e.category}</Badge>
                  </div>
                  <p className="text-xs text-gray-500 flex items-center gap-1"><CalendarDays size={12} /> {e.date} · {e.startTime}–{e.endTime}</p>
                  <p className="text-sm text-gray-700 line-clamp-2">{e.description}</p>
                  <div className="flex items-center justify-between text-xs pt-2 border-t">
                    <span>${e.pricePerGuest}/guest</span>
                    <Badge className={remaining > 5 ? 'bg-emerald-100 text-emerald-700' : remaining > 0 ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700'}>
                      {remaining > 0 ? `${remaining} left` : 'Sold out'}
                    </Badge>
                  </div>
                  <div className="flex gap-1 pt-1">
                    <Button size="sm" variant="outline" onClick={() => book(e.id)} disabled={remaining <= 0} data-testid={`book-${e.id}`}>Book</Button>
                    <Button size="sm" variant="outline" onClick={() => previewMarketing(e.date)} data-testid={`preview-${e.id}`}><Sparkles size={12} className="mr-1" /> AI</Button>
                    <Button size="sm" variant="ghost" onClick={() => setEditing(e)}><Edit2 size={12} /></Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
      </div>

      {/* AI marketing preview drawer */}
      {aiPreview && (
        <Card className="border-purple-300 bg-purple-50"><CardContent className="p-5" data-testid="ai-preview">
          <div className="flex justify-between items-start mb-3">
            <h3 className="font-bold flex items-center gap-1.5"><Sparkles size={16} className="text-purple-600" /> AI Marketing Preview · {aiPreview.date}</h3>
            <button onClick={() => setAiPreview(null)} className="text-gray-400 hover:text-red-600">×</button>
          </div>
          {aiLoading ? <p className="text-sm text-gray-500">Generating…</p> : (
            <div className="space-y-2 text-sm">
              <p><strong>Subject:</strong> {aiPreview.preview?.subject}</p>
              <p className="whitespace-pre-wrap text-gray-700">{aiPreview.preview?.emailBody}</p>
              <p className="italic text-purple-700">SMS: {aiPreview.preview?.sms}</p>
              {aiPreview.preview?.highlights && (
                <ul className="text-xs">{(aiPreview.preview.highlights || []).map((h, i) => <li key={i}>· {h}</li>)}</ul>
              )}
            </div>
          )}
        </CardContent></Card>
      )}

      {/* Editor */}
      {editing && (
        <Card className="border-amber-300"><CardContent className="p-5 space-y-3" data-testid="event-editor">
          <h2 className="font-bold">{editing.id ? 'Edit' : 'New'} Event</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="md:col-span-2"><label className="text-xs uppercase text-gray-500">Title</label>
              <Input value={editing.title} onChange={e => setEditing({ ...editing, title: e.target.value })} /></div>
            <div><label className="text-xs uppercase text-gray-500">Category</label>
              <select className="w-full p-2 border rounded text-sm" value={editing.category} onChange={e => setEditing({ ...editing, category: e.target.value })}>
                <option>experience</option><option>tasting</option><option>live_music</option><option>workshop</option><option>private</option>
              </select></div>
            <div><label className="text-xs uppercase text-gray-500">Date</label>
              <Input type="date" value={editing.date} onChange={e => setEditing({ ...editing, date: e.target.value })} /></div>
            <div><label className="text-xs uppercase text-gray-500">Start</label>
              <Input type="time" value={editing.startTime} onChange={e => setEditing({ ...editing, startTime: e.target.value })} /></div>
            <div><label className="text-xs uppercase text-gray-500">End</label>
              <Input type="time" value={editing.endTime} onChange={e => setEditing({ ...editing, endTime: e.target.value })} /></div>
            <div><label className="text-xs uppercase text-gray-500">Capacity</label>
              <Input type="number" value={editing.capacity} onChange={e => setEditing({ ...editing, capacity: parseInt(e.target.value) || 0 })} /></div>
            <div><label className="text-xs uppercase text-gray-500">Price / Guest</label>
              <Input type="number" value={editing.pricePerGuest} onChange={e => setEditing({ ...editing, pricePerGuest: parseFloat(e.target.value) || 0 })} /></div>
          </div>
          <div><label className="text-xs uppercase text-gray-500">Description</label>
            <Textarea rows={3} value={editing.description} onChange={e => setEditing({ ...editing, description: e.target.value })} /></div>
          <div><label className="text-xs uppercase text-gray-500">Terms & Conditions</label>
            <Textarea rows={2} value={editing.termsAndConditions} onChange={e => setEditing({ ...editing, termsAndConditions: e.target.value })} /></div>
          <div className="flex gap-2">
            <Button onClick={save} style={{ background: theme.primary }} data-testid="save-event"><Save size={14} className="mr-1.5" /> Save</Button>
            <Button variant="outline" onClick={() => setEditing(null)}>Cancel</Button>
          </div>
        </CardContent></Card>
      )}
    </div>
  );
}


// =============================================================================
// STAFF AVAILABILITY
// =============================================================================
const DOW = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export function StaffAvailability() {
  const { theme } = useTheme(); const { toast } = useToast();
  const [staff, setStaff] = useState([]);
  const [selected, setSelected] = useState(null);
  const [data, setData] = useState({ weeklyAvailable: [], blackoutDates: [] });

  useEffect(() => {
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/auth/users`, { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } })
      .then(r => r.json()).then(setStaff).catch(() => {});
  }, []);

  const load = async (s) => {
    setSelected(s);
    const r = await v26API.getAvailability(s.id);
    setData({ weeklyAvailable: r.data.weeklyAvailable || [], blackoutDates: r.data.blackoutDates || [] });
  };

  const toggleDay = (d) => {
    setData(prev => ({ ...prev, weeklyAvailable: prev.weeklyAvailable.includes(d)
      ? prev.weeklyAvailable.filter(x => x !== d) : [...prev.weeklyAvailable, d] }));
  };

  const addBlackout = () => {
    const from = prompt('Blackout FROM (YYYY-MM-DD)?'); if (!from) return;
    const to = prompt('Blackout TO (YYYY-MM-DD)?') || from;
    const reason = prompt('Reason?') || 'unavailable';
    setData(prev => ({ ...prev, blackoutDates: [...prev.blackoutDates, { from, to, reason }] }));
  };

  const save = async () => {
    try { await v26API.setAvailability(selected.id, data); toast({ title: 'Saved' }); }
    catch (e) { toast({ title: 'Failed', variant: 'destructive' }); }
  };

  return (
    <div className="space-y-6" data-testid="staff-availability-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
        <Users2 className="text-indigo-600" /> Staff Availability
      </h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card><CardContent className="p-0">
          <div className="px-4 py-3 border-b font-bold text-sm">Staff</div>
          <div className="max-h-[60vh] overflow-y-auto">
            {staff.filter(s => ['cashier','barista','kitchen','manager'].includes(s.role)).map(s => (
              <button key={s.id} onClick={() => load(s)} className={`w-full text-left px-4 py-2 text-sm border-b hover:bg-gray-50 ${selected?.id === s.id ? 'bg-amber-50' : ''}`} data-testid={`staff-${s.id}`}>
                <p className="font-medium">{s.name}</p>
                <p className="text-xs text-gray-500">{s.role}</p>
              </button>
            ))}
          </div>
        </CardContent></Card>
        <Card className="md:col-span-2"><CardContent className="p-5">
          {!selected ? <p className="text-center py-12 text-gray-400">Pick a staff member</p> : (
            <div className="space-y-4">
              <h2 className="font-bold">{selected.name}</h2>
              <div>
                <p className="text-xs uppercase text-gray-500 mb-2">Weekly Available</p>
                <div className="flex gap-2 flex-wrap">
                  {DOW.map(d => (
                    <button key={d} onClick={() => toggleDay(d)}
                      className={`px-3 py-1.5 rounded-lg border transition ${data.weeklyAvailable.includes(d) ? 'text-white border-transparent' : 'bg-white border-gray-300 hover:border-gray-400'}`}
                      style={data.weeklyAvailable.includes(d) ? { background: theme.primary } : {}}
                      data-testid={`day-${d}`}>{d}</button>
                  ))}
                </div>
              </div>
              <div>
                <div className="flex justify-between items-center mb-2">
                  <p className="text-xs uppercase text-gray-500">Blackout Dates / Holidays</p>
                  <Button size="sm" variant="outline" onClick={addBlackout} data-testid="add-blackout"><Plus size={12} className="mr-1" /> Add</Button>
                </div>
                <div className="space-y-1">
                  {data.blackoutDates.length === 0 ? <p className="text-xs text-gray-400">None</p> :
                    data.blackoutDates.map((b, i) => (
                      <div key={i} className="flex justify-between items-center p-2 border rounded text-sm">
                        <span>{b.from} → {b.to} <span className="text-gray-500">({b.reason})</span></span>
                        <button onClick={() => setData(prev => ({ ...prev, blackoutDates: prev.blackoutDates.filter((_, x) => x !== i) }))} className="text-red-500">×</button>
                      </div>
                    ))}
                </div>
              </div>
              <Button onClick={save} style={{ background: theme.primary }} data-testid="save-availability"><Save size={14} className="mr-1.5" /> Save</Button>
            </div>
          )}
        </CardContent></Card>
      </div>
    </div>
  );
}


// =============================================================================
// RICH GIFT-CARD SALE
// =============================================================================
export function GiftCardSale() {
  const { theme } = useTheme(); const { toast } = useToast();
  const [form, setForm] = useState({
    amount: 50, bonus: 0, recipientName: '', recipientEmail: '',
    purchaserName: '', purchaserEmail: '', customerId: '',
    channel: 'counter', paymentMethod: 'card', occasion: 'general', message: '',
  });
  const [issued, setIssued] = useState(null);
  const [customers, setCustomers] = useState([]);
  useEffect(() => { customersAPI.getAll().then(r => setCustomers(r.data || [])).catch(() => {}); }, []);

  const sell = async () => {
    try {
      const r = await v26API.sellGift(form);
      setIssued(r.data);
      toast({ title: 'Gift card sold', description: `${r.data.code} — $${r.data.amount}` });
    } catch (e) {
      toast({ title: 'Failed', description: e?.response?.data?.detail, variant: 'destructive' });
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto" data-testid="giftcard-sale-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
        <Gift className="text-rose-600" /> Sell Gift Card
      </h1>
      <Card><CardContent className="p-5 space-y-3" data-testid="gc-sale-form">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div><label className="text-xs uppercase text-gray-500">Amount $</label>
            <Input type="number" value={form.amount} onChange={e => setForm({ ...form, amount: parseFloat(e.target.value) || 0 })} data-testid="gc-amount" /></div>
          <div><label className="text-xs uppercase text-gray-500">Bonus $</label>
            <Input type="number" value={form.bonus} onChange={e => setForm({ ...form, bonus: parseFloat(e.target.value) || 0 })} data-testid="gc-bonus" /></div>
          <div><label className="text-xs uppercase text-gray-500">Channel</label>
            <select className="w-full p-2 border rounded text-sm" value={form.channel} onChange={e => setForm({ ...form, channel: e.target.value })}>
              <option value="counter">Counter</option><option value="online">Online</option>
            </select></div>
          <div><label className="text-xs uppercase text-gray-500">Payment</label>
            <select className="w-full p-2 border rounded text-sm" value={form.paymentMethod} onChange={e => setForm({ ...form, paymentMethod: e.target.value })}>
              <option>card</option><option>cash</option><option>stripe</option><option>bank</option>
            </select></div>
          <div><label className="text-xs uppercase text-gray-500">Recipient Name</label>
            <Input value={form.recipientName} onChange={e => setForm({ ...form, recipientName: e.target.value })} data-testid="gc-recipient-name" /></div>
          <div><label className="text-xs uppercase text-gray-500">Recipient Email</label>
            <Input type="email" value={form.recipientEmail} onChange={e => setForm({ ...form, recipientEmail: e.target.value })} data-testid="gc-recipient-email" /></div>
          <div><label className="text-xs uppercase text-gray-500">Purchaser Name</label>
            <Input value={form.purchaserName} onChange={e => setForm({ ...form, purchaserName: e.target.value })} /></div>
          <div><label className="text-xs uppercase text-gray-500">Purchaser Email</label>
            <Input type="email" value={form.purchaserEmail} onChange={e => setForm({ ...form, purchaserEmail: e.target.value })} /></div>
          <div className="col-span-2"><label className="text-xs uppercase text-gray-500">Assign to existing customer (optional)</label>
            <select className="w-full p-2 border rounded text-sm" value={form.customerId} onChange={e => setForm({ ...form, customerId: e.target.value })} data-testid="gc-customer">
              <option value="">— None —</option>
              {customers.map(c => <option key={c.id} value={c.id}>{c.name} · {c.email || c.phone}</option>)}
            </select></div>
          <div><label className="text-xs uppercase text-gray-500">Occasion</label>
            <Input value={form.occasion} onChange={e => setForm({ ...form, occasion: e.target.value })} /></div>
        </div>
        <div><label className="text-xs uppercase text-gray-500">Message</label>
          <Textarea rows={2} value={form.message} onChange={e => setForm({ ...form, message: e.target.value })} /></div>
        <Button onClick={sell} style={{ background: theme.primary }} disabled={form.amount <= 0} data-testid="gc-sell-btn"><Gift size={14} className="mr-1.5" /> Issue Card</Button>
      </CardContent></Card>

      {issued && (
        <Card className="border-emerald-300"><CardContent className="p-6 text-center space-y-3" data-testid="gc-issued">
          <CheckCircle className="mx-auto text-emerald-600" />
          <h3 className="font-bold text-lg">Card Issued</h3>
          <p className="text-3xl font-bold">${issued.amount}{issued.bonus > 0 && <span className="text-base text-emerald-600"> +${issued.bonus} bonus</span>}</p>
          <Barcode128 value={issued.code} />
          <p className="text-xs text-gray-500">Recipient: {issued.recipientName} · {issued.recipientEmail}</p>
          <Button variant="outline" onClick={() => window.print()}>Print</Button>
        </CardContent></Card>
      )}
    </div>
  );
}


// =============================================================================
// AI MARKETING EMAILS — autonomous drafts the owner can edit + send
// =============================================================================
export function MarketingEmails() {
  const { theme } = useTheme(); const { toast } = useToast();
  const [rows, setRows] = useState([]);
  const [generating, setGenerating] = useState(false);
  const [form, setForm] = useState({ audience: 'all', tone: 'friendly', horizonDays: 14 });
  const [opened, setOpened] = useState(null);

  const load = () => v26API.listMarketingEmails().then(r => setRows(r.data || []));
  useEffect(() => { load(); }, []);

  const generate = async () => {
    setGenerating(true);
    try {
      const r = await v26API.generateMarketingEmail(form);
      setOpened(r.data);
      toast({ title: 'Draft generated', description: r.data?.subject || 'Ready to review' });
      load();
    } catch (e) {
      toast({ title: 'Generation failed', description: e?.response?.data?.detail, variant: 'destructive' });
    } finally { setGenerating(false); }
  };

  const save = async () => {
    try {
      await v26API.updateMarketingEmail(opened.id, opened);
      toast({ title: 'Saved' }); load();
    } catch { toast({ title: 'Save failed', variant: 'destructive' }); }
  };

  const remove = async (id) => {
    if (!window.confirm('Delete this draft?')) return;
    await v26API.deleteMarketingEmail(id);
    if (opened?.id === id) setOpened(null);
    load();
  };

  return (
    <div className="space-y-6" data-testid="marketing-emails-page">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
          <Sparkles className="text-purple-600" /> AI Marketing Emails
        </h1>
      </div>

      <Card><CardContent className="p-5 space-y-3" data-testid="generate-email-form">
        <p className="text-sm text-gray-600">Generate an email featuring upcoming events, active vouchers and tier perks.</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div><label className="text-xs uppercase text-gray-500">Audience</label>
            <select className="w-full p-2 border rounded text-sm" value={form.audience} onChange={e => setForm({ ...form, audience: e.target.value })} data-testid="mkt-audience">
              <option value="all">All customers</option>
              <option value="tier:Gold">Tier · Gold</option>
              <option value="tier:Silver">Tier · Silver</option>
              <option value="tier:Bronze">Tier · Bronze</option>
              <option value="segment:lapsed">Lapsed (30d+)</option>
              <option value="segment:new">New (≤14d)</option>
            </select></div>
          <div><label className="text-xs uppercase text-gray-500">Tone</label>
            <select className="w-full p-2 border rounded text-sm" value={form.tone} onChange={e => setForm({ ...form, tone: e.target.value })} data-testid="mkt-tone">
              <option value="friendly">Friendly</option><option value="elegant">Elegant</option>
              <option value="urgent">Urgent</option><option value="playful">Playful</option>
            </select></div>
          <div><label className="text-xs uppercase text-gray-500">Horizon (days)</label>
            <Input type="number" value={form.horizonDays} onChange={e => setForm({ ...form, horizonDays: parseInt(e.target.value) || 14 })} data-testid="mkt-horizon" /></div>
        </div>
        <Button onClick={generate} disabled={generating} style={{ background: theme.primary }} data-testid="generate-email-btn">
          {generating ? 'Generating…' : <><Sparkles size={14} className="mr-1.5" /> Generate Draft</>}
        </Button>
      </CardContent></Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-1"><CardContent className="p-0">
          <div className="px-4 py-3 border-b font-bold text-sm">Drafts ({rows.length})</div>
          <div className="max-h-[60vh] overflow-y-auto">
            {rows.length === 0 ? <p className="text-center text-gray-400 py-8 text-sm">No drafts yet</p> :
              rows.map(m => (
                <button key={m.id} onClick={() => setOpened(m)} className={`w-full text-left px-4 py-3 border-b hover:bg-gray-50 ${opened?.id === m.id ? 'bg-purple-50' : ''}`} data-testid={`email-row-${m.id}`}>
                  <p className="font-medium text-sm truncate">{m.subject || '(no subject)'}</p>
                  <p className="text-xs text-gray-500 truncate">{m.audience} · {m.tone}</p>
                  <p className="text-[10px] text-gray-400 mt-1">{new Date(m.createdAt).toLocaleString()}</p>
                </button>
              ))}
          </div>
        </CardContent></Card>

        <Card className="lg:col-span-2"><CardContent className="p-5">
          {!opened ? <p className="text-center text-gray-400 py-12">Pick a draft or generate a new one</p> : (
            <div className="space-y-3" data-testid="email-editor">
              <div><label className="text-xs uppercase text-gray-500">Subject</label>
                <Input value={opened.subject || ''} onChange={e => setOpened({ ...opened, subject: e.target.value })} data-testid="mkt-subject" /></div>
              <div><label className="text-xs uppercase text-gray-500">Preheader</label>
                <Input value={opened.preheader || ''} onChange={e => setOpened({ ...opened, preheader: e.target.value })} /></div>
              <div><label className="text-xs uppercase text-gray-500">Body</label>
                <Textarea rows={10} value={opened.emailBody || ''} onChange={e => setOpened({ ...opened, emailBody: e.target.value })} data-testid="mkt-body" /></div>
              <div><label className="text-xs uppercase text-gray-500">SMS Version</label>
                <Textarea rows={2} value={opened.sms || ''} onChange={e => setOpened({ ...opened, sms: e.target.value })} /></div>
              <div><label className="text-xs uppercase text-gray-500">CTA Label</label>
                <Input value={opened.cta || ''} onChange={e => setOpened({ ...opened, cta: e.target.value })} /></div>
              {opened.highlights && opened.highlights.length > 0 && (
                <div className="bg-purple-50 border border-purple-200 rounded p-3 text-xs">
                  <p className="font-bold uppercase tracking-widest text-purple-700 mb-1">Highlights</p>
                  <ul>{opened.highlights.map((h, i) => <li key={i}>· {h}</li>)}</ul>
                </div>
              )}
              <div className="flex gap-2">
                <Button onClick={save} style={{ background: theme.primary }} data-testid="save-email-btn"><Save size={14} className="mr-1.5" /> Save</Button>
                <Button variant="outline" onClick={() => remove(opened.id)} className="text-red-600" data-testid="delete-email-btn"><Trash2 size={14} className="mr-1.5" /> Delete</Button>
                <Button variant="ghost" onClick={() => setOpened(null)}>Close</Button>
              </div>
            </div>
          )}
        </CardContent></Card>
      </div>
    </div>
  );
}
