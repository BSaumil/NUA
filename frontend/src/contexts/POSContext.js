import React, { createContext, useContext, useState } from 'react';
import { products as mockProducts, transactions as mockTransactions, customers as mockCustomers } from '../mockData';

const POSContext = createContext();

export const POSProvider = ({ children }) => {
  const [cart, setCart] = useState([]);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [currentLocation, setCurrentLocation] = useState('Main Street');
  const [currentUser, setCurrentUser] = useState({ name: 'John Doe', role: 'Admin' });
  // Discounts applied to the current cart — both auto promotions and manually
  // selected vouchers live here so calculateTotal can subtract them all.
  const [appliedDiscounts, setAppliedDiscounts] = useState([]);

  const addToCart = (product, quantity = 1) => {
    setCart(prev => {
      const existing = prev.find(item => item.id === product.id);
      if (existing) {
        return prev.map(item =>
          item.id === product.id
            ? { ...item, quantity: item.quantity + quantity }
            : item
        );
      }
      return [...prev, { ...product, quantity }];
    });
  };

  const removeFromCart = (productId) => {
    setCart(prev => prev.filter(item => item.id !== productId));
  };

  const updateQuantity = (productId, quantity) => {
    if (quantity <= 0) {
      removeFromCart(productId);
      return;
    }
    setCart(prev =>
      prev.map(item =>
        item.id === productId ? { ...item, quantity } : item
      )
    );
  };

  const clearCart = () => {
    setCart([]);
    setSelectedCustomer(null);
    setAppliedDiscounts([]);
  };

  const addDiscount = (d) => setAppliedDiscounts(prev => {
    // Replace same id; otherwise append. Auto-applied promos use promotionId,
    // manual vouchers use voucher.id.
    const key = d.promotionId || d.voucherId || d.id;
    const filtered = prev.filter(x => (x.promotionId || x.voucherId || x.id) !== key);
    return [...filtered, d];
  });

  const removeDiscount = (key) => setAppliedDiscounts(prev =>
    prev.filter(x => (x.promotionId || x.voucherId || x.id) !== key)
  );

  const calculateTotal = () => {
    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const discount = appliedDiscounts.reduce((s, d) => s + (Number(d.discount) || 0), 0);
    const afterDiscount = Math.max(0, subtotal - discount);
    const gst = afterDiscount * 0.1;
    return {
      subtotal: subtotal.toFixed(2),
      discount: discount.toFixed(2),
      gst: gst.toFixed(2),
      total: (afterDiscount + gst).toFixed(2),
    };
  };

  return (
    <POSContext.Provider
      value={{
        cart,
        addToCart,
        removeFromCart,
        updateQuantity,
        clearCart,
        calculateTotal,
        selectedCustomer,
        setSelectedCustomer,
        currentLocation,
        setCurrentLocation,
        currentUser,
        setCurrentUser,
        appliedDiscounts,
        addDiscount,
        removeDiscount,
      }}
    >
      {children}
    </POSContext.Provider>
  );
};

export const usePOS = () => {
  const context = useContext(POSContext);
  if (!context) {
    throw new Error('usePOS must be used within POSProvider');
  }
  return context;
};
