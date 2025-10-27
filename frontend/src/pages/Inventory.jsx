import React, { useState } from 'react';
import { Package, AlertTriangle, TrendingDown, Search, Filter } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { useTheme } from '../contexts/ThemeContext';
import { products } from '../mockData';

const Inventory = () => {
  const { theme } = useTheme();
  const [searchTerm, setSearchTerm] = useState('');

  const lowStockProducts = products.filter(p => p.stock < 100);
  const totalValue = products.reduce((sum, p) => sum + (p.cost * p.stock), 0);

  const filteredProducts = products.filter(p =>
    p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    p.sku.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold" style={{ color: theme.text }}>Inventory Management</h1>
          <p className="text-gray-500 mt-1">Track stock levels and manage inventory across locations</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline">
            <Filter className="mr-2" size={18} />
            Filter
          </Button>
          <Button style={{ backgroundColor: theme.primary }}>
            <Package className="mr-2" size={18} />
            Stock Adjustment
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">Total Items</p>
              <Package size={20} style={{ color: theme.primary }} />
            </div>
            <p className="text-3xl font-bold" style={{ color: theme.text }}>{products.length}</p>
            <p className="text-xs text-gray-500 mt-1">Active products</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">Inventory Value</p>
              <Package size={20} style={{ color: theme.secondary }} />
            </div>
            <p className="text-3xl font-bold" style={{ color: theme.text }}>${totalValue.toFixed(2)}</p>
            <p className="text-xs text-gray-500 mt-1">At cost price</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">Low Stock Items</p>
              <AlertTriangle size={20} style={{ color: '#f59e0b' }} />
            </div>
            <p className="text-3xl font-bold text-orange-500">{lowStockProducts.length}</p>
            <p className="text-xs text-gray-500 mt-1">Needs reordering</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">Total Units</p>
              <TrendingDown size={20} style={{ color: theme.accent }} />
            </div>
            <p className="text-3xl font-bold" style={{ color: theme.text }}>
              {products.reduce((sum, p) => sum + p.stock, 0)}
            </p>
            <p className="text-xs text-gray-500 mt-1">In stock</p>
          </CardContent>
        </Card>
      </div>

      {/* Low Stock Alert */}
      {lowStockProducts.length > 0 && (
        <Card className="border-orange-300 bg-orange-50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle size={20} className="text-orange-600" />
              <h3 className="font-semibold text-orange-900">Low Stock Alert</h3>
            </div>
            <p className="text-sm text-orange-700">
              {lowStockProducts.length} items are running low. Consider reordering soon.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
        <Input
          placeholder="Search by product name or SKU..."
          className="pl-10"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      {/* Inventory Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left p-4 text-sm font-medium text-gray-500">Product</th>
                  <th className="text-left p-4 text-sm font-medium text-gray-500">SKU</th>
                  <th className="text-left p-4 text-sm font-medium text-gray-500">Category</th>
                  <th className="text-right p-4 text-sm font-medium text-gray-500">Stock</th>
                  <th className="text-right p-4 text-sm font-medium text-gray-500">Cost</th>
                  <th className="text-right p-4 text-sm font-medium text-gray-500">Value</th>
                  <th className="text-center p-4 text-sm font-medium text-gray-500">Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredProducts.map(product => {
                  const stockValue = product.cost * product.stock;
                  const isLowStock = product.stock < 100;

                  return (
                    <tr key={product.id} className="border-t hover:bg-gray-50 transition-colors">
                      <td className="p-4">
                        <div className="flex items-center gap-3">
                          <img
                            src={product.image}
                            alt={product.name}
                            className="w-12 h-12 rounded object-cover"
                          />
                          <span className="font-medium" style={{ color: theme.text }}>
                            {product.name}
                          </span>
                        </div>
                      </td>
                      <td className="p-4">
                        <span className="font-mono text-sm text-gray-600">{product.sku}</span>
                      </td>
                      <td className="p-4 text-sm">{product.category}</td>
                      <td className="p-4 text-right">
                        <span
                          className="font-bold"
                          style={{ color: isLowStock ? '#f59e0b' : theme.text }}
                        >
                          {product.stock}
                        </span>
                      </td>
                      <td className="p-4 text-right text-sm">${product.cost.toFixed(2)}</td>
                      <td className="p-4 text-right font-medium" style={{ color: theme.primary }}>
                        ${stockValue.toFixed(2)}
                      </td>
                      <td className="p-4 text-center">
                        {isLowStock ? (
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                            <AlertTriangle size={12} />
                            Low Stock
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            In Stock
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Inventory;
