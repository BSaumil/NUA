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
import { productsAPI, promotionsAPI, customersAPI, transactionsAPI, paymentAPI, stripeAPI, advancedAPI, menuFeaturesAPI, gamificationAPI } from '../services/api';
import { useToast } from '../hooks/use-toast';
import { useAuth } from '../contexts/AuthContext';

// ===== Swipeable Cart Item: left-swipe deletes, right-swipe repeats =====
function SwipeableCartItem({ item, onUpdateQty, onRemove, onRepeat, theme }) {
  const [dragX, setDragX] = useState(0);
  const startXRef = React.useRef(null);
  const isDraggingRef = React.useRef(false);
  const THRESHOLD = 80; // pixels to commit action

  const onPointerDown = (e) => {
    // ignore drags initiated on quantity buttons
    if (e.target.closest('[data-no-swipe]')) return;
    startXRef.current = e.clientX;
    isDraggingRef.current = true;
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e) => {
    if (!isDraggingRef.current || startXRef.current === null) return;
    const dx = e.clientX - startXRef.current;
    setDragX(dx);
  };
  const onPointerUp = (e) => {
    if (!isDraggingRef.current) return;
    isDraggingRef.current = false;
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch {}
    const dx = dragX;
    if (dx <= -THRESHOLD) {
      // Animate out then delete
      setDragX(-400);
      setTimeout(() => onRemove(item.id), 180);
    } else if (dx >= THRESHOLD) {
      // Trigger repeat then bounce back
      onRepeat(item);
      setDragX(0);
    } else {
      setDragX(0);
    }
    startXRef.current = null;
  };

  const bgIntensity = Math.min(Math.abs(dragX) / THRESHOLD, 1);

  return (
    <div className="relative overflow-hidden rounded-lg" data-testid={`cart-item-wrapper-${item.id}`}>
      {/* Background hint — left side (right-swipe = repeat) */}
      <div
        className="absolute inset-y-0 left-0 flex items-center pl-4 text-white font-bold text-xs"
        style={{ backgroundColor: '#10b981', opacity: dragX > 0 ? bgIntensity : 0, width: '100%' }}
        data-testid={`swipe-repeat-bg-${item.id}`}
      >
        <span>+1 REPEAT →</span>
      </div>
      {/* Background hint — right side (left-swipe = delete) */}
      <div
        className="absolute inset-y-0 right-0 flex items-center justify-end pr-4 text-white font-bold text-xs"
        style={{ backgroundColor: '#ef4444', opacity: dragX < 0 ? bgIntensity : 0, width: '100%' }}
        data-testid={`swipe-delete-bg-${item.id}`}
      >
        <span>← DELETE</span>
      </div>
      <Card
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        style={{ transform: `translateX(${dragX}px)`, transition: isDraggingRef.current ? 'none' : 'transform 0.2s ease-out', touchAction: 'pan-y' }}
        className="relative bg-white cursor-grab active:cursor-grabbing select-none"
        data-testid={`cart-item-${item.id}`}
      >
        <CardContent className="p-3">
          <div className="flex items-center gap-3">
            <img src={item.image || 'https://placehold.co/56x56/e5e7eb/9ca3af?text=NUA'} alt={item.name} className="w-14 h-14 object-cover rounded-md flex-shrink-0" draggable={false} />
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-sm truncate">{item.name}</p>
              <p className="text-xs text-gray-500">${item.price.toFixed(2)} each</p>
            </div>
            <div className="flex items-center gap-1.5" data-no-swipe>
              <Button size="sm" variant="outline" onClick={() => onUpdateQty(item.id, item.quantity - 1)} className="w-7 h-7 p-0" data-testid={`cart-minus-${item.id}`}><Minus size={12} /></Button>
              <span className="font-semibold w-6 text-center text-sm">{item.quantity}</span>
              <Button size="sm" variant="outline" onClick={() => onUpdateQty(item.id, item.quantity + 1)} className="w-7 h-7 p-0" data-testid={`cart-plus-${item.id}`}><Plus size={12} /></Button>
            </div>
          </div>
          <div className="flex items-center justify-between mt-1.5">
            <span className="text-[10px] text-gray-300 italic">← swipe delete · repeat swipe →</span>
            <span className="font-bold" style={{ color: theme.primary }}>${(item.price * item.quantity).toFixed(2)}</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

const POSTerminal = () => {
  const { theme } = useTheme();
  const { user } = useAuth();
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

  // Cash payment state
  const [cashTendered, setCashTendered] = useState(0);
  const [showCashChange, setShowCashChange] = useState(false);

  // Ghost discount (owner only - secret)
  const [showGhost, setShowGhost] = useState(false);
  const [ghostAmount, setGhostAmount] = useState('');
  const [lastTxnId, setLastTxnId] = useState(null);

  // v15: Tabs (Hold/Recall), Loyalty preview, BNPL, Multi-lang
  const [showTabsDialog, setShowTabsDialog] = useState(false);
  const [openTabs, setOpenTabs] = useState([]);
  const [labels, setLabels] = useState({});
  // v17: Points-and-Pay
  const [pointsBalance, setPointsBalance] = useState(null);
  const [pointsToRedeem, setPointsToRedeem] = useState(0);
  const [loyaltyCfg, setLoyaltyCfg] = useState({ minRedeem: 50, redeemRate: 0.01 });

  const [categories, setCategories] = useState(['All']);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      // Run all initial fetches in parallel for max speed
      const [productsRes, promotionsRes, customersRes, catsRes, loyaltyRes, labelsRes, trainingRes] = await Promise.allSettled([
        productsAPI.getAll(),
        promotionsAPI.getActive(),
        customersAPI.getAll(),
        fetch(`${process.env.REACT_APP_BACKEND_URL}/api/categories`).then(r => r.json()).catch(() => []),
        loyaltyEngineAPI.getConfig(),
        v15API.getLabels(localStorage.getItem('nua_lang') || 'en'),
        advancedAPI.getTrainingMode(),
      ]);
      if (productsRes.status === 'fulfilled') setProducts(productsRes.value.data || []);
      if (promotionsRes.status === 'fulfilled') setPromotions(promotionsRes.value.data || []);
      if (customersRes.status === 'fulfilled') setCustomers(customersRes.value.data || []);
      if (catsRes.status === 'fulfilled' && Array.isArray(catsRes.value)) {
        setCategories(['All', ...catsRes.value
          .filter(c => c.active !== false)
          .sort((a, b) => (a.sortOrder ?? 99) - (b.sortOrder ?? 99))
          .map(c => c.name)]);
      }
      if (loyaltyRes.status === 'fulfilled') setLoyaltyCfg(loyaltyRes.value.data || { minRedeem: 50, redeemRate: 0.01 });
      if (labelsRes.status === 'fulfilled') setLabels(labelsRes.value.data || {});
      if (trainingRes.status === 'fulfilled') setTrainingMode(trainingRes.value.data?.enabled || false);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast({ title: "Error", description: "Failed to load data.", variant: "destructive" });
    }
  };

  const filteredProducts = products.filter(p =>
    (selectedCategory === 'All' || p.category === selectedCategory) &&
    p.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Group products by category for "All" view (category-wise display)
  const groupedByCategory = React.useMemo(() => {
    const groups = {};
    filteredProducts.forEach(p => {
      const cat = p.category || 'Uncategorized';
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(p);
    });
    return groups;
  }, [filteredProducts]);

  const totalsRaw = calculateTotal();
  const redeemDiscount = pointsToRedeem >= (loyaltyCfg.minRedeem || 50) ? pointsToRedeem * (loyaltyCfg.redeemRate || 0.01) : 0;
  const totals = redeemDiscount > 0 ? { ...totalsRaw, total: Math.max(0, parseFloat(totalsRaw.total) - redeemDiscount).toFixed(2), pointsDiscount: redeemDiscount.toFixed(2) } : totalsRaw;
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
      const res = await transactionsAPI.create({
        items: cart.map(item => ({ productId: item.id, productName: item.name, quantity: item.quantity, price: item.price, category: item.category })),
        paymentMethod, customerId: selectedCustomer?.id || null, location: currentLocation, cashier: currentUser.name,
        pointsRedeemed: pointsToRedeem, pointsDiscount: redeemDiscount,
      });
      setLastTxnId(res.data?.id || null);
      // Loyalty: redeem first (if applicable), then earn on net spend
      if (selectedCustomer && pointsToRedeem >= (loyaltyCfg.minRedeem || 50)) {
        try { await loyaltyEngineAPI.redeem({ customerId: selectedCustomer.id, points: pointsToRedeem, transactionId: res.data?.id }); } catch {}
      }
      if (selectedCustomer) {
        try {
          await loyaltyEngineAPI.earn({
            customerId: selectedCustomer.id,
            transactionId: res.data?.id,
            items: cart.map(i => ({ category: i.category || 'Other', price: i.price, quantity: i.quantity })),
          });
        } catch {}
      }
      toast({ title: "Transaction Complete!", description: `Payment of $${totals.total} via ${paymentMethod}` });
      // Auto-route items to category printers
      try { await gamificationAPI.sendToPrinters({ items: cart.map(i => ({ productName: i.name, category: i.category, quantity: i.quantity })), orderId: res.data?.id }); } catch {}
      resetPayment();
      clearCart();
      setPointsToRedeem(0);
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
    setCashTendered(0); setShowCashChange(false);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast({ title: "Copied!", description: "UPI ID copied to clipboard" });
  };

  return (
    <div className="flex gap-4 h-[calc(100vh-7rem)]" data-testid="pos-terminal">
      {/* Training Mode Banner */}
      {trainingMode && (
        <div className="fixed top-0 left-0 right-0 z-40 bg-amber-500 text-white text-center py-2 text-sm font-semibold"
          data-testid="training-mode-banner">
          TRAINING MODE — Transactions are simulated, no real charges
        </div>
      )}
      {/* Products Grid — smaller cards, category-wise */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="mb-3">
          <h1 className="text-xl font-bold mb-2" style={{ color: theme.text }}
            onDoubleClick={() => { if (user?.role === 'owner') setShowGhost(true); }}
            data-testid="pos-title">POS Terminal</h1>
          <div className="relative mb-3 flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={16} />
              <Input placeholder="Search products..." className="pl-9 h-9" value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)} data-testid="pos-search" />
            </div>
            <VoiceOrderButton
              onAddSuggestions={(suggestions) => {
                suggestions.forEach(s => {
                  const p = products.find(pp => pp.id === s.productId);
                  if (p) { for (let i = 0; i < s.quantity; i++) addToCart(p); }
                });
              }}
              onExtendedAction={(act) => {
                if (act.action === 'void_last_item' && cart.length > 0) {
                  removeFromCart(cart[cart.length - 1].id);
                }
              }}
            />
            <Button variant="outline" className="h-9 px-3" onClick={async () => {
              if (cart.length === 0) { toast({ title: 'Cart empty', variant: 'destructive' }); return; }
              try {
                await v15API.createTab({ name: `Tab ${new Date().toLocaleTimeString()}`, cart, selectedCustomer });
                toast({ title: 'Order held', description: 'Recall from "Tabs" button' });
                clearCart();
              } catch { toast({ title: 'Hold failed', variant: 'destructive' }); }
            }} data-testid="hold-order-btn">Hold</Button>
            <Button variant="outline" className="h-9 px-3" onClick={async () => {
              try { const r = await v15API.getTabs(); setOpenTabs(r.data || []); setShowTabsDialog(true); } catch {}
            }} data-testid="recall-tab-btn">Tabs</Button>
          </div>
          <div className="flex gap-1.5 overflow-x-auto pb-1">
            {categories.map(cat => (
              <button key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all ${selectedCategory === cat ? 'text-white shadow-sm' : 'bg-white text-gray-600 border hover:border-gray-400'}`}
                style={selectedCategory === cat ? { backgroundColor: theme.primary } : {}}
                data-testid={`pos-cat-${cat}`}>
                {cat}
              </button>
            ))}
          </div>
        </div>
        <div className="flex-1 overflow-y-auto pr-1">
          {selectedCategory === 'All' ? (
            products.length === 0 ? (
              // Skeleton loader while products fetch
              <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-2" data-testid="pos-skeleton">
                {[...Array(12)].map((_, i) => (
                  <div key={i} className="bg-white rounded-lg border overflow-hidden animate-pulse">
                    <div className="w-full h-16 bg-gray-200" />
                    <div className="p-2 space-y-1">
                      <div className="h-3 bg-gray-200 rounded" />
                      <div className="h-3 bg-gray-100 rounded w-2/3" />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
            // Category-wise grouped view
            <div className="space-y-5">
              {Object.entries(groupedByCategory).map(([cat, prods]) => (
                <div key={cat} data-testid={`pos-category-section-${cat}`}>
                  <div className="flex items-center gap-2 mb-2 sticky top-0 bg-gray-50 py-1.5 z-[1]">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500">{cat}</h3>
                    <span className="text-[10px] text-gray-400">{prods.length} items</span>
                    <div className="flex-1 border-b border-dashed"></div>
                  </div>
                  <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-2">
                    {prods.map(product => (
                      <button key={product.id}
                        onClick={() => addToCart(product)}
                        className="bg-white rounded-lg border hover:shadow-md hover:-translate-y-0.5 transition-all overflow-hidden text-left active:scale-95"
                        data-testid={`product-${product.id}`}>
                        <img src={product.image || 'https://placehold.co/200x100/e5e7eb/9ca3af?text=NUA'} alt={product.name} className="w-full h-16 object-cover" />
                        <div className="p-2">
                          <h3 className="font-medium text-xs leading-tight line-clamp-1" style={{ color: theme.text }}>{product.name}</h3>
                          <div className="flex items-center justify-between mt-1">
                            <span className="text-sm font-bold" style={{ color: theme.primary }}>${product.price.toFixed(2)}</span>
                            <span className="text-[9px] text-gray-400">{product.stock}</span>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            )
          ) : (
            // Single category compact grid
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-2">
              {filteredProducts.map(product => (
                <button key={product.id}
                  onClick={() => addToCart(product)}
                  className="bg-white rounded-lg border hover:shadow-md hover:-translate-y-0.5 transition-all overflow-hidden text-left active:scale-95"
                  data-testid={`product-${product.id}`}>
                  <img src={product.image || 'https://placehold.co/200x100/e5e7eb/9ca3af?text=NUA'} alt={product.name} className="w-full h-16 object-cover" />
                  <div className="p-2">
                    <h3 className="font-medium text-xs leading-tight line-clamp-1" style={{ color: theme.text }}>{product.name}</h3>
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-sm font-bold" style={{ color: theme.primary }}>${product.price.toFixed(2)}</span>
                      <span className="text-[9px] text-gray-400">{product.stock}</span>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
        {/* Active Promotions */}
        {promotions.filter(p => p.active).length > 0 && (
          <div className="mt-2 p-2.5 bg-gradient-to-r from-yellow-50 to-orange-50 rounded-lg border border-yellow-200">
            <div className="flex gap-2 overflow-x-auto items-center">
              <h3 className="text-[10px] font-bold uppercase text-yellow-700 whitespace-nowrap">Promotions</h3>
              {promotions.filter(p => p.active).map(promo => (
                <div key={promo.id} className="bg-white px-3 py-1.5 rounded-md border text-xs whitespace-nowrap">
                  <span className="font-medium">{promo.name}</span>
                  <span className="ml-2 font-bold" style={{ color: theme.accent }}>{promo.discount}% OFF</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Cart Panel — bigger for easier billing */}
      <div className="w-[440px] flex-shrink-0 flex flex-col border bg-white rounded-xl shadow-sm p-4" data-testid="pos-cart-panel">
        <h2 className="text-xl font-bold mb-3" style={{ color: theme.text }}>{labels.cart || 'Current Order'}</h2>
        {/* Customer Selection */}
        <Card className="mb-4"><CardContent className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <User size={18} style={{ color: theme.primary }} />
            <span className="font-medium text-sm">Customer</span>
          </div>
          {selectedCustomer ? (
            <div>
              <div className="flex items-center justify-between">
                <div><p className="font-medium">{selectedCustomer.name}</p><p className="text-xs text-gray-500">{selectedCustomer.membershipTier} Member {pointsBalance !== null && <span className="ml-1 text-amber-600 font-semibold">⭐ {pointsBalance} pts</span>}</p></div>
                <Button variant="ghost" size="sm" onClick={() => { setSelectedCustomer(null); setPointsBalance(null); setPointsToRedeem(0); }}>Remove</Button>
              </div>
              {pointsBalance !== null && pointsBalance >= loyaltyCfg.minRedeem && (
                <div className="mt-2 p-2 bg-amber-50 rounded text-xs space-y-1" data-testid="points-pay-block">
                  <p className="text-amber-700 font-medium">Points & Pay (1 pt = ${loyaltyCfg.redeemRate} · min {loyaltyCfg.minRedeem})</p>
                  <div className="flex gap-1 items-center">
                    <Input type="number" min={loyaltyCfg.minRedeem} max={pointsBalance} step="10" value={pointsToRedeem || ''} placeholder={`${loyaltyCfg.minRedeem}-${pointsBalance}`} onChange={e => setPointsToRedeem(Math.min(pointsBalance, parseInt(e.target.value) || 0))} className="h-7 text-xs" data-testid="points-input" />
                    <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => setPointsToRedeem(pointsBalance)} data-testid="use-all-pts">All</Button>
                  </div>
                  {pointsToRedeem >= loyaltyCfg.minRedeem && <p className="text-green-700 font-semibold" data-testid="redeem-value">Discount: ${(pointsToRedeem * loyaltyCfg.redeemRate).toFixed(2)}</p>}
                </div>
              )}
            </div>
          ) : (
            <select className="w-full p-2 border rounded-md text-sm"
              onChange={async (e) => {
                const c = customers.find(c => c.id === e.target.value);
                setSelectedCustomer(c);
                if (c) {
                  try { const r = await loyaltyEngineAPI.getBalance(c.id); setPointsBalance(r.data?.points || 0); } catch {}
                  // Your Usual
                  try { const r = await phaseEFAPI.yourUsual(c.id); setYourUsual(r.data?.items || []); } catch {}
                } else { setYourUsual([]); }
              }}
              data-testid="pos-customer-select">
              <option value="">Walk-in Customer</option>
              {customers.map(c => <option key={c.id} value={c.id}>{c.name} ({c.membershipTier})</option>)}
            </select>
          )}
        </CardContent></Card>

        {/* Your Usual — predictive suggestions for known customer */}
        {selectedCustomer && yourUsual.length > 0 && (
          <Card className="mb-3 border-amber-200 bg-amber-50" data-testid="your-usual">
            <CardContent className="p-3">
              <p className="text-xs font-bold uppercase tracking-wider text-amber-700 mb-2">⭐ Your Usual</p>
              <div className="flex gap-2 overflow-x-auto">
                {yourUsual.map(p => (
                  <button key={p.id} onClick={() => { const prod = products.find(pp => pp.id === p.id); if (prod) addToCart(prod); }} className="flex-shrink-0 bg-white border rounded-lg p-2 hover:shadow-md transition-all min-w-[110px]" data-testid={`usual-${p.id}`}>
                    {p.image && <img src={p.image} alt={p.name} className="w-full h-12 object-cover rounded mb-1" />}
                    <p className="text-xs font-medium truncate">{p.name}</p>
                    <p className="text-xs text-gray-500">${p.price} · {p.frequency}×</p>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
        <div className="flex-1 overflow-y-auto mb-4">
          {cart.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <ShoppingCart size={48} className="mx-auto mb-3 opacity-50" /><p>Cart is empty</p><p className="text-sm">Tap a product to add</p>
            </div>
          ) : (
            <div className="space-y-2">
              {cart.map(item => (
                <SwipeableCartItem
                  key={item.id}
                  item={item}
                  theme={theme}
                  onUpdateQty={updateQuantity}
                  onRemove={removeFromCart}
                  onRepeat={(it) => { addToCart(it); toast({ title: 'Repeated', description: `Added another ${it.name}` }); }}
                />
              ))}
            </div>
          )}
        </div>

        {/* Totals + Loyalty preview */}
        {cart.length > 0 && (
          <Card className="mb-4"><CardContent className="p-4 space-y-2">
            <div className="flex justify-between text-sm"><span>{labels.subtotal || 'Subtotal'}</span><span>${totals.subtotal}</span></div>
            <div className="flex justify-between text-sm"><span>{labels.tax || 'GST (10%)'}</span><span>${totals.gst}</span></div>
            {totals.pointsDiscount && (
              <div className="flex justify-between text-sm text-green-700" data-testid="points-discount-row">
                <span>⭐ Points redeemed ({pointsToRedeem} pts)</span><span>-${totals.pointsDiscount}</span>
              </div>
            )}
            {selectedCustomer && (
              <div className="flex justify-between text-xs bg-amber-50 -mx-2 px-2 py-1 rounded" data-testid="loyalty-preview">
                <span className="text-amber-700">⭐ Loyalty preview</span>
                <span className="font-bold text-amber-700">+{Math.floor(parseFloat(totals.total))} pts</span>
              </div>
            )}
            <div className="border-t pt-2 flex justify-between font-bold text-lg"><span>{labels.total || 'Total'}</span><span style={{ color: theme.primary }} data-testid="pos-total">${totals.total}</span></div>
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
              <Button className="h-14 flex-col gap-1" variant="outline" onClick={() => { setCashTendered(0); setPaymentView('cash'); }} data-testid="pay-cash">
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
            <Button className="w-full h-12 bg-emerald-700 hover:bg-emerald-800 text-white font-medium"
              onClick={() => { toast({ title: 'BNPL', description: 'Afterpay / Klarna — opening provider redirect (configure keys in Integrations)' }); }} data-testid="pay-bnpl">
              <CreditCard size={18} className="mr-2" /> Pay Later (Afterpay / Klarna)
            </Button>
            <Button className="w-full h-12 bg-orange-500 hover:bg-orange-600 text-white font-medium"
              onClick={() => { toast({ title: 'Crypto', description: 'USDC tap-to-pay via Stripe Crypto — configure keys in Integrations' }); }} data-testid="pay-crypto">
              ₿ Pay with Crypto (USDC)
            </Button>
            <Button className="w-full h-14 bg-indigo-600 hover:bg-indigo-700 text-white font-medium"
              onClick={handleStartSplit} data-testid="pay-split">
              <SplitSquareHorizontal size={20} className="mr-2" /> Split Payment
            </Button>
            <Button className="w-full" variant="ghost" onClick={resetPayment} data-testid="pay-cancel">Cancel</Button>
          </div>
        )}

        {/* Cash Payment Panel */}
        {showPayment && paymentView === 'cash' && (
          <div className="space-y-3" data-testid="cash-payment-panel">
            {!showCashChange ? (
              <>
                <div className="text-center p-3 bg-gray-100 rounded-lg">
                  <p className="text-sm text-gray-500">Amount Due</p>
                  <p className="text-3xl font-bold" style={{ color: theme.primary }}>${totalNum.toFixed(2)}</p>
                </div>
                <p className="text-sm font-medium text-gray-600 text-center">Select amount tendered</p>
                <div className="grid grid-cols-3 gap-2">
                  <Button variant="outline" className="h-12 font-bold" onClick={() => { setCashTendered(totalNum); setShowCashChange(true); }} data-testid="cash-exact">Exact</Button>
                  <Button variant="outline" className="h-12 font-bold" onClick={() => { setCashTendered(Math.ceil(totalNum)); setShowCashChange(true); }} data-testid="cash-round">Round Up</Button>
                  {[5, 10, 20, 50, 100].map(amt => (
                    <Button key={amt} variant="outline" className="h-12 font-bold" disabled={amt < totalNum}
                      onClick={() => { setCashTendered(amt); setShowCashChange(true); }} data-testid={`cash-${amt}`}>
                      ${amt}
                    </Button>
                  ))}
                  <Button variant="outline" className="h-12 font-bold col-span-3" onClick={() => {
                    const custom = prompt('Enter amount tendered:');
                    if (custom && parseFloat(custom) >= totalNum) { setCashTendered(parseFloat(custom)); setShowCashChange(true); }
                    else if (custom) toast({ title: "Error", description: "Amount must be >= total", variant: "destructive" });
                  }} data-testid="cash-custom">Custom Amount</Button>
                </div>
                <Button variant="ghost" className="w-full" onClick={() => setPaymentView('methods')}><ChevronLeft size={16} className="mr-1" /> Back</Button>
              </>
            ) : (
              <div className="space-y-3">
                <div className="text-center p-4 bg-emerald-50 rounded-lg border border-emerald-200">
                  <p className="text-sm text-gray-600">Tendered</p>
                  <p className="text-2xl font-bold text-emerald-700">${cashTendered.toFixed(2)}</p>
                </div>
                <div className="text-center p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <p className="text-sm text-gray-600">Change Due</p>
                  <p className="text-3xl font-bold text-blue-700" data-testid="cash-change">${(cashTendered - totalNum).toFixed(2)}</p>
                </div>
                <Button className="w-full h-14 text-lg font-semibold bg-emerald-600 hover:bg-emerald-700 text-white"
                  onClick={() => { handleCheckout('Cash'); setShowCashChange(false); }} data-testid="cash-complete">
                  Complete Sale
                </Button>
                <Button variant="ghost" className="w-full" onClick={() => setShowCashChange(false)}>Back</Button>
              </div>
            )}
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

      {/* Ghost Discount (Owner Secret - triple-click POS title to show) */}
      {user?.role === 'owner' && (
        <Dialog open={showGhost} onOpenChange={setShowGhost}>
          <DialogContent className="max-w-xs" data-testid="ghost-discount-dialog">
            <DialogHeader><DialogTitle className="text-red-600">Ghost Void</DialogTitle></DialogHeader>
            <div className="space-y-3 py-2">
              <p className="text-xs text-gray-500">This discount will NOT appear in sales, inventory, or any reports.</p>
              <Input type="number" step="0.01" placeholder="Discount amount" value={ghostAmount}
                onChange={e => setGhostAmount(e.target.value)} data-testid="ghost-amount" />
              <p className="text-xs text-gray-400">Last transaction: {lastTxnId || 'None'}</p>
              <Button className="w-full bg-red-600 hover:bg-red-700 text-white" disabled={!lastTxnId || !ghostAmount}
                onClick={async () => {
                  try {
                    await menuFeaturesAPI.ghostDiscount({ transactionId: lastTxnId, amount: parseFloat(ghostAmount), reason: 'Owner void' });
                    toast({ title: "Ghost Applied", description: "Discount applied invisibly" });
                    setShowGhost(false); setGhostAmount('');
                  } catch { toast({ title: "Failed", variant: "destructive" }); }
                }} data-testid="apply-ghost-btn">Apply Ghost Void</Button>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* Open Tabs (Hold / Recall) */}
      <Dialog open={showTabsDialog} onOpenChange={setShowTabsDialog}>
        <DialogContent className="max-w-md" data-testid="tabs-dialog">
          <DialogHeader><DialogTitle>Open Tabs ({openTabs.length})</DialogTitle></DialogHeader>
          <div className="space-y-2 max-h-[60vh] overflow-y-auto">
            {openTabs.map(t => (
              <Card key={t.id} data-testid={`tab-${t.id}`}>
                <CardContent className="p-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-semibold text-sm">{t.name}</p>
                      <p className="text-xs text-gray-500">{t.cart?.length || 0} items · {t.createdByName} · {new Date(t.createdAt).toLocaleTimeString()}</p>
                    </div>
                    <div className="flex gap-1">
                      <Button size="sm" onClick={async () => {
                        clearCart();
                        (t.cart || []).forEach(i => { for (let n = 0; n < i.quantity; n++) addToCart({ ...i }); });
                        if (t.selectedCustomer) setSelectedCustomer(t.selectedCustomer);
                        await v15API.deleteTab(t.id);
                        setShowTabsDialog(false);
                        toast({ title: 'Tab recalled' });
                      }} style={{ backgroundColor: theme.primary }} data-testid={`recall-${t.id}`}>Recall</Button>
                      <Button size="sm" variant="outline" className="text-red-500" onClick={async () => { await v15API.deleteTab(t.id); setOpenTabs(openTabs.filter(o => o.id !== t.id)); }}>×</Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
            {openTabs.length === 0 && <p className="text-center text-gray-400 py-8 text-sm">No tabs on hold</p>}
          </div>
        </DialogContent>
      </Dialog>

    </div>
  );
};

export default POSTerminal;
