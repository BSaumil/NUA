import React, { useState, useEffect } from 'react';
import { Search, Plus, Edit, Trash2, Tag, Package, X, TrendingUp, TrendingDown } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { useTheme } from '../contexts/ThemeContext';
import { productsAPI, promotionsAPI, categoriesAPI, aiPantryAPI } from '../services/api';
import { toast } from 'sonner';

const EMPTY_PRODUCT = { name: '', category: 'Beverages', price: '', cost: '', stock: '', sku: '', image: '', gstRate: 10, locations: ['Main'], onlineChannels: [], seoDescription: '', description: '' };
const EMPTY_PROMO = { name: '', type: 'category', discount: '', schedule: '', active: true, category: '', products: [], startDate: '', endDate: '', activeDays: [], startTime: '', endTime: '' };

const Products = () => {
  const { theme } = useTheme();
  const [searchTerm, setSearchTerm] = useState('');
  const [view, setView] = useState('products');
  const [products, setProducts] = useState([]);
  const [promotions, setPromotions] = useState([]);
  const [insights, setInsights] = useState({});  // {productId: {weeklyUnitsSold, marginPct, ...}}
  const [showProductDialog, setShowProductDialog] = useState(false);
  const [showPromoDialog, setShowPromoDialog] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [editingPromo, setEditingPromo] = useState(null);
  const [productForm, setProductForm] = useState(EMPTY_PRODUCT);
  const [promoForm, setPromoForm] = useState(EMPTY_PROMO);

  useEffect(() => { fetchData(); fetchInsights(); }, []);

  const fetchInsights = async () => {
    try {
      const r = await aiPantryAPI.productInsights();
      const map = {};
      (r.data || []).forEach(i => { map[i.productId] = i; });
      setInsights(map);
    } catch {}
  };

  const fetchData = async () => {
    try {
      const [p, pr] = await Promise.all([productsAPI.getAll(), promotionsAPI.getAll()]);
      setProducts(p.data);
      setPromotions(pr.data);
    } catch { toast.error('Failed to load data'); }
  };

  // === Product CRUD ===
  const openAddProduct = () => { setEditingProduct(null); setProductForm(EMPTY_PRODUCT); setShowProductDialog(true); };
  const openEditProduct = (p) => {
    setEditingProduct(p);
    setProductForm({ name: p.name, category: p.category, price: p.price, cost: p.cost, stock: p.stock, sku: p.sku, image: p.image, gstRate: p.gstRate, locations: p.locations || ['Main'], onlineChannels: p.onlineChannels || [], seoDescription: p.seoDescription || '', description: p.description || '' });
    setShowProductDialog(true);
  };
  const saveProduct = async () => {
    const data = { ...productForm, price: parseFloat(productForm.price), cost: parseFloat(productForm.cost), stock: parseInt(productForm.stock), gstRate: parseFloat(productForm.gstRate) };
    try {
      if (editingProduct) { await productsAPI.update(editingProduct.id, data); toast.success('Product updated'); }
      else { await productsAPI.create(data); toast.success('Product created'); }
      setShowProductDialog(false); fetchData();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed to save product'); }
  };
  const deleteProduct = async (id) => {
    if (!window.confirm('Delete this product?')) return;
    try { await productsAPI.delete(id); toast.success('Product deleted'); fetchData(); } catch { toast.error('Failed to delete'); }
  };

  // === Promotion CRUD ===
  const openAddPromo = () => { setEditingPromo(null); setPromoForm(EMPTY_PROMO); setShowPromoDialog(true); };
  const openEditPromo = (p) => {
    setEditingPromo(p);
    setPromoForm({ name: p.name, type: p.type, discount: p.discount, schedule: p.schedule, active: p.active, category: p.category || '', products: p.products || [], startDate: p.startDate || '', endDate: p.endDate || '', activeDays: p.activeDays || [], startTime: p.startTime || '', endTime: p.endTime || '' });
    setShowPromoDialog(true);
  };
  const savePromo = async () => {
    const data = { ...promoForm, discount: parseFloat(promoForm.discount) };
    try {
      if (editingPromo) { await promotionsAPI.update(editingPromo.id, data); toast.success('Promotion updated'); }
      else { await promotionsAPI.create(data); toast.success('Promotion created'); }
      setShowPromoDialog(false); fetchData();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed to save promotion'); }
  };
  const deletePromo = async (id) => {
    if (!window.confirm('Delete this promotion?')) return;
    try { await promotionsAPI.delete(id); toast.success('Promotion deleted'); fetchData(); } catch { toast.error('Failed to delete'); }
  };

  const filteredProducts = products.filter(p => p.name.toLowerCase().includes(searchTerm.toLowerCase()));

  return (
    <div className="space-y-6" data-testid="products-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold" style={{ color: theme.text }}>Products & Promotions</h1>
          <p className="text-gray-500 mt-1">Manage your catalog, pricing, and special offers</p>
        </div>
        {view === 'products' ? (
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => document.getElementById('csv-import-input').click()} data-testid="csv-import-btn">
              CSV Import
            </Button>
            <input id="csv-import-input" type="file" accept=".csv" className="hidden" onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              const text = await file.text();
              const lines = text.split(/\r?\n/).filter(l => l.trim());
              if (lines.length < 2) return;
              const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
              const rows = lines.slice(1).map(l => {
                const cells = l.split(',');
                const obj = {};
                headers.forEach((h, i) => obj[h] = cells[i]?.trim());
                return obj;
              });
              try {
                const r = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/items/bulk-import`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('nuva_token')}` },
                  body: JSON.stringify({ rows }),
                });
                const d = await r.json();
                alert(`Imported ${d.imported} products`);
                fetchData();
              } catch { alert('Import failed'); }
              e.target.value = '';
            }} />
            <Button style={{ backgroundColor: theme.primary }} onClick={openAddProduct} data-testid="add-product-btn">
              <Plus className="mr-2" size={18} /> Add Product
            </Button>
          </div>
        ) : (
          <Button style={{ backgroundColor: theme.primary }} onClick={openAddPromo} data-testid="add-promo-btn">
            <Plus className="mr-2" size={18} /> Create Promotion
          </Button>
        )}
      </div>

      <div className="flex gap-2">
        <Button variant={view === 'products' ? 'default' : 'outline'} onClick={() => setView('products')}
          style={{ backgroundColor: view === 'products' ? theme.primary : 'transparent', color: view === 'products' ? 'white' : theme.text }}>
          <Package className="mr-2" size={18} /> Products ({products.length})
        </Button>
        <Button variant={view === 'promotions' ? 'default' : 'outline'} onClick={() => setView('promotions')}
          style={{ backgroundColor: view === 'promotions' ? theme.primary : 'transparent', color: view === 'promotions' ? 'white' : theme.text }}>
          <Tag className="mr-2" size={18} /> Promotions ({promotions.length})
        </Button>
      </div>

      {view === 'products' && (
        <>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <Input placeholder="Search products..." className="pl-10" value={searchTerm} onChange={e => setSearchTerm(e.target.value)} data-testid="product-search" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {filteredProducts.map(product => {
              const ins = insights[product.id] || {};
              const sold = ins.weeklyUnitsSold || 0;
              const margin = ins.marginPct || 0;
              // System-color tinting: badges use theme.primary at varying opacity
              const marginTone = margin >= 60 ? 'bg-emerald-100 text-emerald-800 border-emerald-200'
                : margin >= 40 ? 'bg-amber-100 text-amber-800 border-amber-200'
                : 'bg-red-100 text-red-800 border-red-200';
              return (
              <Card key={product.id} className={`hover:shadow-lg transition-shadow ${product.eightySixed ? 'opacity-60' : ''}`} data-testid={`product-card-${product.id}`}>
                <CardContent className="p-4">
                  <div className="relative">
                    <img src={product.image} alt={product.name} className="w-full h-40 object-cover rounded-lg mb-4" />
                    {product.eightySixed && (
                      <span className="absolute top-1 left-1 bg-red-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded">86</span>
                    )}
                    {/* Margin chip — system colour at low opacity */}
                    <span className={`absolute top-1 right-1 text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded border ${marginTone}`}
                      data-testid={`margin-badge-${product.id}`}>
                      {margin.toFixed(0)}% margin
                    </span>
                  </div>
                  <h3 className="font-bold text-lg" style={{ color: theme.text }}>{product.name}</h3>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-sm text-gray-500">{product.category}</span>
                    <span className="text-xs bg-gray-100 px-2 py-1 rounded font-mono">{product.sku}</span>
                  </div>
                  <div className="flex items-center justify-between mt-2">
                    <div>
                      <p className="text-2xl font-bold" style={{ color: theme.primary }}>${Number(product.price).toFixed(2)}</p>
                      <p className="text-xs text-gray-500">Cost: ${Number(product.cost).toFixed(2)}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium">Stock: {product.stock}</p>
                      <p className="text-xs text-gray-500">GST: {product.gstRate}%</p>
                    </div>
                  </div>
                  {/* Weekly sales tile — same accent colour as Theme primary */}
                  <div className="mt-3 flex items-center justify-between px-2.5 py-1.5 rounded-md"
                    style={{ background: `${theme.primary}10`, color: theme.primary }}
                    data-testid={`weekly-sales-${product.id}`}>
                    <span className="text-xs font-medium flex items-center gap-1">
                      {sold > 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />} Past 7 days
                    </span>
                    <span className="font-bold text-sm">
                      {sold} sold · ${Number(ins.weeklyRevenue || 0).toFixed(0)}
                    </span>
                  </div>
                  <div className="flex gap-2 pt-3">
                    <Button variant="outline" size="sm" className="flex-1" onClick={() => openEditProduct(product)} data-testid={`edit-product-${product.id}`}>
                      <Edit size={14} className="mr-1" /> Edit
                    </Button>
                    <Button variant="outline" size="sm" className="text-red-500 hover:bg-red-50" onClick={() => deleteProduct(product.id)} data-testid={`delete-product-${product.id}`}>
                      <Trash2 size={14} />
                    </Button>
                  </div>
                </CardContent>
              </Card>
              );
            })}
            {filteredProducts.length === 0 && <p className="col-span-full text-center text-gray-400 py-12">No products found. Add your first product above.</p>}
          </div>
        </>
      )}

      {view === 'promotions' && (
        <div className="space-y-4">
          {promotions.map(promo => (
            <Card key={promo.id} data-testid={`promo-card-${promo.id}`}>
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-3">
                      <h3 className="text-xl font-bold" style={{ color: theme.text }}>{promo.name}</h3>
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${promo.active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                        {promo.active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div><p className="text-gray-500">Type</p><p className="font-medium capitalize">{promo.type}</p></div>
                      <div><p className="text-gray-500">Discount</p><p className="font-medium" style={{ color: theme.accent }}>{promo.discount}%</p></div>
                      <div><p className="text-gray-500">Schedule</p><p className="font-medium">{promo.schedule}</p></div>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => openEditPromo(promo)} data-testid={`edit-promo-${promo.id}`}><Edit size={14} /></Button>
                    <Button variant="outline" size="sm" className="text-red-500" onClick={() => deletePromo(promo.id)} data-testid={`delete-promo-${promo.id}`}><Trash2 size={14} /></Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
          {promotions.length === 0 && <Card className="border-dashed"><CardContent className="p-12 text-center"><Tag size={40} className="mx-auto mb-3 text-gray-300" /><p className="text-gray-500">No promotions yet</p></CardContent></Card>}
        </div>
      )}

      {/* Product Dialog */}
      <Dialog open={showProductDialog} onOpenChange={setShowProductDialog}>
        <DialogContent className="max-w-md" data-testid="product-dialog">
          <DialogHeader><DialogTitle>{editingProduct ? 'Edit Product' : 'Add Product'}</DialogTitle></DialogHeader>
          <div className="space-y-3 py-2 max-h-[60vh] overflow-y-auto">
            <Input placeholder="Product name" value={productForm.name} onChange={e => setProductForm({ ...productForm, name: e.target.value })} data-testid="product-name-input" />
            <select className="w-full p-2 border rounded-md text-sm" value={productForm.category} onChange={e => setProductForm({ ...productForm, category: e.target.value })} data-testid="product-category-select">
              <option value="Beverages">Beverages</option><option value="Food">Food</option><option value="Bakery">Bakery</option><option value="Alcohol">Alcohol</option><option value="Other">Other</option>
            </select>
            <div className="grid grid-cols-2 gap-2">
              <Input type="number" step="0.01" placeholder="Price" value={productForm.price} onChange={e => setProductForm({ ...productForm, price: e.target.value })} data-testid="product-price-input" />
              <Input type="number" step="0.01" placeholder="Cost" value={productForm.cost} onChange={e => setProductForm({ ...productForm, cost: e.target.value })} data-testid="product-cost-input" />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Input type="number" placeholder="Stock" value={productForm.stock} onChange={e => setProductForm({ ...productForm, stock: e.target.value })} data-testid="product-stock-input" />
              <Input placeholder="SKU" value={productForm.sku} onChange={e => setProductForm({ ...productForm, sku: e.target.value })} data-testid="product-sku-input" />
            </div>
            <Input placeholder="Image URL" value={productForm.image} onChange={e => setProductForm({ ...productForm, image: e.target.value })} data-testid="product-image-input" />
            <Input type="number" step="0.1" placeholder="GST Rate %" value={productForm.gstRate} onChange={e => setProductForm({ ...productForm, gstRate: e.target.value })} />
            <textarea className="w-full min-h-[60px] p-2 border rounded-md text-sm resize-none" placeholder="Item description..." value={productForm.description} onChange={e => setProductForm({ ...productForm, description: e.target.value })} data-testid="product-desc" />
            <textarea className="w-full min-h-[40px] p-2 border rounded-md text-sm resize-none" placeholder="SEO description (for online channels)..." value={productForm.seoDescription} onChange={e => setProductForm({ ...productForm, seoDescription: e.target.value })} data-testid="product-seo" />
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Locations</label>
              <Input placeholder="Comma-separated: Main, Branch 1" value={(productForm.locations || []).join(', ')} onChange={e => setProductForm({ ...productForm, locations: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })} data-testid="product-locations" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Online Channels</label>
              <div className="flex flex-wrap gap-1.5">
                {['Website', 'Uber Eats', 'DoorDash', 'Menulog', 'Deliveroo', 'Google Food'].map(ch => (
                  <button key={ch} type="button" onClick={() => {
                    const chs = (productForm.onlineChannels || []).includes(ch) ? productForm.onlineChannels.filter(c => c !== ch) : [...(productForm.onlineChannels || []), ch];
                    setProductForm({ ...productForm, onlineChannels: chs });
                  }} className={`px-2 py-1 text-xs rounded-full font-medium ${(productForm.onlineChannels || []).includes(ch) ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                    {ch}
                  </button>
                ))}
              </div>
            </div>
            <Button className="w-full" style={{ backgroundColor: theme.primary }} onClick={saveProduct} data-testid="save-product-btn">
              {editingProduct ? 'Update Product' : 'Create Product'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Promotion Dialog */}
      <Dialog open={showPromoDialog} onOpenChange={setShowPromoDialog}>
        <DialogContent className="max-w-md" data-testid="promo-dialog">
          <DialogHeader><DialogTitle>{editingPromo ? 'Edit Promotion' : 'Create Promotion'}</DialogTitle></DialogHeader>
          <div className="space-y-3 py-2 max-h-[65vh] overflow-y-auto">
            <Input placeholder="Promotion name" value={promoForm.name} onChange={e => setPromoForm({ ...promoForm, name: e.target.value })} data-testid="promo-name-input" />
            <select className="w-full p-2 border rounded-md text-sm" value={promoForm.type} onChange={e => setPromoForm({ ...promoForm, type: e.target.value })}>
              <option value="category">Category Discount</option><option value="bundle">Bundle Deal</option>
            </select>
            <Input type="number" step="0.1" placeholder="Discount %" value={promoForm.discount} onChange={e => setPromoForm({ ...promoForm, discount: e.target.value })} data-testid="promo-discount-input" />

            {/* Date Range */}
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Date Range (optional — leave blank for always)</label>
              <div className="grid grid-cols-2 gap-2">
                <Input type="date" placeholder="Start date" value={promoForm.startDate} onChange={e => setPromoForm({ ...promoForm, startDate: e.target.value })} data-testid="promo-start-date" />
                <Input type="date" placeholder="End date" value={promoForm.endDate} onChange={e => setPromoForm({ ...promoForm, endDate: e.target.value })} data-testid="promo-end-date" />
              </div>
            </div>

            {/* Active Days */}
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Active Days (select none for everyday)</label>
              <div className="flex flex-wrap gap-1.5">
                {['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'].map(day => (
                  <button key={day} type="button" onClick={() => {
                    const days = promoForm.activeDays.includes(day) ? promoForm.activeDays.filter(d => d !== day) : [...promoForm.activeDays, day];
                    setPromoForm({ ...promoForm, activeDays: days });
                  }} className={`px-2.5 py-1 text-xs rounded-full font-medium transition-colors ${promoForm.activeDays.includes(day) ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
                    data-testid={`promo-day-${day.toLowerCase()}`}>
                    {day.slice(0, 3)}
                  </button>
                ))}
              </div>
            </div>

            {/* Time Window */}
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Time Window (optional)</label>
              <div className="grid grid-cols-2 gap-2">
                <Input type="time" value={promoForm.startTime} onChange={e => setPromoForm({ ...promoForm, startTime: e.target.value })} data-testid="promo-start-time" />
                <Input type="time" value={promoForm.endTime} onChange={e => setPromoForm({ ...promoForm, endTime: e.target.value })} data-testid="promo-end-time" />
              </div>
            </div>

            <Input placeholder="Schedule note (e.g. Happy Hour)" value={promoForm.schedule} onChange={e => setPromoForm({ ...promoForm, schedule: e.target.value })} data-testid="promo-schedule-input" />
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={promoForm.active} onChange={e => setPromoForm({ ...promoForm, active: e.target.checked })} /> Active
            </label>
            <Button className="w-full" style={{ backgroundColor: theme.primary }} onClick={savePromo} data-testid="save-promo-btn">
              {editingPromo ? 'Update Promotion' : 'Create Promotion'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Products;
