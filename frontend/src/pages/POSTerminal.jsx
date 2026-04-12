import React, { useState, useEffect, useCallback } from 'react';
import {
  Search, Plus, Minus, Trash2, User, CreditCard, Banknote, Smartphone,
  ShoppingCart, QrCode, SplitSquareHorizontal, X, Check, ChevronLeft, Copy
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle
} from '../components/ui/dialog';
import { useTheme } from '../contexts/ThemeContext';
import { usePOS } from '../contexts/POSContext';
import { productsAPI, promotionsAPI, customersAPI, transactionsAPI, paymentAPI, stripeAPI, advancedAPI } from '../services/api';
import { useToast } from '../hooks/use-toast';

const POSTerminal = () => {
  const { theme } = useTheme();
  const { cart, addToCart, removeFromCart, updateQuantity, clearCart, calculateTotal, selectedCustomer, setSelectedCustomer, currentUser, currentLocation } = usePOS();
  const { toast } = useToast();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [products, setProducts] = useState([]);
  const [promotions, setPromotions] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [trainingMode, setTrainingMode] = useState(false);

  // Payment flow state
  const [paymentView, setPaymentView] = useState('methods'); // methods | qr | upi | split | processing
  const [showPayment, setShowPayment] = useState(false);

  // QR / UPI state
  const [qrData, setQrData] = useState(null);

  // Split payment state
  const [splitMode, setSplitMode] = useState('equal'); // equal | custom
  const [splitCount, setSplitCount] = useState(2);
  const [splitParts, setSplitParts] = useState([]);
  const [activeSplitIndex, setActiveSplitIndex] = useState(null);

  const categories = ['All', 'Beverages', 'Food', 'Bakery'];

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [productsRes, promotionsRes, customersRes] = await Promise.all([
        productsAPI.getAll(), promotionsAPI.getActive(), customersAPI.getAll()
      ]);
      setProducts(productsRes.data);
      setPromotions(promotionsRes.data);
      setCustomers(customersRes.data);
      // Check training mode
      advancedAPI.getTrainingMode().then(r => setTrainingMode(r.data?.enabled || false)).catch(() => {});
    } catch (error) {
      console.error('Error fetching data:', error);
      toast({ title: "Error", description: "Failed to load data.", variant: "destructive" });
    }
  };

  const filteredProducts = products.filter(p =>
    (selectedCategory === 'All' || p.category === selectedCategory) &&
    p.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const totals = calculateTotal();
  const totalNum = parseFloat(totals.total) || 0;

  // ---- Standard checkout ----
  const handleCheckout = async (paymentMethod) => {
    if (loading) return;
    if (trainingMode) {
      toast({ title: "Training Mode", description: "Transaction simulated — no real charge was made.", variant: "default" });
      resetPayment();
      clearCart();
      return;
    }
    setLoading(true);
    try {
      await transactionsAPI.create({
        items: cart.map(item => ({ productId: item.id, productName: item.name, quantity: item.quantity, price: item.price })),
        paymentMethod, customerId: selectedCustomer?.id || null, location: currentLocation, cashier: currentUser.name,
      });
      toast({ title: "Transaction Complete!", description: `Payment of $${totals.total} via ${paymentMethod}` });
      resetPayment();
      clearCart();
      const r = await productsAPI.getAll(); setProducts(r.data);
    } catch (error) {
      toast({ title: "Error", description: "Transaction failed.", variant: "destructive" });
    } finally { setLoading(false); }
  };

  // ---- QR / UPI flow ----
  const handleGenerateQR = async (method) => {
    setLoading(true);
    try {
      const res = await paymentAPI.generateQR({ amount: totalNum, method });
      setQrData(res.data);
      setPaymentView(method === 'upi' ? 'upi' : 'qr');
    } catch {
      toast({ title: "Error", description: "Failed to generate QR code.", variant: "destructive" });
    } finally { setLoading(false); }
  };

  // ---- Stripe Checkout ----
  const handleStripeCheckout = async () => {
    setLoading(true);
    try {
      const res = await stripeAPI.createCheckout({
        originUrl: window.location.origin,
        amount: totalNum,
      });
      if (res.data.url) window.location.href = res.data.url;
    } catch {
      toast({ title: "Error", description: "Failed to initiate Stripe checkout.", variant: "destructive" });
    } finally { setLoading(false); }
  };

  const handleConfirmQRPayment = async () => {
    if (!qrData?.paymentId) return;
    setLoading(true);
    try {
      await paymentAPI.confirm(qrData.paymentId);
      await transactionsAPI.create({
        items: cart.map(item => ({ productId: item.id, productName: item.name, quantity: item.quantity, price: item.price })),
        paymentMethod: paymentView === 'upi' ? 'UPI' : 'QR Code',
        customerId: selectedCustomer?.id || null, location: currentLocation, cashier: currentUser.name,
      });
      toast({ title: "Payment Confirmed!", description: `$${totalNum.toFixed(2)} received via ${paymentView === 'upi' ? 'UPI' : 'QR Code'}` });
      resetPayment(); clearCart();
      const r = await productsAPI.getAll(); setProducts(r.data);
    } catch {
      toast({ title: "Error", description: "Confirmation failed.", variant: "destructive" });
    } finally { setLoading(false); }
  };

  // ---- Split payment flow ----
  const initSplitParts = useCallback((count, mode) => {
    const perPerson = Math.floor((totalNum / count) * 100) / 100;
    const remainder = Math.round((totalNum - perPerson * count) * 100) / 100;
    const parts = Array.from({ length: count }, (_, i) => ({
      payerName: `Guest ${i + 1}`,
      amount: i === 0 ? perPerson + remainder : perPerson,
      method: 'Card',
      status: 'pending',
    }));
    setSplitParts(parts);
  }, [totalNum]);

  const handleStartSplit = () => {
    setPaymentView('split');
    initSplitParts(splitCount, splitMode);
  };

  const updateSplitPart = (idx, field, value) => {
    setSplitParts(prev => {
      const next = [...prev];
      next[idx] = { ...next[idx], [field]: value };
      return next;
    });
  };

  const recalcEqualSplit = (count) => {
    setSplitCount(count);
    if (splitMode === 'equal') initSplitParts(count, 'equal');
  };

  const splitPaid = splitParts.filter(s => s.status === 'confirmed').reduce((sum, s) => sum + s.amount, 0);
  const splitRemaining = Math.max(0, Math.round((totalNum - splitPaid) * 100) / 100);

  const handlePaySplit = async (idx) => {
    setActiveSplitIndex(idx);
    setLoading(true);
    try {
      const part = splitParts[idx];
      if (part.method === 'UPI' || part.method === 'QR Code') {
        const res = await paymentAPI.generateQR({ amount: part.amount, method: part.method === 'UPI' ? 'upi' : 'qr_code' });
        await paymentAPI.confirm(res.data.paymentId);
      }
      updateSplitPart(idx, 'status', 'confirmed');
      toast({ title: `Split #${idx + 1} Paid`, description: `$${part.amount.toFixed(2)} from ${part.payerName}` });

      // Check if all paid
      const updatedParts = splitParts.map((s, i) => i === idx ? { ...s, status: 'confirmed' } : s);
      const allPaid = updatedParts.every(s => s.status === 'confirmed');
      if (allPaid) {
        await transactionsAPI.create({
          items: cart.map(item => ({ productId: item.id, productName: item.name, quantity: item.quantity, price: item.price })),
          paymentMethod: 'Split Payment',
          customerId: selectedCustomer?.id || null, location: currentLocation, cashier: currentUser.name,
          splitDetails: updatedParts.map(s => ({ payerName: s.payerName, amount: s.amount, method: s.method })),
        });
        toast({ title: "All Splits Paid!", description: `Total $${totalNum.toFixed(2)} collected` });
        setTimeout(() => { resetPayment(); clearCart(); }, 1200);
        productsAPI.getAll().then(r => setProducts(r.data));
      }
    } catch {
      toast({ title: "Error", description: "Split payment failed.", variant: "destructive" });
    } finally { setLoading(false); setActiveSplitIndex(null); }
  };

  const resetPayment = () => {
    setShowPayment(false); setPaymentView('methods'); setQrData(null);
    setSplitParts([]); setSplitCount(2); setSplitMode('equal');
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast({ title: "Copied!", description: "UPI ID copied to clipboard" });
  };

  return (
    <div className="flex h-screen gap-6" data-testid="pos-terminal">
      {/* Training Mode Banner */}
      {trainingMode && (
        <div className="fixed top-0 left-64 right-0 z-40 bg-amber-500 text-white text-center py-2 text-sm font-semibold"
          data-testid="training-mode-banner">
          TRAINING MODE — Transactions are simulated, no real charges
        </div>
      )}
      {/* Products Grid */}
      <div className="flex-1 flex flex-col">
        <div className="mb-6">
          <h1 className="text-3xl font-bold mb-4" style={{ color: theme.text }}>POS Terminal</h1>
          <div className="flex gap-3 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
              <Input placeholder="Search products..." className="pl-10" value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)} data-testid="pos-search" />
            </div>
          </div>
          <div className="flex gap-2">
            {categories.map(cat => (
              <Button key={cat} variant={selectedCategory === cat ? 'default' : 'outline'}
                onClick={() => setSelectedCategory(cat)}
                style={{ backgroundColor: selectedCategory === cat ? theme.primary : 'transparent', color: selectedCategory === cat ? 'white' : theme.text }}
                data-testid={`pos-cat-${cat}`}>
                {cat}
              </Button>
            ))}
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {filteredProducts.map(product => (
              <Card key={product.id} className="cursor-pointer hover:shadow-lg transition-all duration-300 hover:scale-105"
                onClick={() => addToCart(product)} data-testid={`product-${product.id}`}>
                <CardContent className="p-4">
                  <img src={product.image} alt={product.name} className="w-full h-32 object-cover rounded-lg mb-3" />
                  <h3 className="font-semibold mb-1" style={{ color: theme.text }}>{product.name}</h3>
                  <p className="text-sm text-gray-500 mb-2">{product.category}</p>
                  <p className="text-lg font-bold" style={{ color: theme.primary }}>${product.price.toFixed(2)}</p>
                  <p className="text-xs text-gray-400">Stock: {product.stock}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
        {/* Active Promotions */}
        <div className="mt-4 p-4 bg-gradient-to-r from-yellow-50 to-orange-50 rounded-lg border border-yellow-200">
          <h3 className="font-semibold mb-2" style={{ color: theme.text }}>Active Promotions</h3>
          <div className="flex gap-3 overflow-x-auto">
            {promotions.filter(p => p.active).map(promo => (
              <div key={promo.id} className="bg-white p-3 rounded-lg border min-w-[250px]">
                <p className="font-medium text-sm">{promo.name}</p>
                <p className="text-xs text-gray-500">{promo.schedule}</p>
                <p className="text-sm font-bold mt-1" style={{ color: theme.accent }}>{promo.discount}% OFF</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Cart Panel */}
      <div className="w-96 flex flex-col border-l bg-gray-50 p-6" data-testid="pos-cart-panel">
        <h2 className="text-2xl font-bold mb-4" style={{ color: theme.text }}>Current Order</h2>
        {/* Customer Selection */}
        <Card className="mb-4"><CardContent className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <User size={18} style={{ color: theme.primary }} />
            <span className="font-medium text-sm">Customer</span>
          </div>
          {selectedCustomer ? (
            <div className="flex items-center justify-between">
              <div><p className="font-medium">{selectedCustomer.name}</p><p className="text-xs text-gray-500">{selectedCustomer.membershipTier} Member</p></div>
              <Button variant="ghost" size="sm" onClick={() => setSelectedCustomer(null)}>Remove</Button>
            </div>
          ) : (
            <select className="w-full p-2 border rounded-md text-sm"
              onChange={(e) => { const c = customers.find(c => c.id === e.target.value); setSelectedCustomer(c); }}
              data-testid="pos-customer-select">
              <option value="">Walk-in Customer</option>
              {customers.map(c => <option key={c.id} value={c.id}>{c.name} ({c.membershipTier})</option>)}
            </select>
          )}
        </CardContent></Card>

        {/* Cart Items */}
        <div className="flex-1 overflow-y-auto mb-4">
          {cart.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <ShoppingCart size={48} className="mx-auto mb-3 opacity-50" /><p>Cart is empty</p><p className="text-sm">Add products to start</p>
            </div>
          ) : (
            <div className="space-y-3">
              {cart.map(item => (
                <Card key={item.id} data-testid={`cart-item-${item.id}`}><CardContent className="p-3">
                  <div className="flex items-center gap-3">
                    <img src={item.image} alt={item.name} className="w-12 h-12 object-cover rounded" />
                    <div className="flex-1"><p className="font-medium text-sm">{item.name}</p><p className="text-xs text-gray-500">${item.price.toFixed(2)} each</p></div>
                    <div className="flex items-center gap-2">
                      <Button size="sm" variant="outline" onClick={() => updateQuantity(item.id, item.quantity - 1)} className="w-8 h-8 p-0"><Minus size={14} /></Button>
                      <span className="font-medium w-8 text-center">{item.quantity}</span>
                      <Button size="sm" variant="outline" onClick={() => updateQuantity(item.id, item.quantity + 1)} className="w-8 h-8 p-0"><Plus size={14} /></Button>
                      <Button size="sm" variant="ghost" onClick={() => removeFromCart(item.id)} className="w-8 h-8 p-0 text-red-500"><Trash2 size={14} /></Button>
                    </div>
                  </div>
                  <div className="text-right mt-2"><span className="font-bold" style={{ color: theme.primary }}>${(item.price * item.quantity).toFixed(2)}</span></div>
                </CardContent></Card>
              ))}
            </div>
          )}
        </div>

        {/* Totals */}
        {cart.length > 0 && (
          <Card className="mb-4"><CardContent className="p-4 space-y-2">
            <div className="flex justify-between text-sm"><span>Subtotal</span><span>${totals.subtotal}</span></div>
            <div className="flex justify-between text-sm"><span>GST (10%)</span><span>${totals.gst}</span></div>
            <div className="border-t pt-2 flex justify-between font-bold text-lg"><span>Total</span><span style={{ color: theme.primary }} data-testid="pos-total">${totals.total}</span></div>
          </CardContent></Card>
        )}

        {/* Payment Button */}
        {!showPayment && cart.length > 0 && (
          <Button className="w-full h-14 text-lg font-semibold" style={{ backgroundColor: theme.primary }}
            onClick={() => setShowPayment(true)} data-testid="pos-proceed-payment">
            Proceed to Payment
          </Button>
        )}

        {/* Payment Methods Panel */}
        {showPayment && paymentView === 'methods' && (
          <div className="space-y-2" data-testid="payment-methods-panel">
            <div className="grid grid-cols-2 gap-2">
              <Button className="h-14 flex-col gap-1" variant="outline" onClick={() => handleCheckout('Card')} data-testid="pay-card">
                <CreditCard size={20} /><span className="text-xs">Card</span>
              </Button>
              <Button className="h-14 flex-col gap-1" variant="outline" onClick={() => handleCheckout('Cash')} data-testid="pay-cash">
                <Banknote size={20} /><span className="text-xs">Cash</span>
              </Button>
              <Button className="h-14 flex-col gap-1" variant="outline" onClick={() => handleGenerateQR('qr_code')} data-testid="pay-qr">
                <QrCode size={20} /><span className="text-xs">QR Code</span>
              </Button>
              <Button className="h-14 flex-col gap-1" variant="outline" onClick={() => handleGenerateQR('upi')} data-testid="pay-upi">
                <Smartphone size={20} /><span className="text-xs">UPI</span>
              </Button>
            </div>
            <Button className="w-full h-12 bg-violet-600 hover:bg-violet-700 text-white font-medium"
              onClick={handleStripeCheckout} disabled={loading} data-testid="pay-stripe">
              <CreditCard size={18} className="mr-2" /> Pay with Stripe
            </Button>
            <Button className="w-full h-14 bg-indigo-600 hover:bg-indigo-700 text-white font-medium"
              onClick={handleStartSplit} data-testid="pay-split">
              <SplitSquareHorizontal size={20} className="mr-2" /> Split Payment
            </Button>
            <Button className="w-full" variant="ghost" onClick={resetPayment} data-testid="pay-cancel">Cancel</Button>
          </div>
        )}
      </div>

      {/* ========== QR Code Payment Dialog ========== */}
      <Dialog open={paymentView === 'qr'} onOpenChange={(open) => { if (!open) setPaymentView('methods'); }}>
        <DialogContent className="max-w-sm" data-testid="qr-payment-dialog">
          <DialogHeader><DialogTitle>Scan QR to Pay</DialogTitle></DialogHeader>
          <div className="flex flex-col items-center py-4 space-y-4">
            <div className="bg-white p-4 rounded-xl shadow-inner border">
              {qrData?.qrData && <QRCodeSVG value={qrData.qrData} size={200} level="M" includeMargin />}
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold">${totalNum.toFixed(2)}</p>
              <p className="text-sm text-gray-500 mt-1">Transaction: {qrData?.transactionId}</p>
            </div>
            <Badge variant="outline" className="text-amber-600 border-amber-300 bg-amber-50">Waiting for payment...</Badge>
            <Button className="w-full bg-green-600 hover:bg-green-700 text-white" onClick={handleConfirmQRPayment}
              disabled={loading} data-testid="qr-confirm-btn">
              <Check size={18} className="mr-2" /> Confirm Payment Received
            </Button>
            <Button variant="ghost" className="w-full" onClick={() => setPaymentView('methods')}>
              <ChevronLeft size={16} className="mr-1" /> Back
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* ========== UPI Payment Dialog ========== */}
      <Dialog open={paymentView === 'upi'} onOpenChange={(open) => { if (!open) setPaymentView('methods'); }}>
        <DialogContent className="max-w-sm" data-testid="upi-payment-dialog">
          <DialogHeader><DialogTitle>UPI Payment</DialogTitle></DialogHeader>
          <div className="flex flex-col items-center py-4 space-y-4">
            <div className="bg-white p-4 rounded-xl shadow-inner border">
              {qrData?.qrData && <QRCodeSVG value={qrData.qrData} size={180} level="M" includeMargin />}
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold">${totalNum.toFixed(2)}</p>
              {qrData?.merchantUpi && (
                <div className="flex items-center gap-2 justify-center mt-2 text-sm text-gray-600 bg-gray-50 px-3 py-1.5 rounded-full">
                  <span className="font-mono">{qrData.merchantUpi}</span>
                  <button onClick={() => copyToClipboard(qrData.merchantUpi)} className="text-gray-400 hover:text-gray-700"><Copy size={14} /></button>
                </div>
              )}
              <p className="text-xs text-gray-400 mt-2">Scan QR or pay to UPI ID above</p>
            </div>
            <Badge variant="outline" className="text-amber-600 border-amber-300 bg-amber-50">Awaiting UPI confirmation...</Badge>
            <Button className="w-full bg-green-600 hover:bg-green-700 text-white" onClick={handleConfirmQRPayment}
              disabled={loading} data-testid="upi-confirm-btn">
              <Check size={18} className="mr-2" /> Confirm Payment Received
            </Button>
            <Button variant="ghost" className="w-full" onClick={() => setPaymentView('methods')}>
              <ChevronLeft size={16} className="mr-1" /> Back
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* ========== Split Payment Dialog ========== */}
      <Dialog open={paymentView === 'split'} onOpenChange={(open) => { if (!open) setPaymentView('methods'); }}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto" data-testid="split-payment-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span>Split Payment — ${totalNum.toFixed(2)}</span>
              {splitRemaining > 0 && <Badge variant="outline" className="text-orange-600 border-orange-300">${splitRemaining.toFixed(2)} remaining</Badge>}
              {splitRemaining === 0 && splitParts.length > 0 && <Badge className="bg-green-600 text-white">All paid</Badge>}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            {/* Controls */}
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-600">Split into</span>
                <div className="flex items-center border rounded-lg overflow-hidden">
                  <button className="px-3 py-1.5 hover:bg-gray-100 text-sm" onClick={() => splitCount > 2 && recalcEqualSplit(splitCount - 1)}>-</button>
                  <span className="px-3 py-1.5 font-bold text-sm border-x" data-testid="split-count">{splitCount}</span>
                  <button className="px-3 py-1.5 hover:bg-gray-100 text-sm" onClick={() => splitCount < 10 && recalcEqualSplit(splitCount + 1)}>+</button>
                </div>
              </div>
              <div className="flex gap-1 ml-auto">
                {['equal', 'custom'].map(m => (
                  <button key={m} onClick={() => { setSplitMode(m); if (m === 'equal') initSplitParts(splitCount, 'equal'); }}
                    className={`px-3 py-1.5 text-xs rounded-full font-medium transition-colors ${splitMode === m ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
                    data-testid={`split-mode-${m}`}>
                    {m === 'equal' ? 'Equal' : 'Custom'}
                  </button>
                ))}
              </div>
            </div>

            {/* Split Parts */}
            <div className="space-y-3">
              {splitParts.map((part, idx) => (
                <Card key={idx} className={`border ${part.status === 'confirmed' ? 'border-green-300 bg-green-50/50' : ''}`}
                  data-testid={`split-part-${idx}`}>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${part.status === 'confirmed' ? 'bg-green-600 text-white' : 'bg-gray-200 text-gray-700'}`}>
                        {part.status === 'confirmed' ? <Check size={16} /> : idx + 1}
                      </div>
                      <div className="flex-1 space-y-2">
                        <div className="flex gap-2">
                          <Input placeholder="Guest name" value={part.payerName} className="h-8 text-sm"
                            onChange={e => updateSplitPart(idx, 'payerName', e.target.value)}
                            disabled={part.status === 'confirmed'} data-testid={`split-name-${idx}`} />
                          {splitMode === 'custom' && (
                            <Input type="number" step="0.01" min="0" value={part.amount} className="h-8 text-sm w-28"
                              onChange={e => updateSplitPart(idx, 'amount', parseFloat(e.target.value) || 0)}
                              disabled={part.status === 'confirmed'} data-testid={`split-amount-${idx}`} />
                          )}
                          {splitMode === 'equal' && (
                            <span className="font-bold text-sm whitespace-nowrap self-center">${part.amount.toFixed(2)}</span>
                          )}
                        </div>
                        <div className="flex items-center gap-1.5">
                          {['Card', 'Cash', 'UPI', 'QR Code'].map(method => (
                            <button key={method} onClick={() => part.status !== 'confirmed' && updateSplitPart(idx, 'method', method)}
                              className={`px-2 py-1 text-[11px] rounded-md font-medium transition-colors ${part.method === method ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'}`}
                              disabled={part.status === 'confirmed'} data-testid={`split-method-${idx}-${method.toLowerCase().replace(' ', '-')}`}>
                              {method}
                            </button>
                          ))}
                        </div>
                      </div>
                      {part.status !== 'confirmed' ? (
                        <Button size="sm" className="bg-green-600 hover:bg-green-700 text-white h-8 px-3"
                          onClick={() => handlePaySplit(idx)} disabled={loading && activeSplitIndex === idx}
                          data-testid={`split-pay-${idx}`}>
                          {loading && activeSplitIndex === idx ? '...' : 'Pay'}
                        </Button>
                      ) : (
                        <Badge className="bg-green-100 text-green-700 border-green-300">Paid</Badge>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            <Button variant="ghost" className="w-full" onClick={() => setPaymentView('methods')}>
              <ChevronLeft size={16} className="mr-1" /> Back to Methods
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default POSTerminal;
