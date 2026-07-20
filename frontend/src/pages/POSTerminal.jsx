import React, { useState, useEffect, useCallback } from 'react';
import {
  Search, Plus, Minus, Trash2, User, CreditCard, Banknote, Smartphone,
  ShoppingCart, QrCode, SplitSquareHorizontal, X, Check, ChevronLeft, Copy
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle
} from '../components/ui/dialog';
import { useTheme } from '../contexts/ThemeContext';
import { usePOS } from '../contexts/POSContext';
import { productsAPI, promotionsAPI, customersAPI, transactionsAPI, paymentAPI, stripeAPI, advancedAPI, menuFeaturesAPI, gamificationAPI, v15API, loyaltyEngineAPI, phaseEFAPI, aiWave2API, v26API, floorPlansAPI } from '../services/api';
import { useToast } from '../hooks/use-toast';
import { useAuth } from '../contexts/AuthContext';
import VoiceOrderButton from '../components/VoiceOrderButton';
import SwipeableCartItem from '../components/pos/SwipeableCartItem';
import CustomerCombobox from '../components/pos/CustomerCombobox';
import { QrPaymentDialog, UpiPaymentDialog, SplitPaymentDialog } from '../components/pos/PaymentDialogs';
import ModifierSheet from '../components/pos/ModifierSheet';
import POSHeaderBar from '../components/pos/POSHeaderBar';
import { CategoryIcon } from './Categories';

// SwipeableCartItem and CustomerCombobox now live in components/pos/.

const POSTerminal = () => {
  const { theme } = useTheme();
  const { user } = useAuth();
  const { cart, addToCart, removeFromCart, updateQuantity, clearCart, calculateTotal, selectedCustomer, setSelectedCustomer, currentUser, currentLocation, appliedDiscounts, addDiscount, removeDiscount, appliedGiftCards, addGiftCard, removeGiftCard, pendingGiftActivations } = usePOS();
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
  // Send-to-table flow: opens a floor picker so the server can attach the
  // current cart to a specific table as an open tab (defers payment).
  const [sendToTableOpen, setSendToTableOpen] = useState(false);
  const [floorTables, setFloorTables] = useState([]);
  const [sendingToTable, setSendingToTable] = useState(false);
  const [labels, setLabels] = useState({});
  // v17: Points-and-Pay
  const [pointsBalance, setPointsBalance] = useState(null);
  // Customer wallet: store credit + active vouchers + occasion offers
  const [wallet, setWallet] = useState(null);
  // Category "More" overflow panel open state
  const [showMoreCats, setShowMoreCats] = useState(false);
  const [pointsToRedeem, setPointsToRedeem] = useState(0);
  const [loyaltyCfg, setLoyaltyCfg] = useState({ minRedeem: 10, redeemRate: 0.01 });

  // Wave 2: AI Upsell suggestions
  const [upsells, setUpsells] = useState([]);
  const [upsellLoading, setUpsellLoading] = useState(false);

  // Your Usual — predictive items per known customer
  const [yourUsual, setYourUsual] = useState([]);

  // Voucher / coupon manual entry
  const [voucherCode, setVoucherCode] = useState('');
  const [voucherLoading, setVoucherLoading] = useState(false);
  const [showDiscountPicker, setShowDiscountPicker] = useState(false);
  const [availableVouchers, setAvailableVouchers] = useState([]);

  // Gift-card tender
  const [giftCodeInput, setGiftCodeInput] = useState('');
  const [giftLoading, setGiftLoading] = useState(false);

  // Order context: table # / takeaway / walk-in customer name
  const [orderType, setOrderType] = useState('dine-in'); // dine-in | takeaway
  const [tableNumber, setTableNumber] = useState('');
  const [walkInName, setWalkInName] = useState('');

  // Active promotions (only currently-live ones for staff context)
  const [activePromos, setActivePromos] = useState([]);
  // Collapsed category sections in the "All" grouped view
  const [collapsedCats, setCollapsedCats] = useState([]);

  // Categories with icons + colors (kept as full objects, not just names)
  const [categories, setCategories] = useState([{ id: 'all', name: 'All', icon: 'Sparkles', color: '#6366f1' }]);

  // Modifier definitions (loaded once); ModifierSheet state for click-to-add flow
  const [modifiers, setModifiers] = useState([]);
  const [modifierSheetProduct, setModifierSheetProduct] = useState(null);

  // Smart add-to-cart: if a product has modifierIds, open the picker first.
  // If modifier defs haven't loaded yet but the product has modifierIds,
  // still open the sheet (it will show a loading hint) rather than silently
  // skipping the selection step.
  const handleProductClick = useCallback((product) => {
    if (product.eightySixed) return;
    if ((product.modifierIds || []).length > 0) {
      setModifierSheetProduct(product);
    } else {
      addToCart(product);
    }
  }, [addToCart]);

  // Map a cart line into a backend TransactionItem (flattens selectedModifiers
  // → modifiers list of {modifierId, modifierName, optionId, optionName, price}).
  const toTxItem = useCallback((item, includeCategory = false) => {
    const modifiersFlat = (item.selectedModifiers || []).flatMap(sm =>
      (sm.options || []).map(o => ({
        modifierId: sm.modifierId,
        modifierName: sm.modifierName,
        optionId: o.name,
        optionName: o.name,
        price: o.price || 0,
      }))
    );
    const out = {
      productId: item.productId || item.id,
      productName: item.name,
      quantity: item.quantity,
      price: item.price,
      modifiers: modifiersFlat,
    };
    if (includeCategory) out.category = item.category;
    return out;
  }, []);

  useEffect(() => { fetchData(); }, []);

  // Wave 2 — Fetch AI upsell suggestions whenever the cart changes (debounced)
  useEffect(() => {
    if (!cart || cart.length === 0) { setUpsells([]); return; }
    const t = setTimeout(async () => {
      try {
        setUpsellLoading(true);
        const r = await aiWave2API.upsell(cart.map(i => ({ productId: i.id, name: i.name, quantity: i.quantity, price: i.price })));
        setUpsells(r.data?.suggestions || []);
      } catch { setUpsells([]); }
      finally { setUpsellLoading(false); }
    }, 1200);
    return () => clearTimeout(t);
  }, [cart]);

  // v26 — auto-apply scheduled promotions whenever the cart changes.
  // Manually selected vouchers stay sticky (keyed by voucherId).
  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      // Drop stale auto-promotions before re-evaluating
      (appliedDiscounts || [])
        .filter(d => d.promotionId)
        .forEach(d => removeDiscount(d.promotionId));
      if (!cart || cart.length === 0) return;
      try {
        const items = cart.map(i => ({
          productId: i.id, id: i.id, name: i.name, price: i.price, quantity: i.quantity, category: i.category,
        }));
        const r = await v26API.applyPromos(items);
        if (cancelled) return;
        (r.data?.applied || []).forEach(p => addDiscount({
          promotionId: p.promotionId, label: p.label, discount: p.discount, auto: true,
        }));
      } catch {}
    };
    run();
    return () => { cancelled = true; };
    // Intentionally only depend on cart contents — avoids feedback loop with appliedDiscounts
  }, [cart]);  // eslint-disable-line

  // Push live cart to the customer-facing display (debounced ~400ms)
  useEffect(() => {
    const t = setTimeout(() => {
      v26API.cfdPush({
        cart: cart.map(i => ({ id: i.id, name: i.name, price: i.price, quantity: i.quantity, image: i.image })),
        selectedCustomer: selectedCustomer ? { id: selectedCustomer.id, name: selectedCustomer.name, membershipTier: selectedCustomer.membershipTier } : null,
        tableNumber, walkInName,
      }).catch(() => {});
    }, 400);
    return () => clearTimeout(t);
  }, [cart, selectedCustomer, tableNumber, walkInName]);

  // Live-update products & categories every 12s + on tab focus so any edit done in
  // another window reflects without a manual refresh.
  useEffect(() => {
    const refresh = async () => {
      try {
        const [p, c] = await Promise.all([productsAPI.getAll(), v26API.activePromos?.()]);
        if (Array.isArray(p?.data)) setProducts(p.data);
        if (Array.isArray(c?.data)) setActivePromos(c.data);
      } catch {}
    };
    refresh();
    const id = setInterval(refresh, 12000);
    const onFocus = () => refresh();
    window.addEventListener('focus', onFocus);
    return () => { clearInterval(id); window.removeEventListener('focus', onFocus); };
  }, []);

  // Load available vouchers once when discount picker opens
  useEffect(() => {
    if (!showDiscountPicker) return;
    v26API.listVouchers().then(r => setAvailableVouchers(r.data || [])).catch(() => {});
  }, [showDiscountPicker]);

  const applyManualCode = async () => {
    const code = (voucherCode || '').trim().toUpperCase();
    if (!code) return;
    setVoucherLoading(true);
    try {
      const items = cart.map(i => ({ productId: i.id, id: i.id, name: i.name, price: i.price, quantity: i.quantity, category: i.category }));
      const r = await v26API.applyVoucher(code, items);
      const v = r.data?.voucher || {};
      addDiscount({ voucherId: v.id, label: `${v.name} · ${r.data.message}`, discount: r.data.discount, code });
      toast({ title: 'Voucher applied', description: r.data.message });
      setVoucherCode('');
      setShowDiscountPicker(false);
    } catch (e) {
      toast({ title: 'Could not apply', description: e?.response?.data?.detail || 'Invalid code', variant: 'destructive' });
    } finally { setVoucherLoading(false); }
  };

  const applyAvailableVoucher = async (v) => {
    try {
      const items = cart.map(i => ({ productId: i.id, id: i.id, name: i.name, price: i.price, quantity: i.quantity, category: i.category }));
      const r = await v26API.applyVoucher(v.manualCode || v.barcode || v.id, items);
      addDiscount({ voucherId: v.id, label: `${v.name} · ${r.data.message}`, discount: r.data.discount, code: v.manualCode });
      toast({ title: 'Applied', description: r.data.message });
      setShowDiscountPicker(false);
    } catch (e) {
      toast({ title: 'Could not apply', description: e?.response?.data?.detail || 'Conditions not met', variant: 'destructive' });
    }
  };

  // Look up a gift card, then auto-apply as a tender capped at the balance due.
  const applyGiftCard = async () => {
    const code = (giftCodeInput || '').trim().toUpperCase();
    if (!code) return;
    setGiftLoading(true);
    try {
      const r = await v26API.lookupGift(code);
      const card = r.data || {};
      if (card.status !== 'active') {
        toast({ title: 'Card not active', description: `Status: ${card.status}. Use after activation.`, variant: 'destructive' });
        return;
      }
      const balance = Number(card.currentBalance ?? card.amount ?? 0);
      if (balance <= 0) {
        toast({ title: 'Empty card', description: 'Balance is $0.00', variant: 'destructive' });
        return;
      }
      // Tender = min(balance, current balance due)
      const totalsNow = calculateTotal();
      const balanceDue = Number(totalsNow.balanceDue || totalsNow.total) || 0;
      const tender = Math.min(balance, balanceDue);
      if (tender <= 0) {
        toast({ title: 'No balance due', description: 'Cart already covered by other tenders', variant: 'destructive' });
        return;
      }
      addGiftCard({ code: card.code, giftCardId: card.id, balance, amount: tender });
      toast({ title: 'Gift card applied', description: `$${tender.toFixed(2)} (balance $${balance.toFixed(2)})` });
      setGiftCodeInput('');
      setShowDiscountPicker(false);
    } catch (e) {
      toast({ title: 'Gift card error', description: e?.response?.data?.detail || 'Not found', variant: 'destructive' });
    } finally { setGiftLoading(false); }
  };

  const fetchData = async () => {
    try {
      // Run all initial fetches in parallel for max speed
      const [productsRes, promotionsRes, customersRes, catsRes, modsRes, loyaltyRes, labelsRes, trainingRes] = await Promise.allSettled([
        productsAPI.getAll(),
        promotionsAPI.getActive(),
        customersAPI.getAll(),
        fetch(`${process.env.REACT_APP_BACKEND_URL}/api/categories`).then(r => r.json()).catch(() => []),
        fetch(`${process.env.REACT_APP_BACKEND_URL}/api/modifiers`).then(r => r.json()).catch(() => []),
        loyaltyEngineAPI.getConfig(),
        v15API.getLabels(localStorage.getItem('nua_lang') || 'en'),
        advancedAPI.getTrainingMode(),
      ]);
      if (productsRes.status === 'fulfilled') setProducts(productsRes.value.data || []);
      if (promotionsRes.status === 'fulfilled') setPromotions(promotionsRes.value.data || []);
      if (customersRes.status === 'fulfilled') setCustomers(customersRes.value.data || []);
      if (catsRes.status === 'fulfilled' && Array.isArray(catsRes.value)) {
        const active = catsRes.value
          .filter(c => c.active !== false)
          .sort((a, b) => (a.sortOrder ?? 99) - (b.sortOrder ?? 99))
          .map(c => ({ id: c.id, name: c.name, icon: c.icon || 'Tag', color: c.color || '#6366f1' }));
        setCategories([{ id: 'all', name: 'All', icon: 'Sparkles', color: '#6366f1' }, ...active]);
      }
      if (modsRes.status === 'fulfilled' && Array.isArray(modsRes.value)) {
        setModifiers(modsRes.value);
      }
      if (loyaltyRes.status === 'fulfilled') setLoyaltyCfg(loyaltyRes.value.data || { minRedeem: 10, redeemRate: 0.01 });
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
  const redeemDiscount = pointsToRedeem >= (loyaltyCfg.minRedeem || 10) ? pointsToRedeem * (loyaltyCfg.redeemRate || 0.01) : 0;
  const totals = redeemDiscount > 0
    ? { ...totalsRaw, total: Math.max(0, parseFloat(totalsRaw.total) - redeemDiscount).toFixed(2),
        balanceDue: Math.max(0, parseFloat(totalsRaw.balanceDue || totalsRaw.total) - redeemDiscount).toFixed(2),
        pointsDiscount: redeemDiscount.toFixed(2) }
    : totalsRaw;
  // The amount we charge through the chosen payment method = balance due (after gift cards).
  const totalNum = parseFloat(totals.balanceDue || totals.total) || 0;
  const grossTotal = parseFloat(totals.total) || 0;

  // Settle gift cards after a successful payment: activate sold-cards, redeem tenders.
  const settleGiftCards = async (txId) => {
    for (const card of (pendingGiftActivations || [])) {
      try { await v26API.activateGift(card.code, { transactionId: txId }); }
      catch (e) { console.warn('Gift activation failed', card.code, e); }
    }
    for (const gc of (appliedGiftCards || [])) {
      try {
        if (gc.amount > 0) await v26API.redeemGiftPartial(gc.code, gc.amount, txId);
      } catch (e) { console.warn('Gift redeem failed', gc.code, e); }
    }
  };

  // Discounts applied on screen, in the shape POST /transactions records
  // (backend recomputes totals from these — keep in sync with calculateTotal).
  const buildDiscountPayload = () => ({
    appliedDiscounts: (appliedDiscounts || []).map(d => ({
      label: d.label || '', amount: Number(d.discount) || 0,
      promotionId: d.promotionId || null, voucherId: d.voucherId || null, code: d.code || null,
    })),
    pointsRedeemed: pointsToRedeem || 0,
    pointsDiscount: redeemDiscount || 0,
  });

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
        items: cart.map(item => toTxItem(item, true)),
        paymentMethod, customerId: selectedCustomer?.id || null, location: currentLocation, cashier: currentUser.name,
        orderType, tableNumber: orderType === 'dine-in' ? tableNumber : null, walkInName: orderType === 'takeaway' ? walkInName : null,
        ...buildDiscountPayload(),
      });
      setLastTxnId(res.data?.id || null);
      // Loyalty: redeem first (if applicable), then earn on net spend
      if (selectedCustomer && pointsToRedeem >= (loyaltyCfg.minRedeem || 10)) {
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
      // Settle gift cards: activate any pending-sold cards + redeem applied tenders.
      await settleGiftCards(res.data?.id);
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
      const res = await transactionsAPI.create({
        items: cart.map(item => toTxItem(item)),
        paymentMethod: paymentView === 'upi' ? 'UPI' : 'QR Code',
        customerId: selectedCustomer?.id || null, location: currentLocation, cashier: currentUser.name,
        ...buildDiscountPayload(),
      });
      toast({ title: "Payment Confirmed!", description: `$${totalNum.toFixed(2)} received via ${paymentView === 'upi' ? 'UPI' : 'QR Code'}` });
      await settleGiftCards(res.data?.id);
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
    const part = splitParts[idx];
    // ---- Validation: catch wrong / missing / overshoot amounts BEFORE we charge.
    const amt = Number(part.amount) || 0;
    if (amt <= 0) {
      toast({ title: "Invalid amount", description: `Split #${idx + 1} must be greater than $0.`, variant: "destructive" });
      return;
    }
    // Tolerate 1¢ rounding noise, but reject anything that overshoots the bill.
    if (amt > splitRemaining + 0.005) {
      toast({
        title: "Amount exceeds remaining",
        description: `Only $${splitRemaining.toFixed(2)} remaining — Split #${idx + 1} is $${amt.toFixed(2)}.`,
        variant: "destructive",
      });
      return;
    }
    setActiveSplitIndex(idx);
    setLoading(true);
    try {
      if (part.method === 'UPI' || part.method === 'QR Code') {
        const res = await paymentAPI.generateQR({ amount: part.amount, method: part.method === 'UPI' ? 'upi' : 'qr_code' });
        await paymentAPI.confirm(res.data.paymentId);
      }
      updateSplitPart(idx, 'status', 'confirmed');
      toast({ title: `Split #${idx + 1} Paid`, description: `$${part.amount.toFixed(2)} from ${part.payerName}` });

      // Check if all paid AND the maths balances
      const updatedParts = splitParts.map((s, i) => i === idx ? { ...s, status: 'confirmed' } : s);
      const allPaid = updatedParts.every(s => s.status === 'confirmed');
      if (allPaid) {
        const totalPaid = updatedParts.reduce((sum, s) => sum + Number(s.amount || 0), 0);
        // Defensive: refuse to finalise if the splits don't add up.
        if (Math.abs(totalPaid - totalNum) > 0.01) {
          toast({
            title: "Split doesn't balance",
            description: `Collected $${totalPaid.toFixed(2)} vs bill $${totalNum.toFixed(2)}. Adjust amounts before closing.`,
            variant: "destructive",
          });
          // Revert the just-confirmed status so the cashier can fix it
          updateSplitPart(idx, 'status', 'pending');
          return;
        }
        const res = await transactionsAPI.create({
          items: cart.map(item => toTxItem(item)),
          paymentMethod: 'Split Payment',
          customerId: selectedCustomer?.id || null, location: currentLocation, cashier: currentUser.name,
          splitDetails: updatedParts.map(s => ({ payerName: s.payerName, amount: s.amount, method: s.method })),
          ...buildDiscountPayload(),
        });
        toast({ title: "All Splits Paid!", description: `Total $${totalNum.toFixed(2)} collected` });
        await settleGiftCards(res.data?.id);
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
    <div className="flex flex-col lg:flex-row gap-4 h-[calc(100vh-7rem)]" data-testid="pos-terminal">
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
          {/* Compact status bar replaces the bulky "POS Terminal" title */}
          <div onDoubleClick={() => { if (user?.role === 'owner') setShowGhost(true); }} data-testid="pos-title">
            <POSHeaderBar themeColor={theme.primary} />
          </div>
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
          {activePromos.length > 0 && (
            <div className="flex gap-1.5 overflow-x-auto pb-1.5" data-testid="active-promos-strip">
              <span className="text-[10px] font-bold uppercase tracking-wider text-amber-700 flex items-center bg-amber-100 px-2 rounded-full shrink-0">
                🔥 Live now
              </span>
              {activePromos.map(p => (
                <span key={p.id}
                  className="text-[11px] font-semibold whitespace-nowrap px-2.5 py-1 rounded-full border shrink-0"
                  style={{ background: `${theme.primary}10`, borderColor: `${theme.primary}40`, color: theme.primary }}
                  title={`${p.discount}% off · ${(p.activeDays || []).join(',') || 'all days'} ${p.startTime || ''}–${p.endTime || ''}`}
                  data-testid={`active-promo-${p.id}`}>
                  {p.name} · {p.discount}% off
                </span>
              ))}
            </div>
          )}
          {/* Category bar — compact pills, max 6 visible + "More" overflow panel.
              A category picked from the overflow is promoted into the visible
              row, so frequent switches stay one tap away. */}
          {(() => {
            const MAX_VISIBLE = 6;
            const all = categories[0];                    // 'All' is always first
            const rest = categories.slice(1);
            let visible = rest.slice(0, MAX_VISIBLE);
            let overflow = rest.slice(MAX_VISIBLE);
            if (overflow.length === 1) { visible = rest; overflow = []; }
            const selInOverflow = overflow.find(c => c.name === selectedCategory);
            if (selInOverflow) {
              overflow = [visible[visible.length - 1], ...overflow.filter(c => c.name !== selectedCategory)];
              visible = [...visible.slice(0, -1), selInOverflow];
            }
            const pill = (cat) => {
              const active = selectedCategory === cat.name;
              return (
                <button key={cat.id || cat.name}
                  onClick={() => { setSelectedCategory(cat.name); setShowMoreCats(false); }}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full whitespace-nowrap transition-all flex-shrink-0 text-xs font-semibold ${active ? 'text-white shadow-md' : 'bg-white text-gray-700 border hover:border-gray-400'}`}
                  style={active ? { backgroundColor: cat.color || theme.primary } : { borderColor: `${cat.color || theme.primary}40` }}
                  data-testid={`pos-cat-${cat.name}`}>
                  <CategoryIcon name={cat.icon} size={14} />
                  {cat.name}
                </button>
              );
            };
            return (
              <div className="relative">
                <div className="flex gap-1.5 overflow-x-auto pb-1.5 items-center">
                  {pill(all)}
                  {visible.map(pill)}
                  {overflow.length > 0 && (
                    <button onClick={() => setShowMoreCats(v => !v)}
                      className={`flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-semibold border flex-shrink-0 transition-all ${showMoreCats ? 'text-white' : 'bg-gray-50 text-gray-600 hover:border-gray-400'}`}
                      style={showMoreCats ? { backgroundColor: theme.primary } : {}}
                      data-testid="pos-cat-more">
                      More · {overflow.length} {showMoreCats ? '▴' : '▾'}
                    </button>
                  )}
                </div>
                {showMoreCats && overflow.length > 0 && (
                  <div className="absolute z-30 mt-1 left-0 right-0 bg-white border rounded-xl shadow-lg p-3 grid gap-1.5 [grid-template-columns:repeat(auto-fill,minmax(140px,1fr))]"
                    data-testid="pos-cat-overflow">
                    {overflow.map(cat => (
                      <button key={cat.id || cat.name}
                        onClick={() => { setSelectedCategory(cat.name); setShowMoreCats(false); }}
                        className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold text-gray-700 hover:bg-gray-50 border border-transparent hover:border-gray-200 text-left"
                        data-testid={`pos-cat-overflow-${cat.name}`}>
                        <span className="w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0"
                          style={{ background: `${cat.color || theme.primary}15`, color: cat.color || theme.primary }}>
                          <CategoryIcon name={cat.icon} size={14} />
                        </span>
                        {cat.name}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })()}
        </div>
        <div className="flex-1 overflow-y-auto pr-1">
          {selectedCategory === 'All' ? (
            products.length === 0 ? (
              // Skeleton loader while products fetch — fluid grid
              <div className="grid gap-2 [grid-template-columns:repeat(auto-fill,minmax(130px,1fr))]" data-testid="pos-skeleton">
                {[...Array(12)].map((_, i) => (
                  <div key={i} className="bg-white rounded-lg border overflow-hidden animate-pulse">
                    <div className="w-full h-20 bg-gray-200" />
                    <div className="p-2 space-y-1">
                      <div className="h-3 bg-gray-200 rounded" />
                      <div className="h-3 bg-gray-100 rounded w-2/3" />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
            // Category-wise grouped view — fluid grid that adapts to viewport.
            <div className="space-y-5">
              {Object.entries(groupedByCategory).map(([cat, prods]) => {
                const meta = categories.find(c => c.name === cat);
                const collapsed = collapsedCats.includes(cat);
                return (
                <div key={cat} data-testid={`pos-category-section-${cat}`}>
                  <button
                    onClick={() => setCollapsedCats(cs => cs.includes(cat) ? cs.filter(x => x !== cat) : [...cs, cat])}
                    className="flex items-center gap-2 mb-2 sticky top-0 bg-gray-50 py-1.5 z-[1] w-full"
                    data-testid={`collapse-toggle-${cat}`}>
                    <span className="text-gray-400 text-xs">{collapsed ? '▶' : '▼'}</span>
                    {meta && <div className="w-6 h-6 rounded-md flex items-center justify-center text-white" style={{ background: meta.color }}><CategoryIcon name={meta.icon} size={13} /></div>}
                    <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500">{cat}</h3>
                    <span className="text-[10px] text-gray-400">{prods.length} items</span>
                    <div className="flex-1 border-b border-dashed"></div>
                  </button>
                  {!collapsed && (
                  <div className="grid gap-2 [grid-template-columns:repeat(auto-fill,minmax(130px,1fr))]">
                    {prods.map(product => (
                      <button key={product.id}
                        onClick={() => handleProductClick(product)}
                        disabled={product.eightySixed}
                        className={`bg-white rounded-lg border transition-all overflow-hidden text-left active:scale-95 relative ${product.eightySixed ? 'opacity-50 cursor-not-allowed' : 'hover:shadow-md hover:-translate-y-0.5'}`}
                        data-testid={`product-${product.id}`}
                        data-product-card={product.id}>
                        <img src={product.image || 'https://placehold.co/200x100/e5e7eb/9ca3af?text=NUA'} alt={product.name} className="w-full h-20 object-cover" />
                        {product.eightySixed && (
                          <span className="absolute top-1 right-1 bg-red-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded">86</span>
                        )}
                        <div className="p-2">
                          <h3 className="font-medium text-xs leading-tight line-clamp-1" style={{ color: theme.text }}>{product.name}</h3>
                          <div className="flex items-center justify-between mt-1">
                            <span className="text-sm font-bold" style={{ color: theme.primary }}>${product.price.toFixed(2)}</span>
                            <span className="text-[9px] text-gray-400">{product.stock}</span>
                          </div>
                          {(product.modifierIds || []).length > 0 && (
                            <span className="text-[9px] mt-0.5 inline-block" style={{ color: theme.secondary }} data-testid={`pos-prod-mod-hint-${product.id}`}>
                              + {product.modifierIds.length} option{product.modifierIds.length > 1 ? 's' : ''}
                            </span>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                  )}
                </div>
              );})}
            </div>
            )
          ) : (
            // Single category compact grid — fluid
            <div className="grid gap-2 [grid-template-columns:repeat(auto-fill,minmax(130px,1fr))]">
              {filteredProducts.map(product => (
                <button key={product.id}
                  onClick={() => handleProductClick(product)}
                  disabled={product.eightySixed}
                  className={`bg-white rounded-lg border transition-all overflow-hidden text-left active:scale-95 relative ${product.eightySixed ? 'opacity-50 cursor-not-allowed' : 'hover:shadow-md hover:-translate-y-0.5'}`}
                  data-testid={`product-${product.id}`}
                  data-product-card={product.id}>
                  <img src={product.image || 'https://placehold.co/200x100/e5e7eb/9ca3af?text=NUA'} alt={product.name} className="w-full h-20 object-cover" />
                  {product.eightySixed && (
                    <span className="absolute top-1 right-1 bg-red-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded">86</span>
                  )}
                  <div className="p-2">
                    <h3 className="font-medium text-xs leading-tight line-clamp-1" style={{ color: theme.text }}>{product.name}</h3>
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-sm font-bold" style={{ color: theme.primary }}>${product.price.toFixed(2)}</span>
                      <span className="text-[9px] text-gray-400">{product.stock}</span>
                    </div>
                    {(product.modifierIds || []).length > 0 && (
                      <span className="text-[9px] mt-0.5 inline-block" style={{ color: theme.secondary }} data-testid={`pos-prod-mod-hint-flat-${product.id}`}>
                        + {product.modifierIds.length} option{product.modifierIds.length > 1 ? 's' : ''}
                      </span>
                    )}
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
      <div className="w-full lg:w-[440px] flex-shrink-0 flex flex-col border bg-white rounded-xl shadow-sm p-4" data-testid="pos-cart-panel">
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
                <Button variant="ghost" size="sm" onClick={() => { setSelectedCustomer(null); setPointsBalance(null); setPointsToRedeem(0); setWallet(null); }}>Remove</Button>
              </div>
              {/* Wallet: store credit + vouchers + occasion offers */}
              {wallet && (wallet.storeCredit > 0 || (wallet.vouchers || []).length > 0) && (
                <div className="mt-2 p-2 rounded-lg border border-emerald-200 bg-emerald-50/60 space-y-1.5" data-testid="customer-wallet">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-700">Wallet</p>
                  <div className="flex flex-wrap gap-1.5">
                    {wallet.storeCredit > 0 && (
                      <span className="text-[11px] font-semibold px-2 py-1 rounded-full bg-emerald-600 text-white" data-testid="wallet-store-credit">
                        💳 ${wallet.storeCredit.toFixed(2)} credit
                      </span>
                    )}
                    {(wallet.vouchers || []).map(v => {
                      const applied = (appliedDiscounts || []).some(d => d.voucherId === v.id);
                      return (
                        <button key={v.id} disabled={applied}
                          onClick={() => {
                            addDiscount({ voucherId: v.id, label: `${v.occasion || 'Voucher'} · $${Number(v.amount).toFixed(2)}`, discount: Number(v.amount) || 0 });
                            toast({ title: 'Voucher applied', description: `${v.occasion || v.reason || 'Wallet voucher'} — $${Number(v.amount).toFixed(2)} off` });
                          }}
                          className={`text-[11px] font-semibold px-2 py-1 rounded-full border transition-all ${applied ? 'bg-gray-200 text-gray-400 border-gray-200' : 'bg-white text-emerald-700 border-emerald-300 hover:bg-emerald-100'}`}
                          title={applied ? 'Already applied to this order' : `Tap to apply $${Number(v.amount).toFixed(2)} off`}
                          data-testid={`wallet-voucher-${v.id}`}>
                          {v.occasion ? v.occasion : `🎟 ${v.reason === 'win_back' ? 'We miss you' : 'Voucher'}`} ${Number(v.amount).toFixed(2)}
                          {applied ? ' ✓' : ''}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
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
            <>
              <CustomerCombobox
                customers={customers}
                value={null}
                theme={theme}
                onChange={async (c) => {
                  setSelectedCustomer(c);
                  if (c) {
                    try { const r = await loyaltyEngineAPI.getBalance(c.id); setPointsBalance(r.data?.points || 0); } catch {}
                    try { const r = await customersAPI.getWallet(c.id); setWallet(r.data); } catch { setWallet(null); }
                    try { const r = await phaseEFAPI.yourUsual(c.id); setYourUsual(r.data?.items || []); } catch {}
                  } else { setYourUsual([]); }
                }}
              />
              {/* Order-type strip — Dine-in / Takeaway + table picker + walk-in name */}
              <div className="mt-2 space-y-2" data-testid="order-type-strip">
                <div className="flex gap-1.5">
                  {[
                    { k: 'dine-in', label: '🍽️ Dine-in' },
                    { k: 'takeaway', label: '🥡 Takeaway' },
                  ].map(o => (
                    <button key={o.k}
                      onClick={() => { setOrderType(o.k); if (o.k === 'takeaway') setTableNumber(''); }}
                      className={`flex-1 px-2 py-1.5 rounded-md text-xs font-semibold transition ${orderType === o.k ? 'text-white shadow-sm' : 'bg-white border hover:border-gray-400'}`}
                      style={orderType === o.k ? { background: theme.primary } : {}}
                      data-testid={`order-type-${o.k}`}>
                      {o.label}
                    </button>
                  ))}
                </div>
                {orderType === 'dine-in' ? (
                  <div className="flex gap-2 items-center" data-testid="table-row">
                    <span className="text-xs text-gray-500 whitespace-nowrap">Table #</span>
                    <Input
                      placeholder="e.g. 12, Patio-A, Bar-3"
                      value={tableNumber}
                      onChange={e => setTableNumber(e.target.value)}
                      className="h-8 text-xs flex-1"
                      data-testid="table-input"
                    />
                  </div>
                ) : (
                  <div className="flex gap-2 items-center">
                    <span className="text-xs text-gray-500 whitespace-nowrap">Name</span>
                    <Input
                      placeholder="Customer name for takeaway"
                      value={walkInName}
                      onChange={e => setWalkInName(e.target.value)}
                      className="h-8 text-xs flex-1"
                      data-testid="walk-in-name"
                    />
                  </div>
                )}
              </div>
            </>
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

        {/* Wave 2 — AI Upsell strip */}
        {cart.length > 0 && (upsells.length > 0 || upsellLoading) && (
          <div className="mb-3" data-testid="upsell-strip">
            <div className="text-[10px] font-bold uppercase tracking-widest text-amber-700 mb-1.5 flex items-center gap-1.5">
              <span>✨ AI suggests</span>
              {upsellLoading && <span className="text-gray-400 normal-case font-normal">thinking…</span>}
            </div>
            <div className="flex gap-2 overflow-x-auto pb-1">
              {upsells.map(s => {
                const prod = products.find(p => p.id === s.productId);
                if (!prod) return null;
                return (
                  <button
                    key={s.productId}
                    onClick={() => { addToCart(prod); toast({ title: 'Added', description: s.reason || s.name }); }}
                    className="flex-shrink-0 bg-amber-50 border border-amber-200 rounded-lg p-2 hover:shadow-md hover:-translate-y-0.5 transition-all text-left min-w-[140px] max-w-[180px]"
                    data-testid={`upsell-${s.productId}`}
                  >
                    <div className="text-xs font-semibold text-amber-900 truncate">{s.name}</div>
                    <div className="text-[10px] text-amber-700 line-clamp-2">{s.reason || ''}</div>
                    <div className="text-xs font-bold text-amber-900 mt-1">+${Number(s.price).toFixed(2)}</div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Totals + Loyalty preview */}
        {cart.length > 0 && (
          <Card className="mb-4"><CardContent className="p-4 space-y-2">
            <div className="flex justify-between text-sm"><span>{labels.subtotal || 'Subtotal'}</span><span>${totals.subtotal}</span></div>
            {parseFloat(totals.tierDiscount) > 0 && (
              <div className="flex justify-between text-sm text-purple-700" data-testid="tier-discount-row">
                <span>👑 {selectedCustomer?.membershipTier} member discount</span>
                <span>-${totals.tierDiscount}</span>
              </div>
            )}
            {/* Applied discounts (auto promotions + manual vouchers) */}
            {(appliedDiscounts || []).map((d, i) => {
              const key = d.promotionId || d.voucherId || d.id;
              return (
                <div key={key || i} className="flex justify-between text-sm text-emerald-700" data-testid={`applied-discount-${key}`}>
                  <span className="flex items-center gap-1.5 truncate">
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-100">{d.auto ? 'AUTO' : 'VOUCHER'}</span>
                    <span className="truncate">{d.label}</span>
                  </span>
                  <span className="flex items-center gap-1.5">
                    -${Number(d.discount).toFixed(2)}
                    {!d.auto && (
                      <button onClick={() => removeDiscount(key)} className="text-emerald-600 hover:text-red-600" data-testid={`remove-discount-${key}`}>×</button>
                    )}
                  </span>
                </div>
              );
            })}
            <div className="flex justify-between text-sm"><span>{labels.tax || 'GST (10%)'}</span><span>${totals.gst}</span></div>
            {totals.pointsDiscount && (
              <div className="flex justify-between text-sm text-green-700" data-testid="points-discount-row">
                <span>⭐ Points redeemed ({pointsToRedeem} pts)</span><span>-${totals.pointsDiscount}</span>
              </div>
            )}
            {(appliedGiftCards || []).map(gc => (
              <div key={gc.code} className="flex justify-between text-sm text-violet-700" data-testid={`gift-tender-${gc.code}`}>
                <span className="flex items-center gap-1.5 truncate">
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-violet-100">GIFT</span>
                  <span className="font-mono truncate">{gc.code}</span>
                </span>
                <span className="flex items-center gap-1.5">
                  -${Number(gc.amount).toFixed(2)}
                  <button onClick={() => removeGiftCard(gc.code)} className="text-violet-600 hover:text-red-600" data-testid={`remove-gift-${gc.code}`}>×</button>
                </span>
              </div>
            ))}
            {selectedCustomer && (
              <div className="flex justify-between text-xs bg-amber-50 -mx-2 px-2 py-1 rounded" data-testid="loyalty-preview">
                <span className="text-amber-700">⭐ Loyalty preview</span>
                <span className="font-bold text-amber-700">+{Math.floor(parseFloat(totals.total))} pts</span>
              </div>
            )}
            <div className="border-t pt-2 flex justify-between font-bold text-lg"><span>{labels.total || 'Total'}</span><span style={{ color: theme.primary }} data-testid="pos-total">${totals.total}</span></div>
            {appliedGiftCards.length > 0 && (
              <div className="flex justify-between text-sm font-semibold text-violet-700" data-testid="pos-balance-due">
                <span>Balance due (after gift cards)</span><span>${totals.balanceDue}</span>
              </div>
            )}
          </CardContent></Card>
        )}

        {/* Discount picker — opens above Proceed to Payment */}
        {!showPayment && cart.length > 0 && (
          <Card className="mb-3"><CardContent className="p-3">
            {!showDiscountPicker ? (
              <Button variant="outline" className="w-full" onClick={() => setShowDiscountPicker(true)} data-testid="open-discount-picker">
                🎟️ Apply discount / voucher / gift card
              </Button>
            ) : (
              <div className="space-y-3">
                <div className="flex gap-2">
                  <Input value={voucherCode} onChange={e => setVoucherCode(e.target.value)}
                    placeholder="Voucher code (NUA-XXXX)" className="text-sm" data-testid="voucher-code-input" />
                  <Button onClick={applyManualCode} disabled={voucherLoading || !voucherCode} data-testid="apply-voucher-btn" style={{ background: theme.primary }}>
                    {voucherLoading ? '…' : 'Apply'}
                  </Button>
                </div>
                <div className="flex gap-2">
                  <Input value={giftCodeInput} onChange={e => setGiftCodeInput(e.target.value)}
                    placeholder="Gift card code (GC-XXXX)" className="text-sm" data-testid="gift-code-input" />
                  <Button onClick={applyGiftCard} disabled={giftLoading || !giftCodeInput} data-testid="apply-gift-btn"
                    className="bg-violet-600 hover:bg-violet-700 text-white">
                    {giftLoading ? '…' : '🎁 Apply'}
                  </Button>
                </div>
                {availableVouchers.length > 0 && (
                  <div className="space-y-1 max-h-44 overflow-y-auto" data-testid="voucher-list">
                    <p className="text-[10px] uppercase tracking-widest text-gray-500 font-bold">Available</p>
                    {availableVouchers.filter(v => v.active).map(v => (
                      <button key={v.id} onClick={() => applyAvailableVoucher(v)}
                        className="w-full text-left p-2 border rounded text-xs hover:bg-amber-50 hover:border-amber-300 transition" data-testid={`voucher-${v.id}`}>
                        <div className="flex justify-between font-semibold"><span>{v.name}</span><span className="text-amber-700">{v.discountType === 'percent' ? `${v.value}%` : `$${v.value}`} off</span></div>
                        <div className="text-[10px] text-gray-500 font-mono">{v.manualCode}</div>
                      </button>
                    ))}
                  </div>
                )}
                <Button variant="ghost" size="sm" onClick={() => setShowDiscountPicker(false)} className="w-full">Close</Button>
              </div>
            )}
          </CardContent></Card>
        )}

        {/* Send-to-Table + Payment buttons */}
        {!showPayment && cart.length > 0 && (
          <div className="flex gap-2" data-testid="pos-checkout-actions">
            <Button
              variant="outline"
              className="flex-1 h-14 text-base font-semibold"
              onClick={async () => {
                try {
                  const r = await floorPlansAPI.getAll();
                  const active = (r.data || []).find(p => p.active) || (r.data || [])[0];
                  setFloorTables(active?.tables || []);
                } catch { setFloorTables([]); }
                setSendToTableOpen(true);
              }}
              data-testid="pos-send-to-table">
              Send to Table
            </Button>
            <Button className="flex-1 h-14 text-base font-semibold" style={{ backgroundColor: theme.primary }}
              onClick={() => setShowPayment(true)} data-testid="pos-proceed-payment">
              Proceed to Payment
            </Button>
          </div>
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

      {/* ========== Payment Dialogs (QR / UPI / Split) ========== */}
      <QrPaymentDialog
        open={paymentView === 'qr'} onClose={() => setPaymentView('methods')}
        qrData={qrData} total={totalNum} onConfirm={handleConfirmQRPayment} loading={loading}
      />
      <UpiPaymentDialog
        open={paymentView === 'upi'} onClose={() => setPaymentView('methods')}
        qrData={qrData} total={totalNum} onConfirm={handleConfirmQRPayment} loading={loading}
        onCopyUpi={copyToClipboard}
      />
      <SplitPaymentDialog
        open={paymentView === 'split'} onClose={() => setPaymentView('methods')}
        total={totalNum}
        splitParts={splitParts} splitMode={splitMode} splitCount={splitCount}
        onSetMode={(m) => { setSplitMode(m); if (m === 'equal') initSplitParts(splitCount, 'equal'); }}
        onChangeCount={recalcEqualSplit}
        onUpdatePart={updateSplitPart}
        onPayPart={handlePaySplit}
        splitRemaining={splitRemaining}
        loading={loading} activeSplitIndex={activeSplitIndex}
      />

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

      {/* Send-to-Table dialog */}
      <Dialog open={sendToTableOpen} onOpenChange={setSendToTableOpen}>
        <DialogContent className="max-w-2xl" data-testid="send-to-table-dialog">
          <DialogHeader>
            <DialogTitle>Send order to a table</DialogTitle>
          </DialogHeader>
          <p className="text-xs text-gray-500 mb-2">Pick a table — the current cart becomes an open tab on that table so floor staff can settle it later.</p>
          <div className="grid grid-cols-3 md:grid-cols-5 gap-2 max-h-[55vh] overflow-y-auto">
            {floorTables.length === 0 && (
              <div className="col-span-full text-center text-gray-400 py-6 text-sm" data-testid="send-no-tables">
                No floor plan configured. Set one up in Reservations → Floor Plan.
              </div>
            )}
            {floorTables.map(t => (
              <button
                key={t.id}
                disabled={sendingToTable}
                onClick={async () => {
                  setSendingToTable(true);
                  try {
                    const name = selectedCustomer?.name || walkInName || `Table ${t.number}`;
                    await v15API.createTab({
                      name: `Table ${t.number} — ${name}`,
                      cart, selectedCustomer,
                      tableId: t.id,
                      tableNumber: t.number,
                    });
                    toast({ title: `Sent to Table ${t.number}`, description: 'Ready for later payment.' });
                    // Fire kitchen prints so food fires immediately.
                    try {
                      await gamificationAPI.sendToPrinters({
                        items: cart.map(i => ({ productName: i.name, category: i.category, quantity: i.quantity })),
                        orderId: `TABLE-${t.number}`, tableNumber: t.number,
                      });
                    } catch (err) { /* printer optional */ }
                    setSendToTableOpen(false);
                    clearCart();
                  } catch (e) {
                    toast({ title: 'Send failed', description: e?.response?.data?.detail, variant: 'destructive' });
                  } finally { setSendingToTable(false); }
                }}
                className="rounded-lg border-2 p-3 hover:border-current transition-all disabled:opacity-50 disabled:cursor-not-allowed text-left"
                style={{ borderColor: t.status === 'available' ? '#10b981' : '#f59e0b' }}
                data-testid={`send-table-${t.id}`}
              >
                <div className="font-bold text-lg" style={{ color: theme.text }}>#{t.number}</div>
                <div className="text-[10px] text-gray-500 uppercase tracking-wide">{t.section || 'main'}</div>
                <div className="text-[10px] text-gray-400 mt-0.5">seats {t.capacity || t.maxCovers || 2}</div>
                <div className="text-[10px] mt-1 capitalize" style={{ color: t.status === 'available' ? '#10b981' : '#f59e0b' }}>
                  {t.status || 'available'}
                </div>
              </button>
            ))}
          </div>
        </DialogContent>
      </Dialog>

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

      {/* Modifier picker — opens when a product with attached modifierIds is tapped */}
      <ModifierSheet
        product={modifierSheetProduct}
        modifiers={modifiers}
        open={!!modifierSheetProduct}
        onClose={() => setModifierSheetProduct(null)}
        themeColor={theme.primary}
        onConfirm={(selections, extra) => {
          addToCart(modifierSheetProduct, 1, selections, extra);
          toast({ title: 'Added', description: `${modifierSheetProduct.name} with ${selections.length} option${selections.length !== 1 ? 's' : ''}` });
          setModifierSheetProduct(null);
        }}
      />

    </div>
  );
};

export default POSTerminal;
