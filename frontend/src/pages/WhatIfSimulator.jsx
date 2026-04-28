import React, { useState, useEffect } from 'react';
import {
  FlaskConical, DollarSign, TrendingUp, TrendingDown, ArrowRight, Plus, X, BarChart3
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import { useTheme } from '../contexts/ThemeContext';
import { simulatorAPI } from '../services/api';
import api from '../services/api';
import { toast } from 'sonner';

export default function WhatIfSimulator() {
  const { theme } = useTheme();
  const [products, setProducts] = useState([]);
  const [changes, setChanges] = useState([]);
  const [results, setResults] = useState(null);
  const [selectedProduct, setSelectedProduct] = useState('');

  useEffect(() => {
    api.get('/products').then(r => setProducts(r.data)).catch(console.error);
  }, []);

  const addChange = () => {
    if (!selectedProduct) return;
    const prod = products.find(p => p.id === selectedProduct);
    if (!prod || changes.find(c => c.productId === selectedProduct)) return;
    setChanges([...changes, {
      productId: prod.id,
      productName: prod.name,
      currentPrice: prod.price,
      currentCost: prod.cost || 0,
      newPrice: prod.price,
      newCost: prod.cost || 0,
    }]);
    setSelectedProduct('');
  };

  const removeChange = (idx) => setChanges(changes.filter((_, i) => i !== idx));
  const updateChange = (idx, field, value) => {
    const updated = [...changes];
    updated[idx] = { ...updated[idx], [field]: parseFloat(value) || 0 };
    setChanges(updated);
  };

  const runSimulation = async () => {
    if (changes.length === 0) { toast.error('Add at least one product to simulate'); return; }
    try {
      const payload = { changes: changes.map(c => ({ productId: c.productId, newPrice: c.newPrice, newCost: c.newCost, projectedQty: c.projectedQty })) };
      const res = await api.post('/analytics/what-if-advanced', payload);
      setResults(res.data);
      toast.success('Simulation complete');
    } catch (e) { toast.error('Simulation failed'); }
  };

  return (
    <div className="space-y-6" data-testid="what-if-page">
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #8B5CF6, #EC4899)' }}>
          <FlaskConical size={24} className="text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold" style={{ color: theme.text }}>What-If Simulator</h1>
          <p className="text-sm text-gray-500">Simulate price & cost changes to project profit impact</p>
        </div>
      </div>

      {/* Add products to simulate */}
      <Card className="border-0 shadow-sm">
        <CardHeader className="pb-2"><CardTitle className="text-sm">Configure Changes</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Select value={selectedProduct} onValueChange={setSelectedProduct}>
              <SelectTrigger className="flex-1" data-testid="sim-product-select"><SelectValue placeholder="Select a product to simulate..." /></SelectTrigger>
              <SelectContent>
                {products.filter(p => !changes.find(c => c.productId === p.id)).map(p => (
                  <SelectItem key={p.id} value={p.id}>{p.name} (${p.price})</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={addChange} data-testid="add-sim-product"><Plus size={14} /></Button>
          </div>

          {changes.length > 0 && (
            <div className="space-y-2">
              <div className="grid grid-cols-7 gap-2 text-[10px] font-medium text-gray-500 px-2">
                <span className="col-span-2">Product</span>
                <span className="text-center">Current Price</span>
                <span className="text-center">New Price</span>
                <span className="text-center">New Cost</span>
                <span className="text-center">Qty/Month</span>
                <span></span>
              </div>
              {changes.map((c, idx) => (
                <div key={idx} className="grid grid-cols-7 gap-2 items-center bg-gray-50 rounded-lg p-2" data-testid={`sim-row-${idx}`}>
                  <span className="col-span-2 text-sm font-medium truncate">{c.productName}</span>
                  <span className="text-center text-sm text-gray-500">${c.currentPrice.toFixed(2)}</span>
                  <div className="flex items-center">
                    <span className="text-xs text-gray-400 mr-1">$</span>
                    <Input type="number" step="0.5" className="h-8 text-sm text-center" value={c.newPrice}
                      onChange={e => updateChange(idx, 'newPrice', e.target.value)} data-testid={`new-price-${idx}`} />
                  </div>
                  <div className="flex items-center">
                    <span className="text-xs text-gray-400 mr-1">$</span>
                    <Input type="number" step="0.1" className="h-8 text-sm text-center" value={c.newCost}
                      onChange={e => updateChange(idx, 'newCost', e.target.value)} data-testid={`new-cost-${idx}`} />
                  </div>
                  <div className="flex items-center">
                    <Input type="number" placeholder="Auto" className="h-8 text-sm text-center" value={c.projectedQty || ''}
                      onChange={e => updateChange(idx, 'projectedQty', e.target.value)} data-testid={`projected-qty-${idx}`} />
                  </div>
                  <Button variant="ghost" size="sm" className="h-8 px-2 text-red-400" onClick={() => removeChange(idx)}>
                    <X size={14} />
                  </Button>
                </div>
              ))}
            </div>
          )}

          <Button onClick={runSimulation} style={{ background: theme.primary }} className="w-full" data-testid="run-simulation-btn">
            <FlaskConical size={14} className="mr-2" /> Run Simulation
          </Button>
        </CardContent>
      </Card>

      {/* Results */}
      {results && results.summary && (
        <>
          {/* Summary */}
          <div className="grid grid-cols-3 gap-4">
            <Card className="border-0 shadow-sm">
              <CardContent className="p-4">
                <p className="text-xs text-gray-500">Current Profit</p>
                <p className="text-2xl font-bold" style={{ color: theme.text }}>${(results.summary.currentProfit || 0).toFixed(0)}</p>
              </CardContent>
            </Card>
            <Card className="border-0 shadow-sm">
              <CardContent className="p-4">
                <p className="text-xs text-gray-500">Projected Profit</p>
                <p className="text-2xl font-bold" style={{ color: theme.primary }}>${(results.summary.projectedProfit || 0).toFixed(0)}</p>
              </CardContent>
            </Card>
            <Card className="border-0 shadow-sm" style={{ background: (results.summary.profitChange || 0) >= 0 ? '#ECFDF5' : '#FEF2F2' }}>
              <CardContent className="p-4">
                <p className="text-xs text-gray-500">Net Impact</p>
                <div className="flex items-center gap-2">
                  {(results.summary.profitChange || 0) >= 0 ? <TrendingUp size={20} className="text-green-600" /> : <TrendingDown size={20} className="text-red-600" />}
                  <p className="text-2xl font-bold" style={{ color: (results.summary.profitChange || 0) >= 0 ? '#10B981' : '#EF4444' }}>
                    {(results.summary.profitChange || 0) >= 0 ? '+' : ''}${(results.summary.profitChange || 0).toFixed(0)}
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Detailed Results */}
          {results.items && results.items.length > 0 && (
          <Card className="border-0 shadow-sm">
            <CardHeader className="pb-2"><CardTitle className="text-sm">Simulation Results</CardTitle></CardHeader>
            <CardContent>
              <table className="w-full text-sm" data-testid="sim-results-table">
                <thead>
                  <tr className="border-b bg-gray-50/80">
                    <th className="text-left px-4 py-2 font-medium text-gray-500">Product</th>
                    <th className="text-right px-4 py-2 font-medium text-gray-500">Price</th>
                    <th className="text-right px-4 py-2 font-medium text-gray-500">Qty</th>
                    <th className="text-right px-4 py-2 font-medium text-gray-500">Current Profit</th>
                    <th className="text-right px-4 py-2 font-medium text-gray-500">Projected Profit</th>
                    <th className="text-right px-4 py-2 font-medium text-gray-500">Impact</th>
                  </tr>
                </thead>
                <tbody>
                  {results.items.map((sim, i) => (
                    <tr key={i} className="border-b hover:bg-gray-50/50">
                      <td className="px-4 py-2 font-medium">{sim.productName}</td>
                      <td className="px-4 py-2 text-right">
                        <span className="text-gray-400">${sim.currentPrice}</span>
                        <ArrowRight size={10} className="inline mx-1 text-gray-300" />
                        <span className="font-bold">${sim.newPrice}</span>
                      </td>
                      <td className="px-4 py-2 text-right">
                        <span>{sim.projectedQty}</span>
                      </td>
                      <td className="px-4 py-2 text-right font-mono">${(sim.currentProfit || 0).toFixed(0)}</td>
                      <td className="px-4 py-2 text-right font-mono font-bold">${(sim.projectedProfit || 0).toFixed(0)}</td>
                      <td className="px-4 py-2 text-right">
                        <Badge style={{
                          background: (sim.profitChange || 0) >= 0 ? '#ECFDF5' : '#FEF2F2',
                          color: (sim.profitChange || 0) >= 0 ? '#10B981' : '#EF4444'
                        }}>
                          {(sim.profitChange || 0) >= 0 ? '+' : ''}${(sim.profitChange || 0).toFixed(0)}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
          )}
        </>
      )}
    </div>
  );
}
