import React, { useState, useEffect } from 'react';
import { Plus, Edit, Trash2, List, ChevronDown } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { useTheme } from '../contexts/ThemeContext';
import { itemsSystemAPI } from '../services/api';
import { toast } from 'sonner';

export default function Modifiers() {
  const { theme } = useTheme();
  const [modifiers, setModifiers] = useState([]);
  const [showDialog, setShowDialog] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: '', type: 'list', mandatory: false, multiSelect: false, maxSelections: 1, options: [], printWithItem: true });
  const [newOption, setNewOption] = useState({ name: '', price: '' });

  useEffect(() => { fetchData(); }, []);
  const fetchData = async () => { try { const r = await itemsSystemAPI.getModifiers(); setModifiers(r.data); } catch {} };

  const openAdd = () => { setEditing(null); setForm({ name: '', type: 'list', mandatory: false, multiSelect: false, maxSelections: 1, options: [], printWithItem: true }); setShowDialog(true); };
  const openEdit = (m) => { setEditing(m); setForm({ name: m.name, type: m.type, mandatory: m.mandatory, multiSelect: m.multiSelect, maxSelections: m.maxSelections, options: m.options || [], printWithItem: m.printWithItem !== false }); setShowDialog(true); };

  const addOption = () => {
    if (!newOption.name) return;
    setForm({ ...form, options: [...form.options, { name: newOption.name, price: parseFloat(newOption.price) || 0 }] });
    setNewOption({ name: '', price: '' });
  };

  const handleSave = async () => {
    if (!form.name) { toast.error('Name required'); return; }
    try {
      if (editing) { await itemsSystemAPI.updateModifier(editing.id, form); toast.success('Updated'); }
      else { await itemsSystemAPI.createModifier(form); toast.success('Created'); }
      setShowDialog(false); fetchData();
    } catch { toast.error('Failed'); }
  };

  return (
    <div className="space-y-6" data-testid="modifiers-page">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold" style={{ color: theme.text }}>Modifiers</h1><p className="text-sm text-gray-500">Universal modifiers that print with items. Dropdown or list, mandatory or optional.</p></div>
        <Button style={{ backgroundColor: theme.primary }} onClick={openAdd} data-testid="add-modifier-btn"><Plus size={16} className="mr-1" /> New Modifier</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {modifiers.map(mod => (
          <Card key={mod.id} data-testid={`mod-${mod.id}`}>
            <CardContent className="p-5">
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-bold">{mod.name}</h3>
                <div className="flex gap-1"><Button variant="ghost" size="sm" onClick={() => openEdit(mod)}><Edit size={13} /></Button><Button variant="ghost" size="sm" className="text-red-500" onClick={async () => { await itemsSystemAPI.deleteModifier(mod.id); fetchData(); }}><Trash2 size={13} /></Button></div>
              </div>
              <div className="flex flex-wrap gap-1 mb-2">
                <Badge variant="outline" className="text-[10px]">{mod.type === 'dropdown' ? 'Dropdown' : 'List'}</Badge>
                {mod.mandatory && <Badge className="bg-red-100 text-red-700 text-[10px]">Required</Badge>}
                {mod.multiSelect && <Badge className="bg-blue-100 text-blue-700 text-[10px]">Multi (max {mod.maxSelections})</Badge>}
                {mod.printWithItem && <Badge className="bg-green-100 text-green-700 text-[10px]">Prints</Badge>}
              </div>
              <div className="space-y-1">
                {(mod.options || []).map((o, i) => (
                  <div key={i} className="flex justify-between text-sm py-0.5"><span className="text-gray-600">{o.name}</span>{o.price > 0 && <span className="text-gray-500">+${o.price.toFixed(2)}</span>}</div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
        {modifiers.length === 0 && <Card className="col-span-3 border-dashed"><CardContent className="py-12 text-center text-gray-400"><List size={40} className="mx-auto mb-3 opacity-30" /><p>No modifiers yet</p></CardContent></Card>}
      </div>

      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="max-w-md" data-testid="modifier-dialog">
          <DialogHeader><DialogTitle>{editing ? 'Edit Modifier' : 'New Modifier'}</DialogTitle></DialogHeader>
          <div className="space-y-3 py-2 max-h-[65vh] overflow-y-auto">
            <Input placeholder="Modifier name (e.g. Milk Type, Size)" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} data-testid="mod-name" />
            <select className="w-full p-2 border rounded-md text-sm" value={form.type} onChange={e => setForm({ ...form, type: e.target.value })} data-testid="mod-type">
              <option value="list">List (radio/checkboxes)</option><option value="dropdown">Dropdown</option>
            </select>
            <div className="grid grid-cols-2 gap-3">
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.mandatory} onChange={e => setForm({ ...form, mandatory: e.target.checked })} data-testid="mod-mandatory" /> Mandatory</label>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.multiSelect} onChange={e => setForm({ ...form, multiSelect: e.target.checked })} data-testid="mod-multi" /> Multi-select</label>
            </div>
            {form.multiSelect && <Input type="number" min={1} placeholder="Max selections" value={form.maxSelections} onChange={e => setForm({ ...form, maxSelections: parseInt(e.target.value) || 1 })} data-testid="mod-max" />}
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.printWithItem} onChange={e => setForm({ ...form, printWithItem: e.target.checked })} /> Print with main item on ticket</label>
            <div>
              <p className="text-sm font-medium mb-2">Options</p>
              {form.options.map((o, i) => (
                <div key={i} className="flex items-center gap-2 mb-1"><span className="flex-1 text-sm">{o.name}</span><span className="text-sm text-gray-500">{o.price > 0 ? `+$${o.price}` : 'Free'}</span><button className="text-red-400 text-xs" onClick={() => setForm({ ...form, options: form.options.filter((_, j) => j !== i) })}>&times;</button></div>
              ))}
              <div className="flex gap-2 mt-2">
                <Input placeholder="Option name" className="flex-1 h-8 text-sm" value={newOption.name} onChange={e => setNewOption({ ...newOption, name: e.target.value })} data-testid="option-name" />
                <Input type="number" step="0.01" placeholder="$" className="w-20 h-8 text-sm" value={newOption.price} onChange={e => setNewOption({ ...newOption, price: e.target.value })} />
                <Button size="sm" variant="outline" className="h-8" onClick={addOption} data-testid="add-option-btn"><Plus size={12} /></Button>
              </div>
            </div>
            <Button className="w-full" style={{ backgroundColor: theme.primary }} onClick={handleSave} data-testid="save-mod-btn">{editing ? 'Update' : 'Create'} Modifier</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
