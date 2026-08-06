import React, { useMemo, useState } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Search, Percent, DollarSign, Package, Tag, Sparkles, TrendingUp } from 'lucide-react';
import { finalizeAPI } from '../../services/api';
import { toast } from 'sonner';

/**
 * Create / edit a promotion.
 *
 * Owner/manager can:
 *   • Choose Type: Category Discount · Bundle Deal · Mixed
 *   • Choose Pricing Mode: Percentage OFF · Fixed Bundle Price ($)
 *   • Select Categories (multi-select) AND/OR Individual Items (multi-select)
 *   • Set min/max quantity rules for bundle deals (e.g. "any 3 = $25")
 *   • Full scheduling (dates + weekdays + time window)
 */
export const PromotionDialog = ({
  open, onClose,
  theme,
  editingPromo,
  promoForm, setPromoForm,
  onSave,
  categories = [],
  products = [],
}) => {
  const [itemSearch, setItemSearch] = useState('');
  const [aiPanelOpen, setAiPanelOpen] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [aiSuggestions, setAiSuggestions] = useState(null);

  const runAiDiscovery = async () => {
    setAiBusy(true);
    try {
      const r = await finalizeAPI.bundleSuggestions(30);
      setAiSuggestions(r.data);
      if ((r.data.pairs?.length || 0) + (r.data.triples?.length || 0) === 0) {
        toast.info('No repeat basket patterns yet — need more transactions.');
      }
    } catch (e) { toast.error(e?.response?.data?.detail || 'AI discovery failed'); }
    finally { setAiBusy(false); }
  };

  const applySuggestion = (s) => {
    setPromoForm({
      ...promoForm,
      name: promoForm.name || `${s.productNames.slice(0, 2).join(' + ')}${s.productIds.length > 2 ? ' + more' : ''} Bundle`,
      type: 'bundle',
      pricingMode: 'fixed_price',
      bundlePrice: s.proposedBundlePrice,
      minQuantity: s.productIds.length,
      products: s.productIds,
      categories: s.categories && s.categories.length ? s.categories : (promoForm.categories || []),
    });
    setAiPanelOpen(false);
    toast.success(`Applied · ${s.productIds.length}-item bundle @ $${s.proposedBundlePrice.toFixed(2)}`);
  };

  const selectedCategories = promoForm.categories || (promoForm.category ? [promoForm.category] : []);
  const selectedProducts = promoForm.products || [];

  // An empty channels[] means "unrestricted" (both boxes show checked), so a
  // promo created before this field existed keeps behaving exactly as it did.
  const ALL_CHANNELS = ['dine-in', 'takeaway'];
  const selectedChannels = (promoForm.channels && promoForm.channels.length) ? promoForm.channels : ALL_CHANNELS;
  const toggleChannel = (ch) => {
    const next = selectedChannels.includes(ch)
      ? selectedChannels.filter(c => c !== ch)
      : [...selectedChannels, ch];
    if (next.length === 0) return; // at least one channel must stay selected
    setPromoForm({ ...promoForm, channels: next.length === ALL_CHANNELS.length ? [] : next });
  };

  const toggleCategory = (name) => {
    const cur = new Set(selectedCategories);
    if (cur.has(name)) cur.delete(name); else cur.add(name);
    setPromoForm({
      ...promoForm,
      categories: Array.from(cur),
      // keep single-category field in sync for back-compat when exactly 1 is picked
      category: cur.size === 1 ? Array.from(cur)[0] : '',
    });
  };

  const toggleProduct = (id) => {
    const cur = new Set(selectedProducts);
    if (cur.has(id)) cur.delete(id); else cur.add(id);
    setPromoForm({ ...promoForm, products: Array.from(cur) });
  };

  const filteredProducts = useMemo(() => {
    const term = itemSearch.trim().toLowerCase();
    return (products || [])
      .filter(p => !term || (p.name || '').toLowerCase().includes(term) || (p.category || '').toLowerCase().includes(term))
      .slice(0, 60);
  }, [products, itemSearch]);

  // Compute preview of the bundle savings
  const bundlePreview = useMemo(() => {
    if (promoForm.pricingMode !== 'fixed_price' || !promoForm.bundlePrice) return null;
    const sel = (products || []).filter(p => selectedProducts.includes(p.id));
    const originalTotal = sel.reduce((s, p) => s + (p.price || 0), 0);
    const bundle = parseFloat(promoForm.bundlePrice) || 0;
    if (originalTotal <= 0 || bundle >= originalTotal) return null;
    return {
      originalTotal: originalTotal.toFixed(2),
      bundle: bundle.toFixed(2),
      savings: (originalTotal - bundle).toFixed(2),
      pct: Math.round((1 - bundle / originalTotal) * 100),
    };
  }, [promoForm.pricingMode, promoForm.bundlePrice, promoForm.products, products, selectedProducts]);

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="promo-dialog">
        <DialogHeader>
          <DialogTitle>{editingPromo ? 'Edit Promotion' : 'Create Promotion'}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          {!editingPromo && (
            <div className="rounded-lg border-2 border-dashed border-purple-200 bg-purple-50/40 p-3" data-testid="ai-discovery-block">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Sparkles size={14} className="text-purple-600" />
                  <p className="text-sm font-semibold text-purple-800">AI Bundle Discovery</p>
                  <Badge className="bg-purple-100 text-purple-700 border-0 text-[10px]">Market-basket</Badge>
                </div>
                <Button size="sm" variant="outline" onClick={() => { setAiPanelOpen(!aiPanelOpen); if (!aiSuggestions) runAiDiscovery(); }}
                  data-testid="ai-discover-btn">
                  {aiPanelOpen ? 'Hide' : 'Show'} suggestions
                </Button>
              </div>
              <p className="text-[11px] text-purple-700 mt-1">
                Scans your last 30 days of orders to find combos guests already buy together and proposes a bundle price with a 33% margin floor.
              </p>
              {aiPanelOpen && (
                <div className="mt-3 space-y-2 max-h-64 overflow-y-auto" data-testid="ai-suggestions-panel">
                  {aiBusy && <p className="text-xs text-gray-500">Analysing baskets…</p>}
                  {!aiBusy && aiSuggestions && (
                    <>
                      <p className="text-[10px] uppercase tracking-widest text-purple-700 font-semibold">
                        {aiSuggestions.ordersAnalysed} orders scanned · {aiSuggestions.pairs.length + aiSuggestions.triples.length} candidates
                      </p>
                      {[...(aiSuggestions.triples || []), ...(aiSuggestions.pairs || [])].slice(0, 6).map((s, i) => (
                        <button key={i} type="button" onClick={() => applySuggestion(s)}
                          className="w-full text-left bg-white rounded-lg border border-purple-100 p-2.5 hover:border-purple-400 transition-colors"
                          data-testid={`ai-suggestion-${i}`}>
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-semibold truncate">{s.productNames.join(' + ')}</p>
                              <div className="flex items-center gap-2 text-[10px] text-gray-500 mt-0.5">
                                <span className="flex items-center gap-1"><TrendingUp size={9} /> {s.coOccurrenceCount}× ordered · {s.supportPct}% support</span>
                                <Badge className={`border-0 text-[9px] ${s.confidence === 'high' ? 'bg-emerald-100 text-emerald-700' : s.confidence === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-600'}`}>
                                  {s.confidence}
                                </Badge>
                              </div>
                            </div>
                            <div className="text-right shrink-0">
                              <p className="text-xs text-gray-400 line-through">${s.avgAlaCarte.toFixed(2)}</p>
                              <p className="text-sm font-bold text-emerald-700">${s.proposedBundlePrice.toFixed(2)}</p>
                              <p className="text-[10px] text-emerald-600">−{s.savingsPct}%</p>
                            </div>
                          </div>
                        </button>
                      ))}
                      {(aiSuggestions.pairs.length + aiSuggestions.triples.length) === 0 && (
                        <p className="text-xs text-gray-500 italic">No repeat combos yet in the last 30 days.</p>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          )}

          <Input
            placeholder="Promotion name (e.g. 'Family Feast', 'Happy Hour')"
            value={promoForm.name}
            onChange={e => setPromoForm({ ...promoForm, name: e.target.value })}
            data-testid="promo-name-input"
          />

          {/* Type selector */}
          <div>
            <label className="text-xs font-medium text-gray-500 mb-1.5 block">Promotion type</label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { v: 'category', label: 'Category Discount', icon: Tag, desc: 'Apply to a whole category' },
                { v: 'bundle', label: 'Bundle Deal', icon: Package, desc: 'Combine items for one price' },
                { v: 'mixed', label: 'Mixed', icon: Percent, desc: 'Categories + specific items' },
              ].map(t => {
                const on = promoForm.type === t.v;
                const Icon = t.icon;
                return (
                  <button
                    key={t.v} type="button"
                    onClick={() => setPromoForm({ ...promoForm, type: t.v })}
                    className={`text-left p-3 rounded-lg border-2 transition-all ${on ? 'border-orange-500 bg-orange-50/60' : 'border-gray-200 hover:border-gray-300'}`}
                    data-testid={`promo-type-${t.v}`}
                  >
                    <Icon size={16} className={on ? 'text-orange-600' : 'text-gray-400'} />
                    <p className="text-xs font-semibold mt-1">{t.label}</p>
                    <p className="text-[10px] text-gray-500 leading-tight">{t.desc}</p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Pricing mode + values */}
          <div>
            <label className="text-xs font-medium text-gray-500 mb-1.5 block">Pricing</label>
            <div className="grid grid-cols-2 gap-2 mb-2">
              <button type="button"
                onClick={() => setPromoForm({ ...promoForm, pricingMode: 'percentage' })}
                className={`p-2.5 rounded-lg border-2 flex items-center gap-2 transition-all ${promoForm.pricingMode === 'percentage' ? 'border-orange-500 bg-orange-50/60' : 'border-gray-200'}`}
                data-testid="promo-mode-percentage">
                <Percent size={14} />
                <span className="text-sm font-semibold">Percentage OFF</span>
              </button>
              <button type="button"
                onClick={() => setPromoForm({ ...promoForm, pricingMode: 'fixed_price' })}
                className={`p-2.5 rounded-lg border-2 flex items-center gap-2 transition-all ${promoForm.pricingMode === 'fixed_price' ? 'border-orange-500 bg-orange-50/60' : 'border-gray-200'}`}
                data-testid="promo-mode-fixed">
                <DollarSign size={14} />
                <span className="text-sm font-semibold">Fixed Bundle Price</span>
              </button>
            </div>

            {promoForm.pricingMode === 'percentage' ? (
              <div className="relative">
                <Input
                  type="number" step="0.1" min="0" max="100"
                  placeholder="Discount %"
                  value={promoForm.discount}
                  onChange={e => setPromoForm({ ...promoForm, discount: e.target.value })}
                  data-testid="promo-discount-input"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400">%</span>
              </div>
            ) : (
              <div className="space-y-2">
                <div className="relative">
                  <Input
                    type="number" step="0.01" min="0"
                    placeholder="Bundle price"
                    value={promoForm.bundlePrice || ''}
                    onChange={e => setPromoForm({ ...promoForm, bundlePrice: e.target.value })}
                    data-testid="promo-bundle-price-input"
                    className="pl-7"
                  />
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-gray-500">$</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <Input type="number" min="1" placeholder="Min items (e.g. 3)"
                    value={promoForm.minQuantity || ''}
                    onChange={e => setPromoForm({ ...promoForm, minQuantity: parseInt(e.target.value) || null })}
                    data-testid="promo-min-qty" />
                  <Input type="number" min="1" placeholder="Max items (optional)"
                    value={promoForm.maxQuantity || ''}
                    onChange={e => setPromoForm({ ...promoForm, maxQuantity: parseInt(e.target.value) || null })}
                    data-testid="promo-max-qty" />
                </div>
                {bundlePreview && (
                  <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-2 flex items-center justify-between text-xs" data-testid="promo-bundle-preview">
                    <div>
                      <span className="text-gray-500 line-through">${bundlePreview.originalTotal}</span>
                      <span className="mx-2 font-bold text-emerald-700">${bundlePreview.bundle}</span>
                    </div>
                    <Badge className="bg-emerald-100 text-emerald-700 border-0">
                      Save ${bundlePreview.savings} · {bundlePreview.pct}% off
                    </Badge>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Categories multi-select */}
          {(promoForm.type === 'category' || promoForm.type === 'mixed') && (
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1.5 block">
                Categories <span className="text-gray-400">({selectedCategories.length} selected)</span>
              </label>
              <div className="flex flex-wrap gap-1.5" data-testid="promo-categories">
                {(categories || []).map(c => {
                  const on = selectedCategories.includes(c.name);
                  return (
                    <button key={c.id || c.name} type="button"
                      onClick={() => toggleCategory(c.name)}
                      className={`px-2.5 py-1 text-xs rounded-full font-medium transition-colors ${on ? 'text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
                      style={on ? { background: theme?.primary || '#f97316' } : {}}
                      data-testid={`promo-cat-${(c.name || '').toLowerCase().replace(/\s+/g, '-')}`}>
                      {c.name}
                    </button>
                  );
                })}
                {(!categories || categories.length === 0) && (
                  <span className="text-xs text-gray-400 italic">No categories yet.</span>
                )}
              </div>
            </div>
          )}

          {/* Individual products multi-select */}
          {(promoForm.type === 'bundle' || promoForm.type === 'mixed') && (
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1.5 block">
                Individual items <span className="text-gray-400">({selectedProducts.length} selected)</span>
              </label>
              <div className="relative mb-2">
                <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
                <Input value={itemSearch} onChange={e => setItemSearch(e.target.value)}
                  placeholder="Search products by name or category…"
                  className="pl-8 h-8 text-sm" data-testid="promo-item-search" />
              </div>
              <div className="max-h-52 overflow-y-auto border rounded-lg divide-y bg-gray-50/40" data-testid="promo-items-list">
                {filteredProducts.length === 0 ? (
                  <p className="text-xs text-gray-400 italic p-3">No matching items.</p>
                ) : filteredProducts.map(p => {
                  const on = selectedProducts.includes(p.id);
                  return (
                    <label key={p.id}
                      className={`flex items-center gap-2 p-2 text-sm cursor-pointer transition-colors ${on ? 'bg-orange-50' : 'hover:bg-white'}`}
                      data-testid={`promo-item-${p.id}`}>
                      <input type="checkbox" checked={on} onChange={() => toggleProduct(p.id)} className="accent-orange-500" />
                      <span className="flex-1">{p.name}</span>
                      <span className="text-xs text-gray-500">{p.category}</span>
                      <span className="text-xs font-mono font-semibold">${(p.price || 0).toFixed(2)}</span>
                    </label>
                  );
                })}
              </div>
            </div>
          )}

          <div>
            <label className="text-xs font-medium text-gray-500 mb-1 block">Date range (optional)</label>
            <div className="grid grid-cols-2 gap-2">
              <Input type="date" value={promoForm.startDate}
                onChange={e => setPromoForm({ ...promoForm, startDate: e.target.value })}
                data-testid="promo-start-date" />
              <Input type="date" value={promoForm.endDate}
                onChange={e => setPromoForm({ ...promoForm, endDate: e.target.value })}
                data-testid="promo-end-date" />
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-gray-500 mb-1 block">
              Active days (select none for everyday)
            </label>
            <div className="flex flex-wrap gap-1.5">
              {['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'].map(day => {
                const on = promoForm.activeDays.includes(day);
                return (
                  <button
                    key={day} type="button"
                    onClick={() => setPromoForm({
                      ...promoForm,
                      activeDays: on ? promoForm.activeDays.filter(d => d !== day) : [...promoForm.activeDays, day],
                    })}
                    className={`px-2.5 py-1 text-xs rounded-full font-medium transition-colors ${on ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
                    data-testid={`promo-day-${day.toLowerCase()}`}
                  >{day.slice(0, 3)}</button>
                );
              })}
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-gray-500 mb-1 block">Time window (optional)</label>
            <div className="grid grid-cols-2 gap-2">
              <Input type="time" value={promoForm.startTime}
                onChange={e => setPromoForm({ ...promoForm, startTime: e.target.value })}
                data-testid="promo-start-time" />
              <Input type="time" value={promoForm.endTime}
                onChange={e => setPromoForm({ ...promoForm, endTime: e.target.value })}
                data-testid="promo-end-time" />
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-gray-500 mb-1 block">
              Applies to <span className="text-gray-400">(e.g. a Happy Hour drinks promo should be dine-in only)</span>
            </label>
            <div className="flex flex-wrap gap-1.5">
              {[{ v: 'dine-in', label: 'Dine-in' }, { v: 'takeaway', label: 'Takeaway' }].map(ch => {
                const on = selectedChannels.includes(ch.v);
                return (
                  <button
                    key={ch.v} type="button"
                    onClick={() => toggleChannel(ch.v)}
                    className={`px-2.5 py-1 text-xs rounded-full font-medium transition-colors ${on ? 'text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
                    style={on ? { background: theme?.primary || '#f97316' } : {}}
                    data-testid={`promo-channel-${ch.v}`}
                  >{ch.label}</button>
                );
              })}
            </div>
          </div>

          <Input
            placeholder="Schedule note (e.g. Happy Hour, Family Feast)"
            value={promoForm.schedule}
            onChange={e => setPromoForm({ ...promoForm, schedule: e.target.value })}
            data-testid="promo-schedule-input"
          />

          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={promoForm.active}
                onChange={e => setPromoForm({ ...promoForm, active: e.target.checked })}
                data-testid="promo-active-toggle" />
              Active
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={!!promoForm.stackable}
                onChange={e => setPromoForm({ ...promoForm, stackable: e.target.checked })}
                data-testid="promo-stackable-toggle" />
              Stackable with other promos
            </label>
          </div>

          <Button
            className="w-full text-white" style={{ backgroundColor: theme?.primary || '#f97316' }}
            onClick={onSave} data-testid="save-promo-btn"
          >
            {editingPromo ? 'Update Promotion' : 'Create Promotion'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
