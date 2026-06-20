import React from 'react';
import { Edit, Trash2, CheckSquare, Square, TrendingUp, TrendingDown } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Card, CardContent } from '../ui/card';

/**
 * Renders the catalog as either a card grid or a data table (same data).
 * Inline-edit controls for name/price/stock fields and quick 86 toggles are
 * built in. Pure presentational — all mutations flow through callbacks.
 */
export const ProductTable = ({
  theme,
  layoutMode,
  filteredProducts,
  insights,
  selected,
  toggleSelect,
  allVisibleSelected,
  selectAllVisible,
  clearSelection,
  inlineEditCell,
  inlineValue,
  setInlineValue,
  setInlineEditCell,
  startInlineEdit,
  commitInlineEdit,
  toggleEightySix,
  openEditProduct,
  deleteProduct,
}) => {
  if (layoutMode === 'grid') {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {filteredProducts.map(product => {
          const ins = insights[product.id] || {};
          const sold = ins.weeklyUnitsSold || 0;
          const margin = ins.marginPct || 0;
          const marginTone = margin >= 60 ? 'bg-emerald-100 text-emerald-800 border-emerald-200'
            : margin >= 40 ? 'bg-amber-100 text-amber-800 border-amber-200'
            : 'bg-red-100 text-red-800 border-red-200';
          const isInline = (field) => inlineEditCell?.id === product.id && inlineEditCell?.field === field;
          return (
            <Card
              key={product.id}
              className={`hover:shadow-lg transition-shadow ${product.eightySixed ? 'opacity-60' : ''} ${selected.has(product.id) ? 'ring-2' : ''}`}
              style={selected.has(product.id) ? { boxShadow: `0 0 0 2px ${theme.primary}` } : {}}
              data-testid={`product-card-${product.id}`}
            >
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
                  <img
                    src={product.image || 'https://placehold.co/300x200/e5e7eb/9ca3af?text=NUA'}
                    alt={product.name}
                    className="w-full h-40 object-cover rounded-lg mb-4"
                  />
                  <span
                    className={`absolute top-1 right-1 text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded border ${marginTone}`}
                    data-testid={`margin-badge-${product.id}`}
                  >
                    {margin.toFixed(0)}% margin
                  </span>
                </div>
                {isInline('name') ? (
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
                  >{product.name}</h3>
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
                    {isInline('price') ? (
                      <Input
                        autoFocus
                        type="number"
                        step="0.01"
                        value={inlineValue}
                        onChange={e => setInlineValue(e.target.value)}
                        onBlur={commitInlineEdit}
                        onKeyDown={e => { if (e.key === 'Enter') commitInlineEdit(); if (e.key === 'Escape') setInlineEditCell(null); }}
                        className="text-2xl font-bold h-10 w-24"
                        data-testid={`inline-price-${product.id}`}
                      />
                    ) : (
                      <p
                        className="text-2xl font-bold cursor-text hover:bg-amber-50 rounded px-1"
                        style={{ color: theme.primary }}
                        onClick={() => startInlineEdit(product.id, 'price', product.price)}
                        title="Click to edit"
                        data-testid={`price-${product.id}`}
                      >${Number(product.price).toFixed(2)}</p>
                    )}
                    <p className="text-xs text-gray-500">Cost: ${Number(product.cost).toFixed(2)}</p>
                  </div>
                  <div className="text-right">
                    {isInline('stock') ? (
                      <Input
                        autoFocus
                        type="number"
                        value={inlineValue}
                        onChange={e => setInlineValue(e.target.value)}
                        onBlur={commitInlineEdit}
                        onKeyDown={e => { if (e.key === 'Enter') commitInlineEdit(); if (e.key === 'Escape') setInlineEditCell(null); }}
                        className="h-8 w-20"
                        data-testid={`inline-stock-${product.id}`}
                      />
                    ) : (
                      <p
                        className="text-sm font-medium cursor-text hover:bg-amber-50 rounded px-1"
                        onClick={() => startInlineEdit(product.id, 'stock', product.stock)}
                        title="Click to edit"
                        data-testid={`stock-${product.id}`}
                      >Stock: {product.stock}</p>
                    )}
                    <p className="text-xs text-gray-500">GST: {product.gstRate}%</p>
                  </div>
                </div>
                <div
                  className="mt-3 flex items-center justify-between px-2.5 py-1.5 rounded-md"
                  style={{ background: `${theme.primary}10`, color: theme.primary }}
                  data-testid={`weekly-sales-${product.id}`}
                >
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
        {filteredProducts.length === 0 && (
          <p className="col-span-full text-center text-gray-400 py-12">No products found. Add your first product above.</p>
        )}
      </div>
    );
  }

  // TABLE view
  return (
    <Card>
      <CardContent className="p-0 overflow-x-auto">
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
            ) : filteredProducts.map(product => {
              const isInline = (field) => inlineEditCell?.id === product.id && inlineEditCell?.field === field;
              return (
                <tr
                  key={product.id}
                  className={`border-t hover:bg-amber-50/30 ${selected.has(product.id) ? 'bg-amber-50/60' : ''} ${product.eightySixed ? 'opacity-60' : ''}`}
                  data-testid={`row-${product.id}`}
                >
                  <td className="px-3 py-2">
                    <button onClick={() => toggleSelect(product.id)} data-testid={`row-select-${product.id}`}>
                      {selected.has(product.id) ? <CheckSquare size={14} style={{ color: theme.primary }} /> : <Square size={14} className="text-gray-400" />}
                    </button>
                  </td>
                  <td className="px-3 py-2">
                    <img
                      src={product.image || 'https://placehold.co/40x40/e5e7eb/9ca3af?text=NUA'}
                      alt={product.name}
                      className="w-10 h-10 rounded object-cover"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <p className="font-medium">{product.name}</p>
                    <p className="text-xs text-gray-500 font-mono">{product.sku}</p>
                  </td>
                  <td className="px-3 py-2 text-xs text-gray-700">{product.category}</td>
                  <td className="px-3 py-2 text-right">
                    {isInline('price') ? (
                      <Input
                        autoFocus
                        type="number"
                        step="0.01"
                        value={inlineValue}
                        onChange={e => setInlineValue(e.target.value)}
                        onBlur={commitInlineEdit}
                        onKeyDown={e => { if (e.key === 'Enter') commitInlineEdit(); if (e.key === 'Escape') setInlineEditCell(null); }}
                        className="h-8 w-24 ml-auto"
                      />
                    ) : (
                      <button
                        onClick={() => startInlineEdit(product.id, 'price', product.price)}
                        className="font-mono hover:bg-amber-100 rounded px-1"
                        title="Click to edit"
                        data-testid={`row-price-${product.id}`}
                      >${Number(product.price).toFixed(2)}</button>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right text-xs text-gray-600">${Number(product.cost).toFixed(2)}</td>
                  <td className="px-3 py-2 text-right">
                    {isInline('stock') ? (
                      <Input
                        autoFocus
                        type="number"
                        value={inlineValue}
                        onChange={e => setInlineValue(e.target.value)}
                        onBlur={commitInlineEdit}
                        onKeyDown={e => { if (e.key === 'Enter') commitInlineEdit(); if (e.key === 'Escape') setInlineEditCell(null); }}
                        className="h-8 w-20 ml-auto"
                      />
                    ) : (
                      <button
                        onClick={() => startInlineEdit(product.id, 'stock', product.stock)}
                        className="hover:bg-amber-100 rounded px-1"
                        title="Click to edit"
                        data-testid={`row-stock-${product.id}`}
                      >{product.stock}</button>
                    )}
                  </td>
                  <td className="px-3 py-2 text-center text-xs">
                    {(product.modifierIds || []).length > 0 ? (
                      <span className="font-medium" style={{ color: theme.secondary }}>{product.modifierIds.length}</span>
                    ) : <span className="text-gray-300">—</span>}
                  </td>
                  <td className="px-3 py-2 text-center">
                    <button
                      onClick={() => toggleEightySix(product)}
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${product.eightySixed ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-700'}`}
                      data-testid={`row-86-${product.id}`}
                    >{product.eightySixed ? '86' : 'OK'}</button>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <div className="flex gap-1 justify-end">
                      <Button variant="ghost" size="sm" onClick={() => openEditProduct(product)} data-testid={`row-edit-${product.id}`}><Edit size={12} /></Button>
                      <Button variant="ghost" size="sm" className="text-red-500" onClick={() => deleteProduct(product.id)} data-testid={`row-del-${product.id}`}><Trash2 size={12} /></Button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
};
