import React, { useMemo, useState } from 'react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Check, X } from 'lucide-react';

/**
 * Modifier selection panel — docked in the layout next to the cart (not a
 * full-screen popup), so the cart and product grid stay visible while the
 * cashier picks modifiers. Opens when an item with attached modifierIds is
 * added to the POS cart. Mandatory modifiers MUST be answered before the
 * user can confirm. Multi-select modifiers respect `maxSelections`.
 *
 * Supports nested/conditional modifier groups: an option with a
 * `childModifierId` reveals a follow-up modifier group directly under it
 * once selected (e.g. "Oat Milk" -> "Sweetness Level"), up to 3 levels deep.
 *
 * Props:
 *  - product:         the product being added
 *  - modifiers:       full list of modifier defs from /api/modifiers
 *  - open:            boolean
 *  - onClose:         () => void
 *  - onConfirm:       (selections, totalExtra) => void
 *      selections shape: [{ modifierId, modifierName, options: [{name, price}] }]
 *  - themeColor:      brand primary (NUA orange)
 */
export default function ModifierPanel({ product, modifiers, open, onClose, onConfirm, themeColor = '#f58c14' }) {
  const productModifiers = useMemo(() => {
    if (!product) return [];
    const ids = product.modifierIds || [];
    return ids
      .map(id => modifiers.find(m => m.id === id))
      .filter(Boolean);
  }, [product, modifiers]);

  // selected: { [modifierId]: Set<optionName> }
  const [selected, setSelected] = useState({});
  const [lastProductId, setLastProductId] = useState(null);

  // Reset selection when a different product is opened.
  if (open && product?.id && product.id !== lastProductId) {
    setLastProductId(product.id);
    setSelected({});
  }

  // Nested modifiers: a chosen option can reveal follow-up modifier group(s)
  // (e.g. "Oat Milk" -> "Sweetness Level"), up to 3 levels deep. Walk the
  // product's top-level groups, and for each currently-selected option that
  // has a childModifierId, splice that child group in right after it.
  const MAX_MODIFIER_DEPTH = 3;
  const visibleModifiers = useMemo(() => {
    const out = [];
    const seen = new Set();
    const walk = (mod, depth) => {
      if (!mod || seen.has(mod.id) || depth > MAX_MODIFIER_DEPTH) return;
      seen.add(mod.id);
      out.push(mod);
      const chosenNames = selected[mod.id] || new Set();
      (mod.options || []).forEach(opt => {
        if (chosenNames.has(opt.name) && opt.childModifierId) {
          const child = modifiers.find(m => m.id === opt.childModifierId);
          if (child) walk(child, depth + 1);
        }
      });
    };
    productModifiers.forEach(m => walk(m, 1));
    return out;
  }, [productModifiers, modifiers, selected]);

  if (!open || !product) return null;

  const toggleOption = (mod, optName) => {
    setSelected(prev => {
      const current = new Set(prev[mod.id] || []);
      if (mod.multiSelect) {
        if (current.has(optName)) {
          current.delete(optName);
        } else {
          if (mod.maxSelections > 0 && current.size >= mod.maxSelections) return prev;
          current.add(optName);
        }
      } else {
        // single-select: clear + pick
        if (current.has(optName)) {
          current.clear();
        } else {
          current.clear();
          current.add(optName);
        }
      }
      return { ...prev, [mod.id]: current };
    });
  };

  // Validation: all mandatory modifiers must have ≥1 selection.
  // If modifier definitions haven't loaded yet for a product that DOES have modifierIds,
  // block confirm until they arrive.
  const isLoadingDefs = (product.modifierIds || []).length > 0 && productModifiers.length === 0;
  const missing = visibleModifiers.filter(m => m.mandatory && (!(selected[m.id]) || selected[m.id].size === 0));
  const canConfirm = !isLoadingDefs && missing.length === 0;

  // Compute extra price across all selected option prices
  const extra = visibleModifiers.reduce((sum, m) => {
    const chosenNames = selected[m.id] || new Set();
    const optPrices = (m.options || []).filter(o => chosenNames.has(o.name)).reduce((s, o) => s + (o.price || 0), 0);
    return sum + optPrices;
  }, 0);

  const total = (product.price || 0) + extra;

  const confirm = () => {
    if (!canConfirm) return;
    const selections = visibleModifiers
      .map(m => {
        const names = Array.from(selected[m.id] || []);
        if (names.length === 0) return null;
        const opts = (m.options || []).filter(o => names.includes(o.name));
        return { modifierId: m.id, modifierName: m.name, options: opts };
      })
      .filter(Boolean);
    onConfirm(selections, extra);
  };

  return (
    <div
      className="w-full lg:w-[380px] flex-shrink-0 flex flex-col min-h-0 border bg-white rounded-xl shadow-sm p-4 animate-in slide-in-from-right-4 fade-in duration-200"
      data-testid="modifier-sheet"
    >
      <div className="flex items-center justify-between gap-3 pb-3 border-b mb-3">
        <div className="min-w-0">
          <h2 className="font-bold truncate">{product.name}</h2>
          <span className="text-sm font-mono" style={{ color: themeColor }}>${total.toFixed(2)}</span>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="p-1.5 rounded-md hover:bg-gray-100 text-gray-500 flex-shrink-0"
          aria-label="Close"
          data-testid="mod-close"
        >
          <X size={18} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto space-y-4 min-h-0">
        {productModifiers.length === 0 ? (
          (product.modifierIds || []).length > 0 ? (
            <p className="text-center text-amber-600 text-sm py-6" data-testid="mod-loading">
              Loading modifiers… please retry in a moment
            </p>
          ) : (
            <p className="text-center text-gray-400 text-sm py-6">No modifiers — tap Confirm to add</p>
          )
        ) : visibleModifiers.map(mod => {
          const chosenNames = selected[mod.id] || new Set();
          const isNested = !productModifiers.some(m => m.id === mod.id);
          return (
            <div key={mod.id} data-testid={`mod-group-${mod.id}`} className={isNested ? 'pl-3 border-l-2 border-gray-200' : ''}>
              <div className="flex items-center gap-2 mb-2">
                <h3 className="text-sm font-bold">{mod.name}</h3>
                {mod.mandatory ? (
                  <Badge className="bg-red-100 text-red-700 text-[10px]">Required</Badge>
                ) : (
                  <Badge variant="outline" className="text-[10px]">Optional</Badge>
                )}
                {mod.multiSelect && (
                  <span className="text-[10px] text-gray-500">choose up to {mod.maxSelections || (mod.options || []).length}</span>
                )}
              </div>
              <div className="grid grid-cols-2 gap-2">
                {(mod.options || []).map(opt => {
                  const isSelected = chosenNames.has(opt.name);
                  return (
                    <button
                      key={opt.name}
                      type="button"
                      onClick={() => toggleOption(mod, opt.name)}
                      className={`flex items-center justify-between gap-2 px-3 py-2 rounded-lg border text-sm transition-all ${isSelected ? 'text-white border-transparent' : 'bg-white text-gray-700 border-gray-200 hover:border-gray-400'}`}
                      style={isSelected ? { background: themeColor } : {}}
                      data-testid={`mod-opt-${mod.id}-${opt.name}`}
                    >
                      <span className="flex items-center gap-1.5">
                        {isSelected && <Check size={12} />}
                        {opt.name}
                      </span>
                      {opt.price > 0 && (
                        <span className={`text-xs font-mono ${isSelected ? 'text-white/90' : 'text-gray-500'}`}>+${opt.price.toFixed(2)}</span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex flex-col gap-2 pt-3 border-t mt-3">
        {!canConfirm && (
          <p className="text-xs text-red-600" data-testid="mod-validation">
            Pick a choice for: {missing.map(m => m.name).join(', ')}
          </p>
        )}
        <div className="flex gap-2">
          <Button variant="outline" onClick={onClose} className="flex-1" data-testid="mod-cancel">Cancel</Button>
          <Button
            onClick={confirm}
            disabled={!canConfirm}
            className="flex-1 text-white hover:opacity-90"
            style={{ background: themeColor }}
            data-testid="mod-confirm"
          >
            Add — ${total.toFixed(2)}
          </Button>
        </div>
      </div>
    </div>
  );
}
