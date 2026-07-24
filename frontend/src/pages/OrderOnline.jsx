import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShoppingBag, MapPin, Store, Bike, Plus, Minus, Clock, ArrowRight, Trash2 } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { CategoryIcon } from './Categories';
import { onlineAPI } from '../services/api';
import { useToast } from '../hooks/use-toast';

const CHANNELS = [
  { key: 'pickup', label: 'Pickup', icon: Store, hint: 'Skip the queue' },
  { key: 'delivery', label: 'Delivery', icon: Bike, hint: 'To your door' },
  { key: 'dine-in', label: 'Dine-in', icon: ShoppingBag, hint: 'Order ahead' },
];

export default function OrderOnline() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCat, setSelectedCat] = useState('All');
  const [cart, setCart] = useState([]);
  const [channel, setChannel] = useState('pickup');
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [address, setAddress] = useState('');
  const [notes, setNotes] = useState('');
  const [placing, setPlacing] = useState(false);

  useEffect(() => {
    Promise.all([onlineAPI.publicProducts(), onlineAPI.publicCategories()])
      .then(([p, c]) => { setProducts(p.data || []); setCategories(c.data || []); })
      .catch(() => {});
  }, []);

  // Filter categories by selected channel
  const cats = useMemo(() => categories.filter(c => true), [categories]);

  const filteredProducts = selectedCat === 'All'
    ? products
    : products.filter(p => p.category === selectedCat);

  // Menu prices already include GST — it's disclosed below, not added on top.
  const subtotal = cart.reduce((s, i) => s + i.price * i.quantity, 0);
  const total = subtotal;
  const gst = total / 11;

  const maxPrepMin = useMemo(() => {
    if (cart.length === 0) return 0;
    return Math.max(...cart.map(i => {
      const c = cats.find(cc => cc.name === i.category);
      return c?.prepTime || 8;
    }));
  }, [cart, cats]);

  const addItem = (p) => setCart(prev => {
    const ex = prev.find(x => x.id === p.id);
    if (ex) return prev.map(x => x.id === p.id ? { ...x, quantity: x.quantity + 1 } : x);
    return [...prev, { id: p.id, name: p.name, price: p.price, quantity: 1, category: p.category, image: p.image }];
  });
  const updQty = (id, d) => setCart(prev =>
    prev.map(x => x.id === id ? { ...x, quantity: Math.max(0, x.quantity + d) } : x).filter(x => x.quantity > 0)
  );
  const removeItem = (id) => setCart(prev => prev.filter(x => x.id !== id));

  const place = async () => {
    if (!name) { toast({ title: 'Name required', variant: 'destructive' }); return; }
    if (cart.length === 0) { toast({ title: 'Cart is empty', variant: 'destructive' }); return; }
    if (channel === 'delivery' && !address) { toast({ title: 'Delivery address required', variant: 'destructive' }); return; }
    setPlacing(true);
    try {
      const r = await onlineAPI.placeOrder({
        items: cart.map(i => ({ id: i.id, productId: i.id, name: i.name, price: i.price, quantity: i.quantity, category: i.category })),
        channel,
        customerName: name, customerPhone: phone, customerEmail: email,
        address: channel === 'delivery' ? address : '', notes,
      });
      toast({ title: 'Order placed!', description: `Tracking code: ${r.data.id}` });
      navigate(`/track/${r.data.id}`);
    } catch (e) {
      toast({ title: 'Failed', description: e?.response?.data?.detail, variant: 'destructive' });
    } finally { setPlacing(false); }
  };

  return (
    <div className="min-h-screen bg-gray-50" data-testid="order-online-page">
      <div className="max-w-6xl mx-auto p-4 sm:p-6 space-y-5">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">NUA · Order Online</h1>
            <p className="text-sm text-gray-500">Fresh food, real-time ETA</p>
          </div>
          <Button variant="ghost" onClick={() => navigate('/track')} className="text-sm">Track an order</Button>
        </header>

        {/* Channel picker */}
        <div className="grid grid-cols-3 gap-2" data-testid="channel-picker">
          {CHANNELS.map(c => {
            const Active = c.icon;
            const on = channel === c.key;
            return (
              <button key={c.key} onClick={() => setChannel(c.key)}
                className={`p-4 rounded-xl border-2 transition flex items-center gap-3 ${on ? 'border-gray-900 bg-white shadow-sm' : 'border-transparent bg-white hover:border-gray-300'}`}
                data-testid={`channel-${c.key}`}>
                <Active size={20} className={on ? 'text-gray-900' : 'text-gray-400'} />
                <div className="text-left">
                  <p className={`font-bold text-sm ${on ? '' : 'text-gray-600'}`}>{c.label}</p>
                  <p className="text-[10px] text-gray-400">{c.hint}</p>
                </div>
              </button>
            );
          })}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Catalog */}
          <div className="lg:col-span-2 space-y-3">
            <div className="flex gap-2 overflow-x-auto pb-1">
              <button onClick={() => setSelectedCat('All')}
                className={`px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap ${selectedCat === 'All' ? 'bg-gray-900 text-white' : 'bg-white border'}`}
                data-testid="online-cat-All">All</button>
              {cats.map(c => (
                <button key={c.id} onClick={() => setSelectedCat(c.name)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap ${selectedCat === c.name ? 'text-white' : 'bg-white border'}`}
                  style={selectedCat === c.name ? { background: c.color } : {}}
                  data-testid={`online-cat-${c.name}`}>
                  <CategoryIcon name={c.icon} size={12} /> {c.name}
                  <span className="text-[10px] opacity-70">⏱{c.prepTime}m</span>
                </button>
              ))}
            </div>
            <div className="grid gap-2 [grid-template-columns:repeat(auto-fill,minmax(170px,1fr))]">
              {filteredProducts.map(p => (
                <Card key={p.id} className="overflow-hidden cursor-pointer hover:shadow-md transition" onClick={() => addItem(p)} data-testid={`online-product-${p.id}`}>
                  <img src={p.image || 'https://placehold.co/300x180/e5e7eb/9ca3af?text=NUA'} alt={p.name} className="w-full h-28 object-cover" />
                  <CardContent className="p-2.5">
                    <p className="font-medium text-sm truncate">{p.name}</p>
                    <p className="text-[10px] text-gray-400 uppercase">{p.category}</p>
                    <div className="flex justify-between items-center mt-1">
                      <span className="font-bold text-sm">${p.price.toFixed(2)}</span>
                      <Button size="sm" className="h-7 px-2 text-xs"><Plus size={11} /></Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* Cart */}
          <Card className="lg:sticky lg:top-4 self-start">
            <CardContent className="p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="font-bold">Your Cart ({cart.length})</h2>
                {cart.length > 0 && <span className="flex items-center gap-1 text-xs text-purple-700"><Clock size={12} /> ~{maxPrepMin}m prep</span>}
              </div>

              {cart.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-8">Add items to start your order</p>
              ) : (
                <div className="space-y-2" data-testid="online-cart">
                  {cart.map(i => (
                    <div key={i.id} className="flex items-center gap-2">
                      <div className="flex-1">
                        <p className="text-sm font-medium">{i.name}</p>
                        <p className="text-xs text-gray-400">${i.price.toFixed(2)} ea</p>
                      </div>
                      <div className="flex items-center gap-1">
                        <Button size="sm" variant="outline" className="h-7 w-7 p-0" onClick={() => updQty(i.id, -1)} data-testid={`online-minus-${i.id}`}><Minus size={11} /></Button>
                        <span className="w-5 text-center text-sm">{i.quantity}</span>
                        <Button size="sm" variant="outline" className="h-7 w-7 p-0" onClick={() => updQty(i.id, 1)} data-testid={`online-plus-${i.id}`}><Plus size={11} /></Button>
                        <button onClick={() => removeItem(i.id)} className="text-gray-300 hover:text-red-600 ml-1"><Trash2 size={12} /></button>
                      </div>
                    </div>
                  ))}

                  <div className="pt-2 border-t text-sm space-y-1">
                    <div className="flex justify-between font-bold"><span>Total</span><span>${total.toFixed(2)}</span></div>
                    <div className="flex justify-between text-[11px] text-gray-400"><span>GST Included</span><span>${gst.toFixed(2)}</span></div>
                    <p className="text-[10px] text-gray-400 text-center">Prices include GST</p>
                  </div>

                  <div className="pt-2 border-t space-y-2">
                    <Input placeholder="Your name *" value={name} onChange={e => setName(e.target.value)} data-testid="online-name" />
                    <Input placeholder="Phone" value={phone} onChange={e => setPhone(e.target.value)} data-testid="online-phone" />
                    <Input placeholder="Email (optional)" value={email} onChange={e => setEmail(e.target.value)} />
                    {channel === 'delivery' && (
                      <Textarea rows={2} placeholder="Delivery address *" value={address} onChange={e => setAddress(e.target.value)} data-testid="online-address" />
                    )}
                    <Textarea rows={2} placeholder="Special instructions (e.g. no onion)" value={notes} onChange={e => setNotes(e.target.value)} />
                  </div>

                  <Button onClick={place} disabled={placing} className="w-full bg-gray-900 hover:bg-black text-white" data-testid="place-order-btn">
                    {placing ? 'Placing…' : (<><ArrowRight size={14} className="mr-1" /> Place order · ${total.toFixed(2)}</>)}
                  </Button>
                  <p className="text-[10px] text-gray-400 text-center">Payment collected at {channel === 'delivery' ? 'delivery' : 'pickup'}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
