import React, { useState, useEffect } from 'react';
import { Plus, Edit, Trash2, Save, GripVertical } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { useTheme } from '../contexts/ThemeContext';
import { itemsSystemAPI } from '../services/api';
import { toast } from 'sonner';

export default function Categories() {
  const { theme } = useTheme();
  const [categories, setCategories] = useState([]);
  const [showDialog, setShowDialog] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: '', sortOrder: 0, active: true });

  useEffect(() => { fetchData(); }, []);
  const fetchData = async () => { try { const r = await itemsSystemAPI.getCategories(); setCategories(r.data); } catch {} };

  const openAdd = () => { setEditing(null); setForm({ name: '', sortOrder: categories.length, active: true }); setShowDialog(true); };
  const openEdit = (c) => { setEditing(c); setForm({ name: c.name, sortOrder: c.sortOrder, active: c.active }); setShowDialog(true); };

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
        <div><h1 className="text-2xl font-bold" style={{ color: theme.text }}>Categories</h1><p className="text-sm text-gray-500">Create, reassign, or remove categories</p></div>
        <Button style={{ backgroundColor: theme.primary }} onClick={openAdd} data-testid="add-category-btn"><Plus size={16} className="mr-1" /> New Category</Button>
      </div>

      <div className="space-y-2">
        {categories.map((cat, i) => (
          <Card key={cat.id} data-testid={`cat-${cat.id}`}>
            <CardContent className="p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <GripVertical size={16} className="text-gray-300" />
                <div>
                  <h3 className="font-medium">{cat.name}</h3>
                  <p className="text-xs text-gray-400">Sort: {cat.sortOrder}</p>
                </div>
                <Badge className={cat.active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}>{cat.active ? 'Active' : 'Inactive'}</Badge>
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
        <DialogContent className="max-w-sm" data-testid="category-dialog">
          <DialogHeader><DialogTitle>{editing ? 'Edit Category' : 'New Category'}</DialogTitle></DialogHeader>
          <div className="space-y-3 py-2">
            <Input placeholder="Category name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} data-testid="cat-name-input" />
            <Input type="number" placeholder="Sort order" value={form.sortOrder} onChange={e => setForm({ ...form, sortOrder: parseInt(e.target.value) || 0 })} />
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.active} onChange={e => setForm({ ...form, active: e.target.checked })} /> Active</label>
            <Button className="w-full" style={{ backgroundColor: theme.primary }} onClick={handleSave} data-testid="save-cat-btn">{editing ? 'Update' : 'Create'}</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
