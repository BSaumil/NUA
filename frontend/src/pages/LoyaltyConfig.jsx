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
  const [cfg, setCfg] = useState({
    earnRate: 1, redeemRate: 0.01, minRedeem: 50, categoryMultipliers: {}, active: true,
    pointsExpiryDays: 0, expiryWarnDays: 7, downgradeEnabled: false, downgradeGraceDays: 30,
  });
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
        <CardContent className="p-6 space-y-4">
          <h2 className="font-bold text-sm uppercase tracking-wider text-gray-500">Expiry & Tier Downgrade</h2>
          <p className="text-xs text-gray-500">Both run automatically the next time the Ash agent tick executes — Settings &gt; Ash &gt; Run Tick, or the "agent_tick" voice command.</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs uppercase tracking-wider text-gray-500">Points expire after (days of inactivity)</label>
              <Input type="number" min="0" value={cfg.pointsExpiryDays}
                onChange={e => setCfg({ ...cfg, pointsExpiryDays: parseInt(e.target.value) || 0 })}
                data-testid="points-expiry-days" />
              <p className="text-[11px] text-gray-400 mt-1">0 = points never expire. Otherwise, a customer's balance is zeroed once this many days pass with no earn or redeem activity.</p>
              {cfg.pointsExpiryDays > 0 && (
                <div className="mt-2">
                  <label className="text-xs uppercase tracking-wider text-gray-500">Warn this many days before expiry</label>
                  <Input type="number" min="1" value={cfg.expiryWarnDays}
                    onChange={e => setCfg({ ...cfg, expiryWarnDays: parseInt(e.target.value) || 1 })}
                    data-testid="expiry-warn-days" />
                  <p className="text-[11px] text-gray-400 mt-1">Sends a one-time email/SMS ("your points expire in N days") to customers with an email or phone on file, instead of letting the balance vanish with no warning.</p>
                </div>
              )}
            </div>
            <div>
              <label className="flex items-center gap-2 text-sm mb-1">
                <input type="checkbox" checked={cfg.downgradeEnabled}
                  onChange={e => setCfg({ ...cfg, downgradeEnabled: e.target.checked })}
                  data-testid="downgrade-enabled" /> Allow tier downgrades
              </label>
              <Input type="number" min="1" value={cfg.downgradeGraceDays} disabled={!cfg.downgradeEnabled}
                onChange={e => setCfg({ ...cfg, downgradeGraceDays: parseInt(e.target.value) || 1 })}
                data-testid="downgrade-grace-days" placeholder="Grace period (days)" />
              <p className="text-[11px] text-gray-400 mt-1">Tiers only ever went up before. When enabled, a customer whose points balance falls below their tier's threshold is downgraded after this many days below it — not immediately.</p>
            </div>
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
