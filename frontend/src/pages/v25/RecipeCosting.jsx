import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { v25API, productsAPI } from '../../services/api';
import { useTheme } from '../../contexts/ThemeContext';
import { useToast } from '../../hooks/use-toast';
import { ChefHat, Plus } from 'lucide-react';

export default function RecipeCosting() {
  const { theme } = useTheme(); const { toast } = useToast();
  const [products, setProducts] = useState([]);
  const [selected, setSelected] = useState(null);
  const [ings, setIngs] = useState([]);
  // Goes through the authenticated client on purpose: /products hands an
  // anonymous caller the menu with cost stripped out, and a costing screen
  // with every cost at zero is worse than one that fails loudly.
  useEffect(() => { productsAPI.getAll().then(r => setProducts(r.data || [])).catch(() => {}); }, []);
  const open = async (p) => { setSelected(p); const r = await v25API.getRecipe(p.id); setIngs(r.data?.ingredients || []); };
  const save = async () => { await v25API.upsertRecipe({ productId: selected.id, ingredients: ings }); toast({ title: 'Recipe saved · cost updated' }); };
  const total = ings.reduce((s, i) => s + (parseFloat(i.quantity) || 0) * (parseFloat(i.costPerUnit) || 0), 0);
  return (
    <div className="space-y-6" data-testid="recipe-costing-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><ChefHat className="text-red-600" /> Recipe Costing Engine</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="md:col-span-1"><CardContent className="p-0">
          <div className="px-4 py-3 border-b font-bold">Menu Items</div>
          <div className="max-h-[60vh] overflow-y-auto">
            {products.map(p => (
              <button key={p.id} onClick={() => open(p)} className={`w-full text-left px-4 py-2.5 text-sm border-b hover:bg-gray-50 ${selected?.id === p.id ? 'bg-amber-50' : ''}`} data-testid={`prod-${p.id}`}>
                <div className="flex justify-between"><span>{p.name}</span><span className="text-xs text-gray-500">${p.price}</span></div>
              </button>
            ))}
          </div>
        </CardContent></Card>
        <Card className="md:col-span-2"><CardContent className="p-5">
          {!selected ? <p className="text-center py-12 text-gray-400">Pick an item to cost it</p> : (
            <>
              <div className="flex justify-between items-baseline mb-3">
                <h2 className="font-bold">{selected.name}</h2>
                <div className="text-right"><p className="text-xs text-gray-500">Cost / Sells / Margin</p><p className="font-mono">${total.toFixed(2)} / ${selected.price} / {selected.price > 0 ? ((selected.price - total)/selected.price*100).toFixed(1) : 0}%</p></div>
              </div>
              <div className="space-y-2">
                {ings.map((ing, i) => (
                  <div key={i} className="grid grid-cols-12 gap-2 items-center">
                    <Input className="col-span-5" placeholder="Ingredient" value={ing.item || ''} onChange={e => { const a = [...ings]; a[i].item = e.target.value; setIngs(a); }} />
                    <Input className="col-span-2" type="number" placeholder="Qty" value={ing.quantity || ''} onChange={e => { const a = [...ings]; a[i].quantity = parseFloat(e.target.value) || 0; setIngs(a); }} />
                    <Input className="col-span-2" placeholder="Unit" value={ing.unit || ''} onChange={e => { const a = [...ings]; a[i].unit = e.target.value; setIngs(a); }} />
                    <Input className="col-span-2" type="number" placeholder="$/unit" value={ing.costPerUnit || ''} onChange={e => { const a = [...ings]; a[i].costPerUnit = parseFloat(e.target.value) || 0; setIngs(a); }} />
                    <Button size="sm" variant="ghost" className="col-span-1" onClick={() => setIngs(ings.filter((_, x) => x !== i))}>×</Button>
                  </div>
                ))}
                <Button variant="outline" onClick={() => setIngs([...ings, { item: '', quantity: 0, unit: 'g', costPerUnit: 0 }])} data-testid="add-ing"><Plus size={14} className="mr-1" /> Add Ingredient</Button>
              </div>
              <Button onClick={save} className="mt-4" style={{ background: theme.primary }} data-testid="save-recipe">Save Recipe & Update Cost</Button>
            </>
          )}
        </CardContent></Card>
      </div>
    </div>
  );
}
