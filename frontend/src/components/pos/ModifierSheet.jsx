import React, { useMemo, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Check } from 'lucide-react';

/**
 * Modifier selection sheet — opens when an item with attached modifierIds is
 * added to the POS cart. Mandatory modifiers MUST be answered before the user
 * can confirm. Multi-select modifiers respect `maxSelections`.
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
export default function ModifierSheet({ product, modifiers, open, onClose, onConfirm, themeColor = '#f58c14' }) {
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

  if (!product) return null;

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

  // Validation: all mandatory modifiers must have ≥1 selection
  const missing = productModifiers.filter(m => m.mandatory && (!(selected[m.id]) || selected[m.id].size === 0));
  const canConfirm = missing.length === 0;

  // Compute extra price across all selected option prices
  const extra = productModifiers.reduce((sum, m) => {
    const chosenNames = selected[m.id] || new Set();
    const optPrices = (m.options || []).filter(o => chosenNames.has(o.name)).reduce((s, o) => s + (o.price || 0), 0);
    return sum + optPrices;
  }, 0);

  const total = (product.price || 0) + extra;

  const confirm = () => {
    if (!canConfirm) return;
    const selections = productModifiers
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
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="max-w-lg" data-testid="modifier-sheet">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between gap-3">
            <span>{product.name}</span>
            <span className="text-sm font-mono" style={{ color: themeColor }}>${total.toFixed(2)}</span>
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 max-h-[60vh] overflow-y-auto py-1">
          {productModifiers.length === 0 ? (
            <p className="text-center text-gray-400 text-sm py-6">No modifiers — tap Confirm to add</p>
          ) : productModifiers.map(mod => {
            const chosenNames = selected[mod.id] || new Set();
            return (
              <div key={mod.id} data-testid={`mod-group-${mod.id}`}>
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

        <div className="flex flex-col gap-2 pt-3 border-t">
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
      </DialogContent>
    </Dialog>
  );
}
