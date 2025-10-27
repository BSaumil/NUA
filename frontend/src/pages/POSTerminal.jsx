import React, { useState } from 'react';
import { Search, Plus, Minus, Trash2, User, CreditCard, Banknote, Smartphone, ShoppingCart } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { useTheme } from '../contexts/ThemeContext';
import { usePOS } from '../contexts/POSContext';
import { products, promotions, customers } from '../mockData';
import { useToast } from '../hooks/use-toast';

const POSTerminal = () => {
  const { theme } = useTheme();
  const { cart, addToCart, removeFromCart, updateQuantity, clearCart, calculateTotal, selectedCustomer, setSelectedCustomer } = usePOS();
  const { toast } = useToast();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [showPayment, setShowPayment] = useState(false);

  const categories = ['All', 'Beverages', 'Food', 'Bakery'];
  const filteredProducts = products.filter(p =>
    (selectedCategory === 'All' || p.category === selectedCategory) &&
    p.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const totals = calculateTotal();

  const handleCheckout = (paymentMethod) => {
    toast({
      title: "Transaction Complete!",
      description: `Payment of $${totals.total} received via ${paymentMethod}`,
    });
    clearCart();
    setShowPayment(false);
  };

  return (
    <div className="flex h-screen gap-6">
      {/* Products Grid */}
      <div className="flex-1 flex flex-col">
        {/* Search & Filters */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold mb-4" style={{ color: theme.text }}>POS Terminal</h1>
          <div className="flex gap-3 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
              <Input
                placeholder="Search products..."
                className="pl-10"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
          <div className="flex gap-2">
            {categories.map(cat => (
              <Button
                key={cat}
                variant={selectedCategory === cat ? 'default' : 'outline'}
                onClick={() => setSelectedCategory(cat)}
                style={{
                  backgroundColor: selectedCategory === cat ? theme.primary : 'transparent',
                  color: selectedCategory === cat ? 'white' : theme.text
                }}
              >
                {cat}
              </Button>
            ))}
          </div>
        </div>

        {/* Products Grid */}
        <div className="flex-1 overflow-y-auto">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {filteredProducts.map(product => (
              <Card
                key={product.id}
                className="cursor-pointer hover:shadow-lg transition-all duration-300 hover:scale-105"
                onClick={() => addToCart(product)}
              >
                <CardContent className="p-4">
                  <img
                    src={product.image}
                    alt={product.name}
                    className="w-full h-32 object-cover rounded-lg mb-3"
                  />
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
          <h3 className="font-semibold mb-2" style={{ color: theme.text }}>🎉 Active Promotions</h3>
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
      <div className="w-96 flex flex-col border-l bg-gray-50 p-6">
        <h2 className="text-2xl font-bold mb-4" style={{ color: theme.text }}>Current Order</h2>

        {/* Customer Selection */}
        <Card className="mb-4">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <User size={18} style={{ color: theme.primary }} />
              <span className="font-medium text-sm">Customer</span>
            </div>
            {selectedCustomer ? (
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">{selectedCustomer.name}</p>
                  <p className="text-xs text-gray-500">{selectedCustomer.membershipTier} Member</p>
                </div>
                <Button variant="ghost" size="sm" onClick={() => setSelectedCustomer(null)}>Remove</Button>
              </div>
            ) : (
              <select
                className="w-full p-2 border rounded-md text-sm"
                onChange={(e) => {
                  const customer = customers.find(c => c.id === e.target.value);
                  setSelectedCustomer(customer);
                }}
              >
                <option value="">Walk-in Customer</option>
                {customers.map(c => (
                  <option key={c.id} value={c.id}>{c.name} ({c.membershipTier})</option>
                ))}
              </select>
            )}
          </CardContent>
        </Card>

        {/* Cart Items */}
        <div className="flex-1 overflow-y-auto mb-4">
          {cart.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <ShoppingCart size={48} className="mx-auto mb-3 opacity-50" />
              <p>Cart is empty</p>
              <p className="text-sm">Add products to start</p>
            </div>
          ) : (
            <div className="space-y-3">
              {cart.map(item => (
                <Card key={item.id}>
                  <CardContent className="p-3">
                    <div className="flex items-center gap-3">
                      <img src={item.image} alt={item.name} className="w-12 h-12 object-cover rounded" />
                      <div className="flex-1">
                        <p className="font-medium text-sm">{item.name}</p>
                        <p className="text-xs text-gray-500">${item.price.toFixed(2)} each</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => updateQuantity(item.id, item.quantity - 1)}
                          className="w-8 h-8 p-0"
                        >
                          <Minus size={14} />
                        </Button>
                        <span className="font-medium w-8 text-center">{item.quantity}</span>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => updateQuantity(item.id, item.quantity + 1)}
                          className="w-8 h-8 p-0"
                        >
                          <Plus size={14} />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => removeFromCart(item.id)}
                          className="w-8 h-8 p-0 text-red-500"
                        >
                          <Trash2 size={14} />
                        </Button>
                      </div>
                    </div>
                    <div className="text-right mt-2">
                      <span className="font-bold" style={{ color: theme.primary }}>
                        ${(item.price * item.quantity).toFixed(2)}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Totals */}
        {cart.length > 0 && (
          <Card className="mb-4">
            <CardContent className="p-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span>Subtotal</span>
                <span>${totals.subtotal}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span>GST (10%)</span>
                <span>${totals.gst}</span>
              </div>
              <div className="border-t pt-2 flex justify-between font-bold text-lg">
                <span>Total</span>
                <span style={{ color: theme.primary }}>${totals.total}</span>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Payment Methods */}
        {!showPayment && cart.length > 0 && (
          <Button
            className="w-full h-14 text-lg font-semibold"
            style={{ backgroundColor: theme.primary }}
            onClick={() => setShowPayment(true)}
          >
            Proceed to Payment
          </Button>
        )}

        {showPayment && (
          <div className="space-y-3">
            <Button
              className="w-full h-12"
              variant="outline"
              onClick={() => handleCheckout('Card')}
            >
              <CreditCard className="mr-2" size={20} />
              Card Payment
            </Button>
            <Button
              className="w-full h-12"
              variant="outline"
              onClick={() => handleCheckout('Cash')}
            >
              <Banknote className="mr-2" size={20} />
              Cash Payment
            </Button>
            <Button
              className="w-full h-12"
              variant="outline"
              onClick={() => handleCheckout('Digital Wallet')}
            >
              <Smartphone className="mr-2" size={20} />
              Digital Wallet
            </Button>
            <Button
              className="w-full"
              variant="ghost"
              onClick={() => setShowPayment(false)}
            >
              Cancel
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

export default POSTerminal;
