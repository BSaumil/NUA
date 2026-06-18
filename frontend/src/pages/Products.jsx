import React, { useState, useEffect, useMemo } from 'react';
import { Search, Plus, Edit, Trash2, Tag, Package, X, TrendingUp, TrendingDown, CheckSquare, Square, ImageIcon, Download, ChevronDown, Ban, ArrowUpDown, Filter as FilterIcon, ChevronUp } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { useTheme } from '../contexts/ThemeContext';
import { productsAPI, promotionsAPI, categoriesAPI, modifiersAPI, aiPantryAPI, productsBulkAPI } from '../services/api';
import ImageLibrary from '../components/ImageLibrary';
import { toast } from 'sonner';

const makeEmptyProduct = () => ({
  name: '', category: '', categoryId: '', price: '', cost: '', stock: '', sku: '',
  image: '', gstRate: 10, locations: ['Main'], onlineChannels: [],
  seoDescription: '', description: '', modifierIds: [],
});
const makeEmptyPromo = () => ({
  name: '', type: 'category', discount: '', schedule: '', active: true,
  category: '', products: [], startDate: '', endDate: '',
  activeDays: [], startTime: '', endTime: '',
});

const Products = () => {
  const { theme } = useTheme();
  const [searchTerm, setSearchTerm] = useState('');
  const [view, setView] = useState('products');
  const [products, setProducts] = useState([]);
  const [promotions, setPromotions] = useState([]);
  const [categories, setCategories] = useState([]);
  const [modifiers, setModifiers] = useState([]);
  const [insights, setInsights] = useState({});  // {productId: {weeklyUnitsSold, marginPct, ...}}
  const [showProductDialog, setShowProductDialog] = useState(false);
  const [showPromoDialog, setShowPromoDialog] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [editingPromo, setEditingPromo] = useState(null);
  const [productForm, setProductForm] = useState(makeEmptyProduct);
  const [promoForm, setPromoForm] = useState(makeEmptyPromo);

  // -------- NEW: filter / sort / bulk / library state --------
  const [filterCats, setFilterCats] = useState([]);     // [] = all
  const [filterStatus, setFilterStatus] = useState('all'); // all | active | 86
  const [sortKey, setSortKey] = useState('name');       // name | price | stock | margin | recent
  const [sortDir, setSortDir] = useState('asc');        // asc | desc
  const [selected, setSelected] = useState(new Set());  // selected productIds
  const [bulkOpen, setBulkOpen] = useState(false);
  const [layoutMode, setLayoutMode] = useState('grid'); // grid | table
  const [imageLibraryOpen, setImageLibraryOpen] = useState(false);
  const [bulkImageLibraryOpen, setBulkImageLibraryOpen] = useState(false);
  const [bulkPatch, setBulkPatch] = useState({
    categoryId: '', pricePercentDelta: '', cost: '', gstRate: '', image: '',
    eightySixed: '', // '' | 'true' | 'false'
    addModifierIds: [], removeModifierIds: [],
  });
  const [inlineEditCell, setInlineEditCell] = useState(null); // {id, field}
  const [inlineValue, setInlineValue] = useState('');

  useEffect(() => { fetchData(); fetchInsights(); }, []);

  const fetchInsights = async () => {
    try {
      const r = await aiPantryAPI.productInsights();
      const map = {};
      (r.data || []).forEach(i => { map[i.productId] = i; });
      setInsights(map);
    } catch { /* ignore: insights are optional */ }
  };

  const fetchData = async () => {
    try {
      const [productsRes, promotionsRes, categoriesRes, modifiersRes] = await Promise.all([
        productsAPI.getAll(),
        promotionsAPI.getAll(),
        categoriesAPI.getAll(),
        modifiersAPI.getAll(),
      ]);
      setProducts(productsRes.data);
      setPromotions(promotionsRes.data);
      const activeCats = (categoriesRes.data || []).filter(c => c.active !== false);
      const sortedCats = Array.from(activeCats).sort((a, b) => (a.sortOrder || 0) - (b.sortOrder || 0));
      setCategories(sortedCats);
      setModifiers(modifiersRes.data || []);
    } catch { toast.error('Failed to load data'); }
  };

  // === Product CRUD ===
  function openAddProduct() {
    const firstCat = categories[0];
    setEditingProduct(null);
    setProductForm({
      name: '', category: firstCat?.name || '', categoryId: firstCat?.id || '',
      price: '', cost: '', stock: '', sku: '', image: '', gstRate: 10,
      locations: ['Main'], onlineChannels: [], seoDescription: '', description: '',
      modifierIds: [],
    });
    setShowProductDialog(true);
  }
  const openEditProduct = (p) => {
    setEditingProduct(p);
    setProductForm({
      name: p.name, category: p.category, categoryId: p.categoryId || '',
      price: p.price, cost: p.cost, stock: p.stock, sku: p.sku, image: p.image,
      gstRate: p.gstRate, locations: p.locations || ['Main'], onlineChannels: p.onlineChannels || [],
      seoDescription: p.seoDescription || '', description: p.description || '',
      modifierIds: p.modifierIds || [],
    });
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

  const toggleModifierForProduct = (mid) => {
    const arr = productForm.modifierIds || [];
    setProductForm({
      ...productForm,
      modifierIds: arr.includes(mid) ? arr.filter(x => x !== mid) : [...arr, mid],
    });
  };

  const handleCategoryChange = (catId) => {
    const c = categories.find(x => x.id === catId);
    setProductForm({ ...productForm, categoryId: catId, category: c?.name || '' });
  };

  // === Promotion CRUD ===
  const openAddPromo = () => { setEditingPromo(null); setPromoForm(makeEmptyPromo()); setShowPromoDialog(true); };
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

  const filteredProducts = useMemo(() => {
    const term = searchTerm.toLowerCase();
    let list = products.filter(p => {
      // text search: name OR sku
      if (term && !(p.name?.toLowerCase().includes(term) || p.sku?.toLowerCase().includes(term))) return false;
      // category filter (multi)
      if (filterCats.length > 0) {
        const matchById = p.categoryId && filterCats.includes(p.categoryId);
        const matchByName = !p.categoryId && filterCats.some(fc => {
          const c = categories.find(x => x.id === fc);
          return c && c.name === p.category;
        });
        if (!matchById && !matchByName) return false;
      }
      // status
      if (filterStatus === 'active' && p.eightySixed) return false;
      if (filterStatus === '86' && !p.eightySixed) return false;
      return true;
    });
    // sort
    const dir = sortDir === 'asc' ? 1 : -1;
    list = [...list].sort((a, b) => {
      let av, bv;
      if (sortKey === 'name') { av = (a.name || '').toLowerCase(); bv = (b.name || '').toLowerCase(); }
      else if (sortKey === 'price') { av = Number(a.price || 0); bv = Number(b.price || 0); }
      else if (sortKey === 'stock') { av = Number(a.stock || 0); bv = Number(b.stock || 0); }
      else if (sortKey === 'margin') {
        const am = insights[a.id]?.marginPct ?? (a.price && a.cost ? ((a.price - a.cost) / a.price * 100) : 0);
        const bm = insights[b.id]?.marginPct ?? (b.price && b.cost ? ((b.price - b.cost) / b.price * 100) : 0);
        av = am; bv = bm;
      } else if (sortKey === 'recent') {
        av = a.updatedAt || a.createdAt || ''; bv = b.updatedAt || b.createdAt || '';
      } else if (sortKey === 'category') {
        av = (a.category || ''); bv = (b.category || '');
      }
      if (av < bv) return -1 * dir;
      if (av > bv) return 1 * dir;
      return 0;
    });
    return list;
  }, [products, searchTerm, filterCats, filterStatus, sortKey, sortDir, insights, categories]);

  // -------- Bulk + inline operations --------
  const toggleSelect = (id) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };
  const selectAllVisible = () => {
    setSelected(new Set(filteredProducts.map(p => p.id)));
  };
  const clearSelection = () => setSelected(new Set());
  const allVisibleSelected = filteredProducts.length > 0 && filteredProducts.every(p => selected.has(p.id));

  const applyBulk = async () => {
    if (selected.size === 0) return toast.error('Pick at least one product');
    const payload = { productIds: Array.from(selected) };
    if (bulkPatch.categoryId) {
      const c = categories.find(x => x.id === bulkPatch.categoryId);
      payload.categoryId = bulkPatch.categoryId;
      payload.category = c?.name || undefined;
    }
    if (bulkPatch.pricePercentDelta !== '' && !isNaN(parseFloat(bulkPatch.pricePercentDelta))) {
      payload.pricePercentDelta = parseFloat(bulkPatch.pricePercentDelta);
    }
    if (bulkPatch.cost !== '' && !isNaN(parseFloat(bulkPatch.cost))) payload.cost = parseFloat(bulkPatch.cost);
    if (bulkPatch.gstRate !== '' && !isNaN(parseFloat(bulkPatch.gstRate))) payload.gstRate = parseFloat(bulkPatch.gstRate);
    if (bulkPatch.image) payload.image = bulkPatch.image;
    if (bulkPatch.eightySixed === 'true') payload.eightySixed = true;
    if (bulkPatch.eightySixed === 'false') payload.eightySixed = false;
    if (bulkPatch.addModifierIds.length > 0) payload.addModifierIds = bulkPatch.addModifierIds;
    if (bulkPatch.removeModifierIds.length > 0) payload.removeModifierIds = bulkPatch.removeModifierIds;

    try {
      const r = await productsBulkAPI.bulkEdit(payload);
      toast.success(`Updated ${r.data?.updated || 0} products`);
      setBulkOpen(false);
      setBulkPatch({ categoryId: '', pricePercentDelta: '', cost: '', gstRate: '', image: '', eightySixed: '', addModifierIds: [], removeModifierIds: [] });
      clearSelection();
      fetchData();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Bulk update failed');
    }
  };

  const bulkDelete = async () => {
    if (selected.size === 0) return;
    if (!window.confirm(`Delete ${selected.size} products? This cannot be undone.`)) return;
    let ok = 0, fail = 0;
    for (const id of selected) {
      try { await productsAPI.delete(id); ok++; } catch { fail++; }
    }
    toast.success(`Deleted ${ok}${fail > 0 ? ` · ${fail} failed` : ''}`);
    clearSelection(); fetchData();
  };

  const toggleEightySix = async (p) => {
    try {
      await productsBulkAPI.bulkEdit({ productIds: [p.id], eightySixed: !p.eightySixed });
      toast.success(p.eightySixed ? 'Un-86\'d' : 'Marked as 86 (out of stock)');
      fetchData();
    } catch { toast.error('Failed'); }
  };

  const startInlineEdit = (id, field, currentValue) => {
    setInlineEditCell({ id, field });
    setInlineValue(currentValue?.toString() ?? '');
  };
  const commitInlineEdit = async () => {
    if (!inlineEditCell) return;
    const { id, field } = inlineEditCell;
    let value = inlineValue;
    if (field === 'price' || field === 'cost') value = parseFloat(value) || 0;
    if (field === 'stock') value = parseInt(value, 10) || 0;
    try {
      await productsAPI.update(id, { [field]: value });
      toast.success(`${field} updated`);
      fetchData();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Failed'); }
    setInlineEditCell(null);
  };

  const exportCsv = () => {
    const headers = ['id', 'name', 'sku', 'category', 'price', 'cost', 'stock', 'gstRate', 'eightySixed', 'modifiersCount'];
    const rows = filteredProducts.map(p => [
      p.id, p.name, p.sku, p.category, p.price, p.cost, p.stock, p.gstRate,
      p.eightySixed ? 'Y' : 'N', (p.modifierIds || []).length,
    ]);
    const escape = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
    const csv = [headers.join(','), ...rows.map(r => r.map(escape).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `products-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click(); URL.revokeObjectURL(url);
  };

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
          {/* Filter + sort + bulk toolbar */}
          <div className="bg-white rounded-lg border p-3 space-y-3" data-testid="products-toolbar">
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative flex-1 min-w-[200px]">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={16} />
                <Input placeholder="Search by name or SKU..." className="pl-9 h-9" value={searchTerm} onChange={e => setSearchTerm(e.target.value)} data-testid="product-search" />
              </div>
              {/* Sort */}
              <div className="flex items-center gap-1 text-xs">
                <ArrowUpDown size={14} className="text-gray-400" />
                <select className="border rounded p-1.5 text-xs" value={sortKey} onChange={e => setSortKey(e.target.value)} data-testid="sort-key-select">
                  <option value="name">Name</option>
                  <option value="category">Category</option>
                  <option value="price">Price</option>
                  <option value="stock">Stock</option>
                  <option value="margin">Margin</option>
                  <option value="recent">Recently edited</option>
                </select>
                <button onClick={() => setSortDir(sortDir === 'asc' ? 'desc' : 'asc')} className="border rounded p-1.5 hover:bg-gray-50" data-testid="sort-dir-toggle" title="Toggle direction">
                  {sortDir === 'asc' ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                </button>
              </div>
              {/* Status filter */}
              <select className="border rounded p-1.5 text-xs" value={filterStatus} onChange={e => setFilterStatus(e.target.value)} data-testid="filter-status-select">
                <option value="all">All status</option>
                <option value="active">Active only</option>
                <option value="86">Only 86’d</option>
              </select>
              {/* Layout toggle */}
              <div className="flex items-center border rounded overflow-hidden text-xs">
                <button onClick={() => setLayoutMode('grid')} className={`px-2 py-1 ${layoutMode === 'grid' ? 'text-white' : 'text-gray-500'}`} style={layoutMode === 'grid' ? { background: theme.primary } : {}} data-testid="view-grid">Grid</button>
                <button onClick={() => setLayoutMode('table')} className={`px-2 py-1 ${layoutMode === 'table' ? 'text-white' : 'text-gray-500'}`} style={layoutMode === 'table' ? { background: theme.primary } : {}} data-testid="view-table">Table</button>
              </div>
              <Button variant="outline" size="sm" onClick={exportCsv} className="h-9" data-testid="export-csv-btn">
                <Download size={14} className="mr-1.5" /> CSV
              </Button>
            </div>
            {/* Category chips */}
            <div className="flex items-center gap-1.5 flex-wrap" data-testid="category-filter-chips">
              <FilterIcon size={12} className="text-gray-400" />
              <span className="text-[10px] uppercase tracking-widest text-gray-400">Category</span>
              <button
                onClick={() => setFilterCats([])}
                className={`px-2.5 py-1 text-xs rounded-full font-medium transition-colors ${filterCats.length === 0 ? 'text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
                style={filterCats.length === 0 ? { background: theme.primary } : {}}
                data-testid="filter-cat-all"
              >
                All
              </button>
              {categories.map(c => {
                const on = filterCats.includes(c.id);
                return (
                  <button
                    key={c.id}
                    onClick={() => setFilterCats(on ? filterCats.filter(x => x !== c.id) : [...filterCats, c.id])}
                    className={`px-2.5 py-1 text-xs rounded-full font-medium transition-colors ${on ? 'text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
                    style={on ? { background: theme.primary } : {}}
                    data-testid={`filter-cat-${c.id}`}
                  >
                    {c.name}
                  </button>
                );
              })}
            </div>
            {/* Bulk action toolbar */}
            {selected.size > 0 && (
              <div className="flex items-center justify-between bg-amber-50 border border-amber-200 rounded px-3 py-2" data-testid="bulk-action-bar">
                <span className="text-sm font-medium text-amber-900">
                  {selected.size} selected
                  <button onClick={clearSelection} className="ml-2 text-xs underline text-amber-700" data-testid="bulk-clear">clear</button>
                </span>
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="outline" onClick={() => setBulkOpen(true)} data-testid="bulk-edit-open">
                    <Edit size={14} className="mr-1.5" /> Bulk Edit
                  </Button>
                  <Button size="sm" variant="outline" className="text-red-600" onClick={bulkDelete} data-testid="bulk-delete">
                    <Trash2 size={14} className="mr-1.5" /> Delete
                  </Button>
                </div>
              </div>
            )}
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <button onClick={allVisibleSelected ? clearSelection : selectAllVisible} className="flex items-center gap-1.5 hover:text-gray-800" data-testid="bulk-select-all">
                {allVisibleSelected ? <CheckSquare size={14} /> : <Square size={14} />}
                Select all visible ({filteredProducts.length})
              </button>
            </div>
          </div>

          {layoutMode === 'grid' ? (
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
              <Card key={product.id} className={`hover:shadow-lg transition-shadow ${product.eightySixed ? 'opacity-60' : ''} ${selected.has(product.id) ? 'ring-2' : ''}`} style={selected.has(product.id) ? { boxShadow: `0 0 0 2px ${theme.primary}` } : {}} data-testid={`product-card-${product.id}`}>
                <CardContent className="p-4">
                  <div className="relative">
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); toggleSelect(product.id); }}
                      className="absolute top-1 left-1 bg-white/95 hover:bg-white rounded p-0.5 border shadow-sm z-10"
                      data-testid={`select-${product.id}`}
                      aria-label="Select"
                    >
                      {selected.has(product.id) ? <CheckSquare size={14} style={{ color: theme.primary }} /> : <Square size={14} className="text-gray-400" />}
                    </button>
                    <button
                      type="button"
                      onClick={() => toggleEightySix(product)}
                      className={`absolute bottom-1 left-1 z-10 px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider shadow-sm transition-all ${product.eightySixed ? 'bg-red-600 text-white' : 'bg-white/90 text-gray-500 hover:text-red-600 border border-gray-200'}`}
                      data-testid={`toggle-86-${product.id}`}
                      title={product.eightySixed ? 'Un-86 (back in stock)' : 'Mark 86 (out of stock)'}
                    >
                      {product.eightySixed ? '86 · Tap to undo' : 'Set 86'}
                    </button>
                    <img src={product.image || 'https://placehold.co/300x200/e5e7eb/9ca3af?text=NUA'} alt={product.name} className="w-full h-40 object-cover rounded-lg mb-4" />
                    {/* Margin chip — system colour at low opacity */}
                    <span className={`absolute top-1 right-1 text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded border ${marginTone}`}
                      data-testid={`margin-badge-${product.id}`}>
                      {margin.toFixed(0)}% margin
                    </span>
                  </div>
                  {/* Inline-editable name */}
                  {inlineEditCell?.id === product.id && inlineEditCell?.field === 'name' ? (
                    <Input
                      autoFocus
                      value={inlineValue}
                      onChange={e => setInlineValue(e.target.value)}
                      onBlur={commitInlineEdit}
                      onKeyDown={e => { if (e.key === 'Enter') commitInlineEdit(); if (e.key === 'Escape') setInlineEditCell(null); }}
                      className="text-lg font-bold h-9 mt-1"
                      data-testid={`inline-name-${product.id}`}
                    />
                  ) : (
                    <h3
                      className="font-bold text-lg cursor-text hover:bg-amber-50 rounded px-0.5"
                      style={{ color: theme.text }}
                      onClick={() => startInlineEdit(product.id, 'name', product.name)}
                      title="Click to edit"
                    >
                      {product.name}
                    </h3>
                  )}
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-sm text-gray-500">{product.category}</span>
                    <span className="text-xs bg-gray-100 px-2 py-1 rounded font-mono">{product.sku}</span>
                  </div>
                  {(product.modifierIds || []).length > 0 && (
                    <p className="text-[10px] mt-1 font-medium" style={{ color: theme.secondary }} data-testid={`product-mods-${product.id}`}>
                      {product.modifierIds.length} modifier{product.modifierIds.length > 1 ? 's' : ''} attached
                    </p>
                  )}
                  <div className="flex items-center justify-between mt-2">
                    <div>
                      {inlineEditCell?.id === product.id && inlineEditCell?.field === 'price' ? (
                        <Input autoFocus type="number" step="0.01" value={inlineValue}
                          onChange={e => setInlineValue(e.target.value)}
                          onBlur={commitInlineEdit}
                          onKeyDown={e => { if (e.key === 'Enter') commitInlineEdit(); if (e.key === 'Escape') setInlineEditCell(null); }}
                          className="text-2xl font-bold h-10 w-24" data-testid={`inline-price-${product.id}`} />
                      ) : (
                        <p className="text-2xl font-bold cursor-text hover:bg-amber-50 rounded px-1"
                          style={{ color: theme.primary }}
                          onClick={() => startInlineEdit(product.id, 'price', product.price)}
                          title="Click to edit"
                          data-testid={`price-${product.id}`}>
                          ${Number(product.price).toFixed(2)}
                        </p>
                      )}
                      <p className="text-xs text-gray-500">Cost: ${Number(product.cost).toFixed(2)}</p>
                    </div>
                    <div className="text-right">
                      {inlineEditCell?.id === product.id && inlineEditCell?.field === 'stock' ? (
                        <Input autoFocus type="number" value={inlineValue}
                          onChange={e => setInlineValue(e.target.value)}
                          onBlur={commitInlineEdit}
                          onKeyDown={e => { if (e.key === 'Enter') commitInlineEdit(); if (e.key === 'Escape') setInlineEditCell(null); }}
                          className="h-8 w-20" data-testid={`inline-stock-${product.id}`} />
                      ) : (
                        <p className="text-sm font-medium cursor-text hover:bg-amber-50 rounded px-1"
                          onClick={() => startInlineEdit(product.id, 'stock', product.stock)}
                          title="Click to edit"
                          data-testid={`stock-${product.id}`}>
                          Stock: {product.stock}
                        </p>
                      )}
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
          ) : (
            /* TABLE VIEW */
            <Card><CardContent className="p-0 overflow-x-auto">
              <table className="w-full text-sm" data-testid="products-table">
                <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                  <tr>
                    <th className="px-3 py-2 text-left w-8">
                      <button onClick={allVisibleSelected ? clearSelection : selectAllVisible} data-testid="th-select-all">
                        {allVisibleSelected ? <CheckSquare size={14} style={{ color: theme.primary }} /> : <Square size={14} className="text-gray-400" />}
                      </button>
                    </th>
                    <th className="px-3 py-2 text-left">Image</th>
                    <th className="px-3 py-2 text-left">Name / SKU</th>
                    <th className="px-3 py-2 text-left">Category</th>
                    <th className="px-3 py-2 text-right">Price</th>
                    <th className="px-3 py-2 text-right">Cost</th>
                    <th className="px-3 py-2 text-right">Stock</th>
                    <th className="px-3 py-2 text-center">Mods</th>
                    <th className="px-3 py-2 text-center">Status</th>
                    <th className="px-3 py-2 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredProducts.length === 0 ? (
                    <tr><td colSpan={10} className="text-center py-12 text-gray-400">No products found</td></tr>
                  ) : filteredProducts.map(product => (
                    <tr key={product.id} className={`border-t hover:bg-amber-50/30 ${selected.has(product.id) ? 'bg-amber-50/60' : ''} ${product.eightySixed ? 'opacity-60' : ''}`} data-testid={`row-${product.id}`}>
                      <td className="px-3 py-2">
                        <button onClick={() => toggleSelect(product.id)} data-testid={`row-select-${product.id}`}>
                          {selected.has(product.id) ? <CheckSquare size={14} style={{ color: theme.primary }} /> : <Square size={14} className="text-gray-400" />}
                        </button>
                      </td>
                      <td className="px-3 py-2">
                        <img src={product.image || 'https://placehold.co/40x40/e5e7eb/9ca3af?text=NUA'} alt={product.name} className="w-10 h-10 rounded object-cover" />
                      </td>
                      <td className="px-3 py-2">
                        <p className="font-medium">{product.name}</p>
                        <p className="text-xs text-gray-500 font-mono">{product.sku}</p>
                      </td>
                      <td className="px-3 py-2 text-xs text-gray-700">{product.category}</td>
                      <td className="px-3 py-2 text-right">
                        {inlineEditCell?.id === product.id && inlineEditCell?.field === 'price' ? (
                          <Input autoFocus type="number" step="0.01" value={inlineValue}
                            onChange={e => setInlineValue(e.target.value)}
                            onBlur={commitInlineEdit}
                            onKeyDown={e => { if (e.key === 'Enter') commitInlineEdit(); if (e.key === 'Escape') setInlineEditCell(null); }}
                            className="h-8 w-24 ml-auto" />
                        ) : (
                          <button onClick={() => startInlineEdit(product.id, 'price', product.price)} className="font-mono hover:bg-amber-100 rounded px-1" title="Click to edit" data-testid={`row-price-${product.id}`}>
                            ${Number(product.price).toFixed(2)}
                          </button>
                        )}
                      </td>
                      <td className="px-3 py-2 text-right text-xs text-gray-600">${Number(product.cost).toFixed(2)}</td>
                      <td className="px-3 py-2 text-right">
                        {inlineEditCell?.id === product.id && inlineEditCell?.field === 'stock' ? (
                          <Input autoFocus type="number" value={inlineValue}
                            onChange={e => setInlineValue(e.target.value)}
                            onBlur={commitInlineEdit}
                            onKeyDown={e => { if (e.key === 'Enter') commitInlineEdit(); if (e.key === 'Escape') setInlineEditCell(null); }}
                            className="h-8 w-20 ml-auto" />
                        ) : (
                          <button onClick={() => startInlineEdit(product.id, 'stock', product.stock)} className="hover:bg-amber-100 rounded px-1" title="Click to edit" data-testid={`row-stock-${product.id}`}>
                            {product.stock}
                          </button>
                        )}
                      </td>
                      <td className="px-3 py-2 text-center text-xs">
                        {(product.modifierIds || []).length > 0 ? (
                          <span className="font-medium" style={{ color: theme.secondary }}>{product.modifierIds.length}</span>
                        ) : <span className="text-gray-300">—</span>}
                      </td>
                      <td className="px-3 py-2 text-center">
                        <button onClick={() => toggleEightySix(product)} className={`px-2 py-0.5 rounded text-[10px] font-bold ${product.eightySixed ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-700'}`} data-testid={`row-86-${product.id}`}>
                          {product.eightySixed ? '86' : 'OK'}
                        </button>
                      </td>
                      <td className="px-3 py-2 text-right">
                        <div className="flex gap-1 justify-end">
                          <Button variant="ghost" size="sm" onClick={() => openEditProduct(product)} data-testid={`row-edit-${product.id}`}><Edit size={12} /></Button>
                          <Button variant="ghost" size="sm" className="text-red-500" onClick={() => deleteProduct(product.id)} data-testid={`row-del-${product.id}`}><Trash2 size={12} /></Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent></Card>
          )}
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
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Category</label>
              <select className="w-full p-2 border rounded-md text-sm" value={productForm.categoryId} onChange={e => handleCategoryChange(e.target.value)} data-testid="product-category-select">
                <option value="">— Select a category —</option>
                {categories.map(c => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Input type="number" step="0.01" placeholder="Price" value={productForm.price} onChange={e => setProductForm({ ...productForm, price: e.target.value })} data-testid="product-price-input" />
              <Input type="number" step="0.01" placeholder="Cost" value={productForm.cost} onChange={e => setProductForm({ ...productForm, cost: e.target.value })} data-testid="product-cost-input" />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Input type="number" placeholder="Stock" value={productForm.stock} onChange={e => setProductForm({ ...productForm, stock: e.target.value })} data-testid="product-stock-input" />
              <Input placeholder="SKU" value={productForm.sku} onChange={e => setProductForm({ ...productForm, sku: e.target.value })} data-testid="product-sku-input" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Image</label>
              {productForm.image && (
                <img src={productForm.image} alt="" className="w-full h-32 object-cover rounded mb-2 border" />
              )}
              <div className="flex gap-2">
                <Input placeholder="Image URL or pick from library →" value={productForm.image} onChange={e => setProductForm({ ...productForm, image: e.target.value })} data-testid="product-image-input" />
                <Button type="button" variant="outline" onClick={() => setImageLibraryOpen(true)} data-testid="open-image-library">
                  <ImageIcon size={14} className="mr-1.5" /> Library
                </Button>
              </div>
            </div>
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
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Modifiers (select multiple)</label>
              {modifiers.length === 0 ? (
                <p className="text-xs text-gray-400 italic">No modifiers defined yet. Create some at <span className="font-mono">/modifiers</span> to use them here.</p>
              ) : (
                <div className="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto p-2 border rounded-md bg-gray-50" data-testid="product-modifiers-picker">
                  {modifiers.map(m => {
                    const selected = (productForm.modifierIds || []).includes(m.id);
                    return (
                      <button
                        key={m.id}
                        type="button"
                        onClick={() => toggleModifierForProduct(m.id)}
                        className={`px-2.5 py-1 text-xs rounded-full font-medium transition-colors border ${selected ? 'text-white border-transparent' : 'bg-white text-gray-700 border-gray-200 hover:border-gray-400'}`}
                        style={selected ? { background: theme.primary } : {}}
                        data-testid={`mod-toggle-${m.id}`}
                        title={`${m.options?.length || 0} options${m.mandatory ? ' · required' : ''}`}
                      >
                        {m.name}
                        {m.mandatory ? <span className="ml-1 opacity-70">*</span> : null}
                        {m.multiSelect ? <span className="ml-1 opacity-70">+</span> : null}
                      </button>
                    );
                  })}
                </div>
              )}
              {(productForm.modifierIds || []).length > 0 && (
                <p className="text-[10px] text-gray-500 mt-1">{productForm.modifierIds.length} selected · tap a chip to toggle</p>
              )}
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

      {/* Image Library — opens from product dialog */}
      <ImageLibrary
        open={imageLibraryOpen}
        onClose={() => setImageLibraryOpen(false)}
        onPick={(dataUrl) => setProductForm(prev => ({ ...prev, image: dataUrl }))}
        themeColor={theme.primary}
      />

      {/* Image Library — for bulk-image apply */}
      <ImageLibrary
        open={bulkImageLibraryOpen}
        onClose={() => setBulkImageLibraryOpen(false)}
        onPick={(dataUrl) => setBulkPatch(prev => ({ ...prev, image: dataUrl }))}
        themeColor={theme.primary}
      />

      {/* Bulk edit dialog */}
      <Dialog open={bulkOpen} onOpenChange={setBulkOpen}>
        <DialogContent className="max-w-xl" data-testid="bulk-edit-dialog">
          <DialogHeader>
            <DialogTitle>Bulk Edit · {selected.size} product{selected.size !== 1 ? 's' : ''}</DialogTitle>
          </DialogHeader>
          <p className="text-xs text-gray-500 -mt-2 mb-1">Only fields you fill in below will be applied. Empty fields leave existing values untouched.</p>
          <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-1">
            <div>
              <label className="text-xs uppercase text-gray-500 mb-1 block">Category</label>
              <select className="w-full p-2 border rounded text-sm" value={bulkPatch.categoryId} onChange={e => setBulkPatch({ ...bulkPatch, categoryId: e.target.value })} data-testid="bulk-category-select">
                <option value="">— Leave unchanged —</option>
                {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs uppercase text-gray-500 mb-1 block">Price ±%</label>
                <Input type="number" step="0.5" placeholder="e.g. 10 = +10%, -5 = -5%" value={bulkPatch.pricePercentDelta} onChange={e => setBulkPatch({ ...bulkPatch, pricePercentDelta: e.target.value })} data-testid="bulk-price-delta" />
              </div>
              <div>
                <label className="text-xs uppercase text-gray-500 mb-1 block">Set Cost $</label>
                <Input type="number" step="0.01" placeholder="Leave blank to keep" value={bulkPatch.cost} onChange={e => setBulkPatch({ ...bulkPatch, cost: e.target.value })} data-testid="bulk-cost" />
              </div>
              <div>
                <label className="text-xs uppercase text-gray-500 mb-1 block">GST Rate %</label>
                <Input type="number" step="0.1" placeholder="Leave blank to keep" value={bulkPatch.gstRate} onChange={e => setBulkPatch({ ...bulkPatch, gstRate: e.target.value })} data-testid="bulk-gst" />
              </div>
              <div>
                <label className="text-xs uppercase text-gray-500 mb-1 block">Status</label>
                <select className="w-full p-2 border rounded text-sm" value={bulkPatch.eightySixed} onChange={e => setBulkPatch({ ...bulkPatch, eightySixed: e.target.value })} data-testid="bulk-status">
                  <option value="">— Leave unchanged —</option>
                  <option value="false">Mark all as IN STOCK (un-86)</option>
                  <option value="true">Mark all as 86 (out of stock)</option>
                </select>
              </div>
            </div>
            <div>
              <label className="text-xs uppercase text-gray-500 mb-1 block">Image</label>
              <div className="flex gap-2 items-center">
                {bulkPatch.image ? (
                  <img src={bulkPatch.image} alt="" className="w-14 h-14 rounded object-cover border" />
                ) : <span className="text-xs text-gray-400">No bulk image change</span>}
                <Button type="button" variant="outline" size="sm" onClick={() => setBulkImageLibraryOpen(true)} data-testid="bulk-pick-image"><ImageIcon size={14} className="mr-1.5" /> Pick from Library</Button>
                {bulkPatch.image && <button type="button" onClick={() => setBulkPatch({ ...bulkPatch, image: '' })} className="text-xs text-gray-400 hover:text-red-600">Clear</button>}
              </div>
            </div>
            <div>
              <label className="text-xs uppercase text-gray-500 mb-1 block">Add modifiers (assign to all selected)</label>
              <div className="flex flex-wrap gap-1.5 p-2 border rounded bg-gray-50 max-h-32 overflow-y-auto">
                {modifiers.length === 0 ? <span className="text-xs text-gray-400 italic">No modifiers yet</span> : modifiers.map(m => {
                  const on = bulkPatch.addModifierIds.includes(m.id);
                  return (
                    <button key={m.id} type="button"
                      onClick={() => setBulkPatch(prev => ({ ...prev, addModifierIds: on ? prev.addModifierIds.filter(x => x !== m.id) : [...prev.addModifierIds, m.id] }))}
                      className={`px-2 py-0.5 text-xs rounded-full font-medium border ${on ? 'text-white border-transparent' : 'bg-white text-gray-700 border-gray-200'}`}
                      style={on ? { background: theme.primary } : {}}
                      data-testid={`bulk-add-mod-${m.id}`}>
                      {m.name}
                    </button>
                  );
                })}
              </div>
            </div>
            <div>
              <label className="text-xs uppercase text-gray-500 mb-1 block">Remove modifiers (from all selected)</label>
              <div className="flex flex-wrap gap-1.5 p-2 border rounded bg-gray-50 max-h-32 overflow-y-auto">
                {modifiers.length === 0 ? <span className="text-xs text-gray-400 italic">No modifiers yet</span> : modifiers.map(m => {
                  const on = bulkPatch.removeModifierIds.includes(m.id);
                  return (
                    <button key={m.id} type="button"
                      onClick={() => setBulkPatch(prev => ({ ...prev, removeModifierIds: on ? prev.removeModifierIds.filter(x => x !== m.id) : [...prev.removeModifierIds, m.id] }))}
                      className={`px-2 py-0.5 text-xs rounded-full font-medium border ${on ? 'text-white border-transparent' : 'bg-white text-gray-700 border-gray-200'}`}
                      style={on ? { background: '#dc2626' } : {}}
                      data-testid={`bulk-rm-mod-${m.id}`}>
                      <Ban size={10} className="inline mr-0.5" /> {m.name}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
          <div className="flex gap-2 pt-3 border-t">
            <Button variant="outline" onClick={() => setBulkOpen(false)} className="flex-1">Cancel</Button>
            <Button onClick={applyBulk} className="flex-1 text-white hover:opacity-90" style={{ background: theme.primary }} data-testid="bulk-apply">
              Apply to {selected.size}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Products;
