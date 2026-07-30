import React from 'react';
import { ImageIcon, Ban, ArrowDownToLine } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';

/**
 * Bulk-edit dialog for the Products page. Price/cost/GST/category/status are
 * edited per-row — each selected product keeps its own value, since a single
 * shared number rarely makes sense across items with different costs. The
 * "fill all" buttons are a convenience to copy one row's value down to every
 * row, not a separate all-at-once apply — the owner can still tweak any row
 * afterward. Modifiers and image stay genuinely bulk (same modifier/photo
 * assigned to every selected item), applied via a single shared patch.
 */
export const BulkEditDialog = ({
  open, onClose,
  theme,
  selectedCount,
  bulkPatch, setBulkPatch,
  bulkRows, updateBulkRow, fillBulkRows,
  categories, modifiers,
  onApply,
  onOpenImageLibrary,
}) => (
  <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
    <DialogContent className="max-w-3xl" data-testid="bulk-edit-dialog">
      <DialogHeader>
        <DialogTitle>Bulk Edit · {selectedCount} product{selectedCount !== 1 ? 's' : ''}</DialogTitle>
      </DialogHeader>
      <p className="text-xs text-gray-500 -mt-2 mb-1">
        Each item below keeps its own price, cost, GST and status — edit a row directly, or use
        <ArrowDownToLine size={11} className="inline mx-0.5 -mt-0.5" /> to copy that row's value down to every item, then adjust any row you need to.
      </p>
      <div className="border rounded-lg overflow-x-auto max-h-[40vh]">
        <table className="w-full text-xs">
          <thead className="bg-gray-50 sticky top-0">
            <tr>
              <th className="px-2 py-2 text-left">Item</th>
              <th className="px-2 py-2 text-left">Category</th>
              <th className="px-2 py-2 text-right">Price $</th>
              <th className="px-2 py-2 text-right">Cost $</th>
              <th className="px-2 py-2 text-right">GST %</th>
              <th className="px-2 py-2 text-center">Status</th>
            </tr>
          </thead>
          <tbody>
            {bulkRows.map((row, i) => (
              <tr key={row.id} className="border-t" data-testid={`bulk-row-${row.id}`}>
                <td className="px-2 py-1.5 max-w-[140px] truncate font-medium" title={row.name}>{row.name}</td>
                <td className="px-2 py-1.5">
                  <div className="flex items-center gap-1">
                    <select
                      className="w-full p-1 border rounded text-xs"
                      value={row.categoryId}
                      onChange={e => updateBulkRow(row.id, 'categoryId', e.target.value)}
                      data-testid={`bulk-row-category-${row.id}`}
                    >
                      <option value="">{row.category || '—'}</option>
                      {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                    </select>
                    {i === 0 && categories.length > 0 && (
                      <button type="button" title="Fill down" onClick={() => fillBulkRows('categoryId', row.categoryId)} className="text-gray-400 hover:text-gray-700" data-testid="fill-category"><ArrowDownToLine size={13} /></button>
                    )}
                  </div>
                </td>
                <td className="px-2 py-1.5">
                  <div className="flex items-center gap-1 justify-end">
                    <Input type="number" step="0.01" value={row.price}
                      onChange={e => updateBulkRow(row.id, 'price', e.target.value)}
                      className="h-7 w-20 text-xs text-right" data-testid={`bulk-row-price-${row.id}`} />
                    {i === 0 && (
                      <button type="button" title="Fill down" onClick={() => fillBulkRows('price', row.price)} className="text-gray-400 hover:text-gray-700" data-testid="fill-price"><ArrowDownToLine size={13} /></button>
                    )}
                  </div>
                </td>
                <td className="px-2 py-1.5">
                  <div className="flex items-center gap-1 justify-end">
                    <Input type="number" step="0.01" value={row.cost}
                      onChange={e => updateBulkRow(row.id, 'cost', e.target.value)}
                      className="h-7 w-20 text-xs text-right" data-testid={`bulk-row-cost-${row.id}`} />
                    {i === 0 && (
                      <button type="button" title="Fill down" onClick={() => fillBulkRows('cost', row.cost)} className="text-gray-400 hover:text-gray-700" data-testid="fill-cost"><ArrowDownToLine size={13} /></button>
                    )}
                  </div>
                </td>
                <td className="px-2 py-1.5">
                  <div className="flex items-center gap-1 justify-end">
                    <Input type="number" step="0.1" value={row.gstRate}
                      onChange={e => updateBulkRow(row.id, 'gstRate', e.target.value)}
                      className="h-7 w-16 text-xs text-right" data-testid={`bulk-row-gst-${row.id}`} />
                    {i === 0 && (
                      <button type="button" title="Fill down" onClick={() => fillBulkRows('gstRate', row.gstRate)} className="text-gray-400 hover:text-gray-700" data-testid="fill-gst"><ArrowDownToLine size={13} /></button>
                    )}
                  </div>
                </td>
                <td className="px-2 py-1.5 text-center">
                  <button
                    type="button"
                    onClick={() => updateBulkRow(row.id, 'eightySixed', !row.eightySixed)}
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${row.eightySixed ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-700'}`}
                    data-testid={`bulk-row-status-${row.id}`}
                  >{row.eightySixed ? '86' : 'OK'}</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="space-y-3 max-h-[24vh] overflow-y-auto pr-1 border-t pt-3">
        <p className="text-xs uppercase text-gray-500 font-semibold">Apply to all {selectedCount} selected (modifiers &amp; image)</p>
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
        >Save Changes</Button>
      </div>
    </DialogContent>
  </Dialog>
);
