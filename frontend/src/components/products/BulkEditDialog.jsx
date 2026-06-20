import React from 'react';
import { ImageIcon, Ban } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';

/**
 * Bulk-edit dialog for the Products page. Only fields the user fills in are
 * applied; empty fields leave existing values untouched. All state mutations
 * flow through the parent via setBulkPatch / onApply.
 */
export const BulkEditDialog = ({
  open, onClose,
  theme,
  selectedCount,
  bulkPatch, setBulkPatch,
  categories, modifiers,
  onApply,
  onOpenImageLibrary,
}) => (
  <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
    <DialogContent className="max-w-xl" data-testid="bulk-edit-dialog">
      <DialogHeader>
        <DialogTitle>Bulk Edit · {selectedCount} product{selectedCount !== 1 ? 's' : ''}</DialogTitle>
      </DialogHeader>
      <p className="text-xs text-gray-500 -mt-2 mb-1">
        Only fields you fill in below will be applied. Empty fields leave existing values untouched.
      </p>
      <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-1">
        <div>
          <label className="text-xs uppercase text-gray-500 mb-1 block">Category</label>
          <select
            className="w-full p-2 border rounded text-sm"
            value={bulkPatch.categoryId}
            onChange={e => setBulkPatch({ ...bulkPatch, categoryId: e.target.value })}
            data-testid="bulk-category-select"
          >
            <option value="">— Leave unchanged —</option>
            {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs uppercase text-gray-500 mb-1 block">Price ±%</label>
            <Input
              type="number" step="0.5"
              placeholder="e.g. 10 = +10%, -5 = -5%"
              value={bulkPatch.pricePercentDelta}
              onChange={e => setBulkPatch({ ...bulkPatch, pricePercentDelta: e.target.value })}
              data-testid="bulk-price-delta"
            />
          </div>
          <div>
            <label className="text-xs uppercase text-gray-500 mb-1 block">Set Cost $</label>
            <Input
              type="number" step="0.01"
              placeholder="Leave blank to keep"
              value={bulkPatch.cost}
              onChange={e => setBulkPatch({ ...bulkPatch, cost: e.target.value })}
              data-testid="bulk-cost"
            />
          </div>
          <div>
            <label className="text-xs uppercase text-gray-500 mb-1 block">GST Rate %</label>
            <Input
              type="number" step="0.1"
              placeholder="Leave blank to keep"
              value={bulkPatch.gstRate}
              onChange={e => setBulkPatch({ ...bulkPatch, gstRate: e.target.value })}
              data-testid="bulk-gst"
            />
          </div>
          <div>
            <label className="text-xs uppercase text-gray-500 mb-1 block">Status</label>
            <select
              className="w-full p-2 border rounded text-sm"
              value={bulkPatch.eightySixed}
              onChange={e => setBulkPatch({ ...bulkPatch, eightySixed: e.target.value })}
              data-testid="bulk-status"
            >
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
            <Button
              type="button" variant="outline" size="sm"
              onClick={onOpenImageLibrary}
              data-testid="bulk-pick-image"
            ><ImageIcon size={14} className="mr-1.5" /> Pick from Library</Button>
            {bulkPatch.image && (
              <button
                type="button"
                onClick={() => setBulkPatch({ ...bulkPatch, image: '' })}
                className="text-xs text-gray-400 hover:text-red-600"
              >Clear</button>
            )}
          </div>
        </div>
        <div>
          <label className="text-xs uppercase text-gray-500 mb-1 block">Add modifiers (assign to all selected)</label>
          <div className="flex flex-wrap gap-1.5 p-2 border rounded bg-gray-50 max-h-32 overflow-y-auto">
            {modifiers.length === 0 ? <span className="text-xs text-gray-400 italic">No modifiers yet</span> : modifiers.map(m => {
              const on = bulkPatch.addModifierIds.includes(m.id);
              return (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => setBulkPatch(prev => ({
                    ...prev,
                    addModifierIds: on ? prev.addModifierIds.filter(x => x !== m.id) : [...prev.addModifierIds, m.id],
                  }))}
                  className={`px-2 py-0.5 text-xs rounded-full font-medium border ${on ? 'text-white border-transparent' : 'bg-white text-gray-700 border-gray-200'}`}
                  style={on ? { background: theme.primary } : {}}
                  data-testid={`bulk-add-mod-${m.id}`}
                >{m.name}</button>
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
                <button
                  key={m.id}
                  type="button"
                  onClick={() => setBulkPatch(prev => ({
                    ...prev,
                    removeModifierIds: on ? prev.removeModifierIds.filter(x => x !== m.id) : [...prev.removeModifierIds, m.id],
                  }))}
                  className={`px-2 py-0.5 text-xs rounded-full font-medium border ${on ? 'text-white border-transparent' : 'bg-white text-gray-700 border-gray-200'}`}
                  style={on ? { background: '#dc2626' } : {}}
                  data-testid={`bulk-rm-mod-${m.id}`}
                ><Ban size={10} className="inline mr-0.5" /> {m.name}</button>
              );
            })}
          </div>
        </div>
      </div>
      <div className="flex gap-2 pt-3 border-t">
        <Button variant="outline" onClick={onClose} className="flex-1">Cancel</Button>
        <Button
          onClick={onApply}
          className="flex-1 text-white hover:opacity-90"
          style={{ background: theme.primary }}
          data-testid="bulk-apply"
        >Apply to {selectedCount}</Button>
      </div>
    </DialogContent>
  </Dialog>
);
