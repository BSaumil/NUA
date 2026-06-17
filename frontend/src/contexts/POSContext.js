import React, { createContext, useContext, useState } from 'react';

const POSContext = createContext();

export const POSProvider = ({ children }) => {
  const [cart, setCart] = useState([]);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [currentLocation, setCurrentLocation] = useState('Main Street');
  const [currentUser, setCurrentUser] = useState({ name: 'John Doe', role: 'Admin' });
  // Discounts applied to the current cart — both auto promotions and manually
  // selected vouchers live here so calculateTotal can subtract them all.
  const [appliedDiscounts, setAppliedDiscounts] = useState([]);
  // Gift cards applied as a tender (each: { code, amount, balance, giftCardId }).
  // They reduce the *amount to charge* (not the subtotal) and are settled via
  // /v26/gift-cards/{code}/redeem after the rest of the payment completes.
  const [appliedGiftCards, setAppliedGiftCards] = useState([]);
  // Gift cards being SOLD in this cart (pending_activation → activate after payment).
  const [pendingGiftActivations, setPendingGiftActivations] = useState([]);

  const addToCart = (product, quantity = 1, selectedModifiers = null, extraPrice = 0) => {
    setCart(prev => {
      // Items with modifier selections become their own unique lines (don't merge).
      if (selectedModifiers && selectedModifiers.length > 0) {
        const shortId = (typeof crypto !== 'undefined' && crypto.randomUUID)
          ? crypto.randomUUID().slice(0, 8)
          : Math.random().toString(36).slice(2, 10);
        const lineId = `${product.id}__${shortId}`;
        return [...prev, {
          ...product,
          id: lineId,            // unique per line for React keys + remove/update
          productId: product.id, // original product id for tx api
          quantity,
          selectedModifiers,
          price: (product.price || 0) + (extraPrice || 0),
          basePrice: product.price || 0,
          modifierSurcharge: extraPrice || 0,
        }];
      }
      // No modifiers — merge same product id (legacy behaviour).
      const existing = prev.find(item => item.id === product.id);
      if (existing) {
        return prev.map(item =>
          item.id === product.id ? { ...item, quantity: item.quantity + quantity } : item
        );
      }
      return [...prev, { ...product, quantity, productId: product.id }];
    });
  };

  const removeFromCart = (productId) =>
    setCart(prev => prev.filter(item => item.id !== productId));

  const updateQuantity = (productId, quantity) => {
    if (quantity <= 0) return removeFromCart(productId);
    setCart(prev => prev.map(item => item.id === productId ? { ...item, quantity } : item));
  };

  const clearCart = () => {
    setCart([]);
    setSelectedCustomer(null);
    setAppliedDiscounts([]);
    setAppliedGiftCards([]);
    setPendingGiftActivations([]);
  };

  const addDiscount = (d) => setAppliedDiscounts(prev => {
    const key = d.promotionId || d.voucherId || d.id;
    const filtered = prev.filter(x => (x.promotionId || x.voucherId || x.id) !== key);
    return [...filtered, d];
  });

  const removeDiscount = (key) => setAppliedDiscounts(prev =>
    prev.filter(x => (x.promotionId || x.voucherId || x.id) !== key)
  );

  // ----- Gift card tenders -----
  const addGiftCard = (gc) => setAppliedGiftCards(prev => {
    if (prev.some(x => x.code === gc.code)) return prev;
    return [...prev, gc];
  });
  const removeGiftCard = (code) => setAppliedGiftCards(prev => prev.filter(x => x.code !== code));
  const updateGiftCardAmount = (code, amount) => setAppliedGiftCards(prev =>
    prev.map(x => x.code === code ? { ...x, amount } : x)
  );

  // ----- Pending gift activations (cards being sold in this checkout) -----
  const queueGiftActivation = (card) => setPendingGiftActivations(prev =>
    prev.some(x => x.code === card.code) ? prev : [...prev, card]
  );
  const clearGiftActivations = () => setPendingGiftActivations([]);

  const calculateTotal = () => {
    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const discount = appliedDiscounts.reduce((s, d) => s + (Number(d.discount) || 0), 0);
    const afterDiscount = Math.max(0, subtotal - discount);
    const gst = afterDiscount * 0.1;
    const grossTotal = afterDiscount + gst;
    const giftCardTender = appliedGiftCards.reduce((s, gc) => s + (Number(gc.amount) || 0), 0);
    const balanceDue = Math.max(0, grossTotal - giftCardTender);
    return {
      subtotal: subtotal.toFixed(2),
      discount: discount.toFixed(2),
      gst: gst.toFixed(2),
      total: grossTotal.toFixed(2),
      giftCardTender: giftCardTender.toFixed(2),
      balanceDue: balanceDue.toFixed(2),
    };
  };

  return (
    <POSContext.Provider
      value={{
        cart, addToCart, removeFromCart, updateQuantity, clearCart, calculateTotal,
        selectedCustomer, setSelectedCustomer,
        currentLocation, setCurrentLocation,
        currentUser, setCurrentUser,
        appliedDiscounts, addDiscount, removeDiscount,
        appliedGiftCards, addGiftCard, removeGiftCard, updateGiftCardAmount,
        pendingGiftActivations, queueGiftActivation, clearGiftActivations,
      }}
    >
      {children}
    </POSContext.Provider>
  );
};

export const usePOS = () => {
  const context = useContext(POSContext);
  if (!context) throw new Error('usePOS must be used within POSProvider');
  return context;
};
