import React, { useState, useEffect } from 'react';
import { Layout, Plus, Trash2, Save, Move } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { useTheme } from '../contexts/ThemeContext';
import { reservationFeaturesAPI, floorPlansAPI } from '../services/api';
import { toast } from 'sonner';

export default function TableLayout() {
  const { theme } = useTheme();
  const [tables, setTables] = useState([]);
  const [combos, setCombos] = useState([]);
  const [selected, setSelected] = useState([]);
  const [comboName, setComboName] = useState('');
  const [maxCovers, setMaxCovers] = useState('');

  useEffect(() => {
    floorPlansAPI.getAll().then(r => {
      const allTables = [];
      (r.data || []).forEach(fp => (fp.tables || []).forEach(t => allTables.push({ ...t, floorPlan: fp.name })));
      setTables(allTables);
    }).catch(() => {});
    reservationFeaturesAPI.getTableCombos().then(r => setCombos(r.data)).catch(() => {});
  }, []);

  const toggleSelect = (tableId, e) => {
    if (e?.shiftKey) {
      setSelected(prev => prev.includes(tableId) ? prev.filter(t => t !== tableId) : [...prev, tableId]);
    } else {
      setSelected(prev => prev.includes(tableId) ? prev.filter(t => t !== tableId) : [...prev, tableId]);
    }
  };

  const createCombo = async () => {
    if (selected.length < 2) { toast.error('Select at least 2 tables'); return; }
    try {
      await reservationFeaturesAPI.createTableCombo({ tableIds: selected, name: comboName || `Combo ${selected.join('+')}`, maxCovers: parseInt(maxCovers) || selected.length * 4 });
      toast.success('Combination created');
      setSelected([]); setComboName(''); setMaxCovers('');
      reservationFeaturesAPI.getTableCombos().then(r => setCombos(r.data)).catch(() => {});
    } catch { toast.error('Failed'); }
  };

  const deleteCombo = async (id) => {
    try { await reservationFeaturesAPI.deleteTableCombo(id); setCombos(combos.filter(c => c.id !== id)); toast.success('Deleted'); } catch {}
  };

  return (
    <div className="space-y-6" data-testid="table-layout-page">
      <div><h1 className="text-2xl font-bold" style={{ color: theme.text }}>Table Layout & Combinations</h1><p className="text-sm text-gray-500">Select tables to create combinations. Hold Shift to multi-select.</p></div>

      {/* Table Grid */}
      <Card><CardHeader><CardTitle className="text-sm">Tables — Click to select, Shift+Click for multi-select</CardTitle></CardHeader>
      <CardContent>
        <div className="grid grid-cols-6 md:grid-cols-8 lg:grid-cols-10 gap-3">
          {tables.map(t => {
            const isSelected = selected.includes(t.number?.toString() || t.id);
            const key = t.number?.toString() || t.id;
            return (
              <button key={key} onClick={(e) => toggleSelect(key, e)}
                className={`p-3 rounded-lg border-2 text-center transition-all cursor-pointer ${isSelected ? 'border-blue-500 bg-blue-50 shadow-md' : 'border-gray-200 hover:border-gray-400'}`}
                data-testid={`table-${key}`}>
                <p className="text-lg font-bold">{t.number || t.id}</p>
                <p className="text-[10px] text-gray-500">{t.seats || t.capacity || 4} seats</p>
              </button>
            );
          })}
          {tables.length === 0 && <p className="col-span-full text-gray-400 text-sm text-center py-8">No tables found. Add tables via Floor Plan first.</p>}
        </div>
        {selected.length > 0 && (
          <div className="flex items-center gap-3 mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
            <Badge className="bg-blue-600 text-white">{selected.length} selected</Badge>
            <Input placeholder="Combination name" className="flex-1 h-8 text-sm" value={comboName} onChange={e => setComboName(e.target.value)} data-testid="combo-name" />
            <Input type="number" placeholder="Max covers" className="w-28 h-8 text-sm" value={maxCovers} onChange={e => setMaxCovers(e.target.value)} data-testid="combo-covers" />
            <Button size="sm" style={{ backgroundColor: theme.primary }} onClick={createCombo} data-testid="create-combo-btn"><Plus size={14} className="mr-1" /> Add Combination</Button>
          </div>
        )}
      </CardContent></Card>

      {/* Existing Combinations */}
      <Card><CardHeader><CardTitle className="text-sm">Existing Combinations</CardTitle></CardHeader>
      <CardContent className="space-y-2">
        {combos.map(c => (
          <div key={c.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg" data-testid={`combo-${c.id}`}>
            <div>
              <p className="font-medium text-sm">{c.name}</p>
              <p className="text-xs text-gray-500">Tables: {(c.tableIds || []).join(', ')} | Max {c.maxCovers} covers</p>
            </div>
            <Button variant="ghost" size="sm" className="text-red-500" onClick={() => deleteCombo(c.id)}><Trash2 size={14} /></Button>
          </div>
        ))}
        {combos.length === 0 && <p className="text-gray-400 text-sm text-center py-4">No combinations yet</p>}
      </CardContent></Card>
    </div>
  );
}
