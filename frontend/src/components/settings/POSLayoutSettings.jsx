import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import { useTheme } from '../../contexts/ThemeContext';
import { posLayoutAPI } from '../../services/api';
import { toast } from 'sonner';
import { PanelLeft, PanelRight, Check } from 'lucide-react';

const TILE_MIN_PX = { compact: 96, comfortable: 130, large: 168 };

const DEFAULTS = { cartPosition: 'right', tileSize: 'comfortable', quickActions: { hold: true, tabs: true } };

/**
 * Structured POS customization — not a drag-and-drop layout builder.
 *
 * A POS is touch/speed-critical: a freely-repositioned element is a place a
 * server can't find a button mid-rush, and a shrunk-to-fit tile is a place a
 * wet or gloved thumb misses the tap. So the three regions (category bar,
 * product grid, cart) stay structurally fixed — what's configurable is a
 * small, safe set of choices within them, each with a live preview built
 * from the same tokens (theme colors, tile-size scale) the real POS uses,
 * so what's previewed here is what actually renders there.
 */
export default function POSLayoutSettings() {
  const { theme } = useTheme();
  const [layout, setLayout] = useState(DEFAULTS);
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    posLayoutAPI.get().then(r => setLayout(r.data)).catch(() => {}).finally(() => setLoaded(true));
  }, []);

  const update = (patch) => setLayout(l => ({ ...l, ...patch }));
  const updateAction = (key, value) =>
    setLayout(l => ({ ...l, quickActions: { ...l.quickActions, [key]: value } }));

  const save = async () => {
    setSaving(true);
    try {
      const r = await posLayoutAPI.save(layout);
      setLayout(r.data);
      toast.success('POS layout saved — applies on every terminal next time it loads the till');
    } catch (e) { toast.error(e.response?.data?.detail || 'Could not save'); }
    setSaving(false);
  };

  const card = { backgroundColor: theme.cardBg || theme.background, color: theme.text };
  const tileMin = TILE_MIN_PX[layout.tileSize] || TILE_MIN_PX.comfortable;

  return (
    <div className="space-y-4" data-testid="pos-layout-settings">
      <Card style={card}>
        <CardContent className="p-6 space-y-6">
          <div>
            <h3 className="font-bold text-lg">POS layout</h3>
            <p className="text-sm opacity-70 mt-1">
              Not a drag-and-drop builder on purpose — the category bar, product grid and cart stay
              where staff already know to find them. What's configurable is what fits your venue:
              which side the cart sits on, how big the tiles are, and which quick actions show.
            </p>
          </div>

          {/* Cart position */}
          <div>
            <div className="text-sm font-semibold mb-2">Cart position</div>
            <div className="flex gap-2">
              {[
                { v: 'right', label: 'Right', Icon: PanelRight },
                { v: 'left', label: 'Left', Icon: PanelLeft },
              ].map(({ v, label, Icon }) => (
                <button key={v} onClick={() => update({ cartPosition: v })}
                  data-testid={`layout-cart-${v}`}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-lg border text-sm font-medium transition-colors"
                  style={layout.cartPosition === v
                    ? { borderColor: theme.primary, backgroundColor: `${theme.primary}15`, color: theme.primary }
                    : { borderColor: theme.border || '#e5e7eb' }}>
                  <Icon size={16} /> {label}
                  {layout.cartPosition === v && <Check size={14} className="ml-1" />}
                </button>
              ))}
            </div>
          </div>

          {/* Tile size */}
          <div>
            <div className="text-sm font-semibold mb-2">Tile size</div>
            <div className="flex gap-2">
              {['compact', 'comfortable', 'large'].map(v => (
                <button key={v} onClick={() => update({ tileSize: v })}
                  data-testid={`layout-tile-${v}`}
                  className="flex-1 px-3 py-2.5 rounded-lg border text-sm font-medium capitalize transition-colors"
                  style={layout.tileSize === v
                    ? { borderColor: theme.primary, backgroundColor: `${theme.primary}15`, color: theme.primary }
                    : { borderColor: theme.border || '#e5e7eb' }}>
                  {v}
                </button>
              ))}
            </div>
            <p className="text-xs opacity-60 mt-1.5">
              Compact fits more on screen; large gives bigger touch targets for busy counters or wet hands.
            </p>
          </div>

          {/* Quick actions */}
          <div>
            <div className="text-sm font-semibold mb-2">Cart quick actions</div>
            <div className="flex gap-4">
              {[
                { k: 'hold', label: 'Hold' },
                { k: 'tabs', label: 'Tabs' },
              ].map(({ k, label }) => (
                <label key={k} className="flex items-center gap-2 text-sm cursor-pointer">
                  <input type="checkbox" checked={!!layout.quickActions[k]}
                    onChange={e => updateAction(k, e.target.checked)}
                    className="w-4 h-4 accent-orange-500" data-testid={`layout-action-${k}`} />
                  {label}
                </label>
              ))}
            </div>
            <p className="text-xs opacity-60 mt-1.5">
              A pure counter-service venue that never parks an order can hide Hold to keep the cart
              simpler; a dine-in venue running tabs across the floor keeps both on.
            </p>
          </div>

          <Button onClick={save} disabled={saving || !loaded} data-testid="layout-save">
            {saving ? 'Saving…' : 'Save layout'}
          </Button>
        </CardContent>
      </Card>

      {/* Live preview — built from the same theme + tile-size tokens the
          real POS terminal reads, so this is a preview of the actual
          result, not an illustration of it. */}
      <Card style={card}>
        <CardContent className="p-6">
          <div className="text-sm font-semibold mb-3">Preview</div>
          <div className={`flex ${layout.cartPosition === 'left' ? 'flex-row-reverse' : 'flex-row'} gap-3 rounded-xl border overflow-hidden`}
               style={{ borderColor: theme.border || '#e5e7eb' }} data-testid="layout-preview">
            <div className="flex-1 p-3 space-y-2" style={{ backgroundColor: theme.background }}>
              <div className="flex gap-1.5">
                {['All', 'Mains', 'Drinks', 'Desserts'].map((c, i) => (
                  <div key={c} className="px-2.5 py-1 rounded-full text-[11px] font-semibold whitespace-nowrap"
                    style={i === 0 ? { backgroundColor: theme.primary, color: '#111827' }
                                  : { border: `1px solid ${theme.primary}40`, color: theme.text }}>
                    {c}
                  </div>
                ))}
              </div>
              <div className="grid gap-1.5" style={{ gridTemplateColumns: `repeat(auto-fill, minmax(${tileMin}px, 1fr))` }}>
                {['Steak', 'Salad', 'Soda', 'Cake'].map(name => (
                  <div key={name} className="rounded-lg border bg-white p-2"
                       style={{ borderColor: theme.border || '#e5e7eb', minHeight: tileMin * 0.6 }}>
                    <div className="text-[11px] font-medium truncate" style={{ color: '#111827' }}>{name}</div>
                    <div className="text-[10px] font-bold" style={{ color: theme.primary }}>$12.00</div>
                  </div>
                ))}
              </div>
            </div>
            <div className="w-32 shrink-0 p-3 space-y-2 border-l" style={{ borderColor: theme.border || '#e5e7eb', backgroundColor: theme.background }}>
              <div className="flex gap-1">
                {layout.quickActions.hold && (
                  <div className="text-[10px] font-semibold px-1.5 py-1 rounded border text-center flex-1"
                       style={{ borderColor: theme.border || '#e5e7eb' }}>Hold</div>
                )}
                {layout.quickActions.tabs && (
                  <div className="text-[10px] font-semibold px-1.5 py-1 rounded border text-center flex-1"
                       style={{ borderColor: theme.border || '#e5e7eb' }}>Tabs</div>
                )}
              </div>
              <div className="text-[10px] rounded p-1.5 bg-white border" style={{ borderColor: theme.border || '#e5e7eb', color: '#111827' }}>
                1x Steak
              </div>
              <div className="text-[11px] font-bold rounded-lg px-2 py-1.5 text-center"
                   style={{ backgroundColor: theme.primary, color: '#111827' }}>
                Pay
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
