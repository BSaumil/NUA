import React, { useState, useEffect } from 'react';
import { Search, Plus, Edit, Trash2, Tag, Package } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { useTheme } from '../contexts/ThemeContext';
import { productsAPI, promotionsAPI } from '../services/api';

const Products = () => {
  const { theme } = useTheme();
  const [searchTerm, setSearchTerm] = useState('');
  const [view, setView] = useState('products'); // 'products' or 'promotions'

  const filteredProducts = products.filter(p =>
    p.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold" style={{ color: theme.text }}>Products & Promotions</h1>
          <p className="text-gray-500 mt-1">Manage your catalog, pricing, and special offers</p>
        </div>
        <Button style={{ backgroundColor: theme.primary }}>
          <Plus className="mr-2" size={18} />
          Add Product
        </Button>
      </div>

      {/* View Tabs */}
      <div className="flex gap-2">
        <Button
          variant={view === 'products' ? 'default' : 'outline'}
          onClick={() => setView('products')}
          style={{
            backgroundColor: view === 'products' ? theme.primary : 'transparent',
            color: view === 'products' ? 'white' : theme.text
          }}
        >
          <Package className="mr-2" size={18} />
          Products
        </Button>
        <Button
          variant={view === 'promotions' ? 'default' : 'outline'}
          onClick={() => setView('promotions')}
          style={{
            backgroundColor: view === 'promotions' ? theme.primary : 'transparent',
            color: view === 'promotions' ? 'white' : theme.text
          }}
        >
          <Tag className="mr-2" size={18} />
          Promotions
        </Button>
      </div>

      {/* Products View */}
      {view === 'products' && (
        <>
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <Input
              placeholder="Search products by name or SKU..."
              className="pl-10"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          {/* Products Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {filteredProducts.map(product => (
              <Card key={product.id} className="hover:shadow-lg transition-shadow duration-300">
                <CardContent className="p-4">
                  <img
                    src={product.image}
                    alt={product.name}
                    className="w-full h-40 object-cover rounded-lg mb-4"
                  />
                  <div className="space-y-2">
                    <h3 className="font-bold text-lg" style={{ color: theme.text }}>{product.name}</h3>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-500">{product.category}</span>
                      <span className="text-xs bg-gray-100 px-2 py-1 rounded">{product.sku}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-2xl font-bold" style={{ color: theme.primary }}>${product.price}</p>
                        <p className="text-xs text-gray-500">Cost: ${product.cost}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-medium">Stock: {product.stock}</p>
                        <p className="text-xs text-gray-500">GST: {product.gstRate}%</p>
                      </div>
                    </div>
                    <div className="flex gap-2 pt-2">
                      <Button variant="outline" size="sm" className="flex-1">
                        <Edit size={14} className="mr-1" />
                        Edit
                      </Button>
                      <Button variant="outline" size="sm" className="text-red-500">
                        <Trash2 size={14} />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      )}

      {/* Promotions View */}
      {view === 'promotions' && (
        <div className="space-y-4">
          <Button style={{ backgroundColor: theme.primary }} className="mb-4">
            <Plus className="mr-2" size={18} />
            Create Promotion
          </Button>

          {promotions.map(promo => (
            <Card key={promo.id}>
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-3">
                      <h3 className="text-xl font-bold" style={{ color: theme.text }}>{promo.name}</h3>
                      <span
                        className="px-3 py-1 rounded-full text-xs font-medium"
                        style={{
                          backgroundColor: promo.active ? '#dcfce7' : '#fee2e2',
                          color: promo.active ? '#15803d' : '#991b1b'
                        }}
                      >
                        {promo.active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <p className="text-gray-500">Type</p>
                        <p className="font-medium capitalize">{promo.type}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Discount</p>
                        <p className="font-medium" style={{ color: theme.accent }}>{promo.discount}%</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Schedule</p>
                        <p className="font-medium">{promo.schedule}</p>
                      </div>
                    </div>
                    {promo.type === 'bundle' && (
                      <div className="mt-3">
                        <p className="text-sm text-gray-500">Bundle Items:</p>
                        <p className="font-medium">
                          {promo.products.map(pid => products.find(p => p.id === pid)?.name).join(' + ')}
                        </p>
                        <p className="text-sm mt-1">
                          <span className="line-through text-gray-400">${promo.originalPrice}</span>
                          <span className="ml-2 font-bold" style={{ color: theme.primary }}>${promo.discountedPrice}</span>
                        </p>
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm">
                      <Edit size={14} />
                    </Button>
                    <Button variant="outline" size="sm" className="text-red-500">
                      <Trash2 size={14} />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default Products;
