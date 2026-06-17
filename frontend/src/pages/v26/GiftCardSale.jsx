import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { useToast } from '../../hooks/use-toast';
import { useTheme } from '../../contexts/ThemeContext';
import { v26API, customersAPI } from '../../services/api';
import Barcode128 from '../../components/Barcode128';
import { Gift, CheckCircle } from 'lucide-react';

export default function GiftCardSale() {
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
