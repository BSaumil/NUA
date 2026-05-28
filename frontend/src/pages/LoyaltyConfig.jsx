import React, { useState, useEffect } from 'react';
import { Award, Plus, Trash2, Save, Sparkles } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { useTheme } from '../contexts/ThemeContext';
import { loyaltyEngineAPI } from '../services/api';
import { toast } from 'sonner';

export default function LoyaltyConfig() {
  const { theme } = useTheme();
  const [cfg, setCfg] = useState({ earnRate: 1, redeemRate: 0.01, minRedeem: 50, categoryMultipliers: {}, active: true });
  const [newCat, setNewCat] = useState('');
  const [newMult, setNewMult] = useState('');

  useEffect(() => { loyaltyEngineAPI.getConfig().then(r => setCfg(c => ({ ...c, ...(r.data || {}) }))); }, []);

  const save = async () => {
    try { await loyaltyEngineAPI.updateConfig(cfg); toast.success('Loyalty config saved'); }
    catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };
  const addMult = () => {
    const m = parseFloat(newMult);
    if (!newCat.trim() || !m || m < 0) { toast.error('Category + valid multiplier required'); return; }
    setCfg(c => ({ ...c, categoryMultipliers: { ...c.categoryMultipliers, [newCat.trim()]: m } }));
    setNewCat(''); setNewMult('');
  };
  const removeMult = (cat) => setCfg(c => { const m = { ...c.categoryMultipliers }; delete m[cat]; return { ...c, categoryMultipliers: m }; });

  return (
    <div className="space-y-6" data-testid="loyalty-config-page">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Award size={22} /> Loyalty Configuration</h1>
        <p className="text-sm text-gray-500">Set how points are earned and redeemed. Per-category multipliers reward strategic items.</p>
      </div>

      <Card>
        <CardContent className="p-6 space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label className="text-xs uppercase tracking-wider text-gray-500">Earn rate (pts / $1)</label>
              <Input type="number" step="0.1" value={cfg.earnRate} onChange={e => setCfg({ ...cfg, earnRate: parseFloat(e.target.value) || 0 })} data-testid="earn-rate" />
            </div>
            <div>
              <label className="text-xs uppercase tracking-wider text-gray-500">Redeem value ($ / pt)</label>
              <Input type="number" step="0.01" value={cfg.redeemRate} onChange={e => setCfg({ ...cfg, redeemRate: parseFloat(e.target.value) || 0 })} data-testid="redeem-rate" />
            </div>
            <div>
              <label className="text-xs uppercase tracking-wider text-gray-500">Minimum redeem (pts)</label>
              <Input type="number" value={cfg.minRedeem} onChange={e => setCfg({ ...cfg, minRedeem: parseInt(e.target.value) || 0 })} data-testid="min-redeem" />
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={cfg.active} onChange={e => setCfg({ ...cfg, active: e.target.checked })} data-testid="loyalty-active" /> Program active
              </label>
            </div>
          </div>
          <div className="bg-blue-50 p-3 rounded text-xs text-blue-700 flex items-start gap-2">
            <Sparkles size={14} className="mt-0.5" />
            <span>Default: $1 spent = 1 point · 1 point = ¢1 face value · min {cfg.minRedeem} pts to redeem. Owner-configurable category multipliers below boost earnings for strategic items.</span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-6">
          <h2 className="font-bold text-sm uppercase tracking-wider text-gray-500 mb-3">Category Multipliers</h2>
          <p className="text-xs text-gray-500 mb-4">A multiplier of 2x means customers earn double points for items in that category.</p>
          <div className="space-y-2 mb-4">
            {Object.entries(cfg.categoryMultipliers || {}).map(([cat, mult]) => (
              <div key={cat} className="flex items-center justify-between p-2 border rounded-lg" data-testid={`mult-${cat}`}>
                <div className="flex items-center gap-2">
                  <Badge style={{ backgroundColor: `${theme.primary}15`, color: theme.primary }}>{cat}</Badge>
                  <span className="text-sm">earn <strong>{mult}x</strong> base points</span>
                </div>
                <Button size="sm" variant="ghost" className="text-red-500" onClick={() => removeMult(cat)} data-testid={`remove-mult-${cat}`}><Trash2 size={13} /></Button>
              </div>
            ))}
            {Object.keys(cfg.categoryMultipliers || {}).length === 0 && <p className="text-xs text-gray-400 text-center py-4">No multipliers — all categories earn at base rate.</p>}
          </div>
          <div className="flex gap-2">
            <Input placeholder="Category name (e.g. Coffee)" value={newCat} onChange={e => setNewCat(e.target.value)} data-testid="new-cat" />
            <Input type="number" step="0.1" placeholder="Multiplier (e.g. 2)" value={newMult} onChange={e => setNewMult(e.target.value)} className="w-40" data-testid="new-mult" />
            <Button variant="outline" onClick={addMult} data-testid="add-mult-btn"><Plus size={14} className="mr-1" /> Add</Button>
          </div>
        </CardContent>
      </Card>

      <Button className="w-full sm:w-auto" style={{ backgroundColor: theme.primary }} onClick={save} data-testid="save-loyalty-cfg"><Save size={16} className="mr-2" /> Save Configuration</Button>
    </div>
  );
}
