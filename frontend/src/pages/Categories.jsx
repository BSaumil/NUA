import React, { useState, useEffect } from 'react';
import {
  Plus, Edit, Trash2, GripVertical,
  // Icon options users can choose from
  Coffee, UtensilsCrossed, Beef, Cake, Soup, Croissant, Wine, Pizza,
  IceCream, Salad, Sandwich, Cookie, EggFried, Fish, Beer, GlassWater,
  Apple, Carrot, Drumstick, Tag, Sparkles
} from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { useTheme } from '../contexts/ThemeContext';
import { itemsSystemAPI } from '../services/api';
import { toast } from 'sonner';

// Whitelist of icons the owner can pick (kept lean so bundle stays small).
export const CATEGORY_ICON_MAP = {
  Coffee, UtensilsCrossed, Beef, Cake, Soup, Croissant, Wine, Pizza,
  IceCream, Salad, Sandwich, Cookie, EggFried, Fish, Beer, GlassWater,
  Apple, Carrot, Drumstick, Tag, Sparkles,
};

export function CategoryIcon({ name, size = 18, className = '', style = {} }) {
  const Icon = CATEGORY_ICON_MAP[name] || Tag;
  return <Icon size={size} className={className} style={style} />;
}

const COLOR_SWATCHES = [
  '#92400e', '#dc2626', '#16a34a', '#db2777', '#ea580c',
  '#0ea5e9', '#8b5cf6', '#f59e0b', '#10b981', '#ef4444',
  '#6366f1', '#14b8a6', '#a855f7', '#84cc16', '#475569',
];

const BLANK = { name: '', sortOrder: 0, active: true, icon: 'Tag', color: '#6366f1' };

export default function Categories() {
  const { theme } = useTheme();
  const [categories, setCategories] = useState([]);
  const [showDialog, setShowDialog] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(BLANK);

  useEffect(() => { fetchData(); }, []);
  const fetchData = async () => { try { const r = await itemsSystemAPI.getCategories(); setCategories(r.data); } catch {} };

  const openAdd = () => { setEditing(null); setForm({ ...BLANK, sortOrder: categories.length }); setShowDialog(true); };
  const openEdit = (c) => {
    setEditing(c);
    setForm({ name: c.name, sortOrder: c.sortOrder, active: c.active, icon: c.icon || 'Tag', color: c.color || '#6366f1' });
    setShowDialog(true);
  };

  const handleSave = async () => {
    if (!form.name) { toast.error('Name required'); return; }
    try {
      if (editing) { await itemsSystemAPI.updateCategory(editing.id, form); toast.success('Category updated'); }
      else { await itemsSystemAPI.createCategory(form); toast.success('Category created'); }
      setShowDialog(false); fetchData();
    } catch { toast.error('Failed'); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this category? Items in it will become uncategorized.')) return;
    try { await itemsSystemAPI.deleteCategory(id); toast.success('Deleted'); fetchData(); } catch {}
  };

  return (
    <div className="space-y-6" data-testid="categories-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: theme.text }}>Categories</h1>
          <p className="text-sm text-gray-500">Create, reassign, customise icon + colour, or remove categories</p>
        </div>
        <Button style={{ backgroundColor: theme.primary }} onClick={openAdd} data-testid="add-category-btn">
          <Plus size={16} className="mr-1" /> New Category
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {categories.map((cat) => (
          <Card key={cat.id} data-testid={`cat-${cat.id}`} className="hover:shadow-md transition-shadow">
            <CardContent className="p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <GripVertical size={16} className="text-gray-300" />
                <div className="w-10 h-10 rounded-xl flex items-center justify-center text-white shadow-sm"
                  style={{ background: cat.color || '#6366f1' }}>
                  <CategoryIcon name={cat.icon} size={20} />
                </div>
                <div>
                  <h3 className="font-medium">{cat.name}</h3>
                  <p className="text-xs text-gray-400">Sort {cat.sortOrder} · {cat.icon || 'Tag'}</p>
                </div>
                <Badge className={cat.active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}>
                  {cat.active ? 'Active' : 'Inactive'}
                </Badge>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => openEdit(cat)} data-testid={`edit-cat-${cat.id}`}><Edit size={14} /></Button>
                <Button variant="outline" size="sm" className="text-red-500" onClick={() => handleDelete(cat.id)}><Trash2 size={14} /></Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="max-w-md" data-testid="category-dialog">
          <DialogHeader><DialogTitle>{editing ? 'Edit Category' : 'New Category'}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="flex items-center gap-3 p-3 rounded-lg border bg-gray-50">
              <div className="w-12 h-12 rounded-xl flex items-center justify-center text-white shadow"
                style={{ background: form.color }}>
                <CategoryIcon name={form.icon} size={22} />
              </div>
              <div className="flex-1">
                <p className="text-xs uppercase text-gray-500 font-bold tracking-widest">Preview</p>
                <p className="font-medium">{form.name || 'Category name'}</p>
              </div>
            </div>
            <div>
              <label className="text-xs uppercase text-gray-500 font-bold">Name</label>
              <Input placeholder="e.g. Coffee" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} data-testid="cat-name-input" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs uppercase text-gray-500 font-bold">Sort order</label>
                <Input type="number" value={form.sortOrder} onChange={e => setForm({ ...form, sortOrder: parseInt(e.target.value) || 0 })} />
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={form.active} onChange={e => setForm({ ...form, active: e.target.checked })} />
                  Active
                </label>
              </div>
            </div>
            <div>
              <label className="text-xs uppercase text-gray-500 font-bold">Icon</label>
              <div className="grid grid-cols-7 gap-2 mt-1" data-testid="cat-icon-grid">
                {Object.keys(CATEGORY_ICON_MAP).map(key => (
                  <button key={key} type="button"
                    onClick={() => setForm({ ...form, icon: key })}
                    className={`w-10 h-10 rounded-lg border flex items-center justify-center transition ${form.icon === key ? 'border-2 shadow-sm' : 'border-gray-200 hover:border-gray-400'}`}
                    style={form.icon === key ? { borderColor: form.color, background: `${form.color}15` } : {}}
                    title={key}
                    data-testid={`cat-icon-${key}`}>
                    <CategoryIcon name={key} size={18} style={form.icon === key ? { color: form.color } : {}} />
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-xs uppercase text-gray-500 font-bold">Colour</label>
              <div className="flex gap-2 flex-wrap mt-1" data-testid="cat-color-row">
                {COLOR_SWATCHES.map(c => (
                  <button key={c} type="button"
                    onClick={() => setForm({ ...form, color: c })}
                    className={`w-8 h-8 rounded-full border-2 transition ${form.color === c ? 'border-gray-900 scale-110' : 'border-white shadow'}`}
                    style={{ background: c }}
                    data-testid={`cat-color-${c.replace('#','')}`} />
                ))}
                <input type="color" value={form.color}
                  onChange={e => setForm({ ...form, color: e.target.value })}
                  className="w-8 h-8 rounded-full border-0 cursor-pointer" />
              </div>
            </div>
            <Button className="w-full" style={{ backgroundColor: theme.primary }} onClick={handleSave} data-testid="save-cat-btn">
              {editing ? 'Update' : 'Create'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
