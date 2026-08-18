import React, { useState, useRef } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { useTheme } from '../../contexts/ThemeContext';
import { useNavigate } from 'react-router-dom';
import { reservationsAPI, reservationsAIAPI } from '../../services/api';
import { toast } from 'sonner';
import {
  Sparkles, Users, MapPin, Check, RefreshCw, LayoutGrid,
  ArrowLeft, Star, AlertCircle, Minus, Plus, Armchair,
} from 'lucide-react';

const TABLE_STATUS_STYLE = {
  available: { label: 'Available now', color: '#10B981', bg: '#ECFDF5' },
  cleaning: { label: 'Being cleared', color: '#F59E0B', bg: '#FFFBEB' },
};

const PARTY_QUICK_PICKS = [1, 2, 3, 4, 5, 6, 8];

export default function WalkInAISeatDialog({ open, onClose, onSeated }) {
  const { theme, darkMode } = useTheme();
  const navigate = useNavigate();

  const [step, setStep] = useState('input'); // input | recommend | notConfigured
  const [partySize, setPartySize] = useState(2);
  const [guestName, setGuestName] = useState('');
  const [guestMatches, setGuestMatches] = useState([]);
  const [guestSearchOpen, setGuestSearchOpen] = useState(false);
  const [selectedGuest, setSelectedGuest] = useState(null);
  const searchTimer = useRef(null);

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null); // { assigned, recommended, alternatives, guest, reason }
  const [chosenTable, setChosenTable] = useState(null);
  const [showAlternatives, setShowAlternatives] = useState(false);
  const [seating, setSeating] = useState(false);

  const reset = () => {
    setStep('input'); setPartySize(2); setGuestName(''); setGuestMatches([]);
    setGuestSearchOpen(false); setSelectedGuest(null); setResult(null);
    setChosenTable(null); setShowAlternatives(false);
  };

  const handleClose = () => { reset(); onClose(); };

  const onGuestNameChange = (v) => {
    setGuestName(v);
    setSelectedGuest(null);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    if (v.trim().length < 2) { setGuestMatches([]); setGuestSearchOpen(false); return; }
    searchTimer.current = setTimeout(async () => {
      try {
        const r = await reservationsAPI.guestLookup({ q: v.trim(), limit: 5, intel: false });
        setGuestMatches(r.data?.matches || []);
        setGuestSearchOpen(true);
      } catch { /* best-effort lookup, never block seating */ }
    }, 300);
  };

  const pickGuest = (m) => {
    setSelectedGuest(m);
    setGuestName(m.name || '');
    setGuestSearchOpen(false);
  };

  const findTable = async () => {
    setLoading(true);
    try {
      const r = await reservationsAIAPI.aiAssignWalkin({
        partySize, customerId: selectedGuest?.id || undefined,
      });
      setResult(r.data);
      setChosenTable(r.data.recommended || null);
      setShowAlternatives(false);
      setStep('recommend');
    } catch (e) {
      if (e?.response?.status === 404) {
        setStep('notConfigured');
      } else {
        toast.error(e?.response?.data?.detail || 'Could not look for a table — try again');
      }
    }
    setLoading(false);
  };

  const seatHere = async () => {
    if (!chosenTable) return;
    setSeating(true);
    try {
      const r = await reservationsAIAPI.seatWalkin({
        tableId: chosenTable.tableId, partySize,
        guestName: selectedGuest?.name || guestName || undefined,
        customerId: selectedGuest?.id || undefined,
      });
      toast.success(`Seated at Table ${r.data.tableName}${r.data.section ? ` · ${r.data.section}` : ''}`);
      onSeated?.();
      handleClose();
      return;
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'That table was just taken — showing you another');
      await findTable();
    }
    setSeating(false);
  };

  const alternatives = result?.alternatives || [];

  return (
    <Dialog open={open} onOpenChange={(o) => !o && handleClose()}>
      <DialogContent className="max-w-md" data-testid="walkin-ai-seat-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles size={18} style={{ color: theme.secondary }} /> Walk-in → AI Seat
          </DialogTitle>
        </DialogHeader>

        {/* ===== STEP: INPUT ===== */}
        {step === 'input' && (
          <div className="space-y-4 py-1">
            <div>
              <label className="text-xs font-semibold text-gray-500 mb-2 block">Party size</label>
              <div className="flex items-center gap-2 flex-wrap">
                {PARTY_QUICK_PICKS.map(n => (
                  <button
                    key={n}
                    onClick={() => setPartySize(n)}
                    data-testid={`walkin-party-${n}`}
                    className="w-11 h-11 rounded-xl text-sm font-bold transition-colors border"
                    style={partySize === n
                      ? { backgroundColor: theme.primary, color: '#fff', borderColor: theme.primary }
                      : { borderColor: darkMode ? '#3f3f46' : '#e5e7eb', color: theme.text }}
                  >
                    {n}
                  </button>
                ))}
                <div className="flex items-center gap-1 ml-1">
                  <button
                    onClick={() => setPartySize(p => Math.max(1, p - 1))}
                    className="w-9 h-9 rounded-lg border flex items-center justify-center"
                    style={{ borderColor: darkMode ? '#3f3f46' : '#e5e7eb' }}
                    data-testid="walkin-party-minus"
                  ><Minus size={14} /></button>
                  <span className="w-8 text-center font-bold text-sm">{partySize}</span>
                  <button
                    onClick={() => setPartySize(p => Math.min(30, p + 1))}
                    className="w-9 h-9 rounded-lg border flex items-center justify-center"
                    style={{ borderColor: darkMode ? '#3f3f46' : '#e5e7eb' }}
                    data-testid="walkin-party-plus"
                  ><Plus size={14} /></button>
                </div>
              </div>
            </div>

            <div className="relative">
              <label className="text-xs font-semibold text-gray-500 mb-2 block">Guest name (optional)</label>
              <Input
                value={guestName}
                onChange={e => onGuestNameChange(e.target.value)}
                onFocus={() => { if (guestMatches.length > 0) setGuestSearchOpen(true); }}
                placeholder="Start typing to find a returning guest…"
                data-testid="walkin-guest-name"
              />
              {selectedGuest && (
                <div
                  className="mt-2 flex items-center gap-2 rounded-lg px-3 py-2 text-xs"
                  style={{ background: `${theme.secondary}12` }}
                  data-testid="walkin-guest-recognised"
                >
                  <Star size={13} style={{ color: theme.secondary }} />
                  <span className="font-medium">{selectedGuest.name}</span>
                  {selectedGuest.isVip && <Badge className="text-[9px]" style={{ background: theme.accent, color: '#fff' }}>VIP</Badge>}
                  {typeof selectedGuest.visits === 'number' && (
                    <span className="text-gray-500">· {selectedGuest.visits} visit{selectedGuest.visits === 1 ? '' : 's'}</span>
                  )}
                </div>
              )}
              {guestSearchOpen && guestMatches.length > 0 && (
                <div className="absolute z-20 mt-1 w-full rounded-lg border bg-white dark:bg-zinc-900 shadow-lg max-h-48 overflow-y-auto">
                  {guestMatches.map(m => (
                    <button
                      key={m.id}
                      onClick={() => pickGuest(m)}
                      className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 dark:hover:bg-zinc-800 flex items-center justify-between"
                      data-testid={`walkin-guest-match-${m.id}`}
                    >
                      <span>{m.name}</span>
                      {m.isVip && <Badge className="text-[9px]" style={{ background: theme.accent, color: '#fff' }}>VIP</Badge>}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <Button
              className="w-full h-12 text-base"
              style={{ backgroundColor: theme.primary }}
              disabled={loading || !partySize}
              onClick={findTable}
              data-testid="walkin-find-table-btn"
            >
              {loading ? <><RefreshCw size={16} className="mr-2 animate-spin" /> Finding a table…</> : <><Sparkles size={16} className="mr-2" /> Find a Table</>}
            </Button>
          </div>
        )}

        {/* ===== STEP: NOT CONFIGURED (empty-state, not a raw error) ===== */}
        {step === 'notConfigured' && (
          <div className="py-6 text-center space-y-3" data-testid="walkin-not-configured">
            <div className="w-14 h-14 rounded-2xl mx-auto flex items-center justify-center" style={{ background: `${theme.primary}15` }}>
              <LayoutGrid size={26} style={{ color: theme.primary }} />
            </div>
            <div>
              <p className="font-semibold" style={{ color: theme.text }}>No tables are configured yet</p>
              <p className="text-sm text-gray-500 mt-1 max-w-xs mx-auto">
                Set up a floor plan with your tables so Walk-in AI Seat can find and seat guests automatically.
              </p>
            </div>
            <div className="flex flex-col gap-2 pt-2 max-w-xs mx-auto">
              <Button style={{ backgroundColor: theme.primary }} onClick={() => { handleClose(); navigate('/floor-plan'); }} data-testid="walkin-goto-floorplan-btn">
                <LayoutGrid size={14} className="mr-1.5" /> Configure Floor & Tables
              </Button>
              <Button variant="outline" onClick={handleClose}>Close</Button>
            </div>
          </div>
        )}

        {/* ===== STEP: RECOMMEND ===== */}
        {step === 'recommend' && result && (
          <div className="space-y-4 py-1">
            <button onClick={() => setStep('input')} className="flex items-center gap-1 text-xs text-gray-500" data-testid="walkin-back-btn">
              <ArrowLeft size={13} /> Party of {partySize}{selectedGuest ? ` · ${selectedGuest.name}` : ''}
            </button>

            {result.assigned === false ? (
              <div className="py-6 text-center space-y-3" data-testid="walkin-no-table-free">
                <AlertCircle size={30} className="mx-auto" style={{ color: theme.primary }} />
                <div>
                  <p className="font-semibold" style={{ color: theme.text }}>No table free right now</p>
                  <p className="text-sm text-gray-500 mt-1">{result.reason || 'Every table that fits this party is currently occupied.'}</p>
                </div>
                <div className="flex flex-col gap-2 pt-1 max-w-xs mx-auto">
                  <Button variant="outline" onClick={findTable} data-testid="walkin-retry-btn"><RefreshCw size={14} className="mr-1.5" /> Check Again</Button>
                  <Button variant="outline" onClick={() => { handleClose(); navigate('/floor-plan'); }}>View Floor Plan</Button>
                </div>
              </div>
            ) : (
              <>
                {chosenTable && (
                  <div className="rounded-xl border-2 p-4" style={{ borderColor: theme.primary, background: `${theme.primary}0a` }} data-testid="walkin-recommendation-card">
                    <div className="flex items-center gap-1.5 text-xs font-semibold mb-2" style={{ color: theme.primary }}>
                      <Sparkles size={13} /> {chosenTable.tableId === result.recommended?.tableId ? 'AI Recommendation' : 'Selected Table'}
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ background: theme.primary }}>
                          <Armchair size={20} className="text-white" />
                        </div>
                        <div>
                          <p className="font-bold text-lg leading-tight" style={{ color: theme.text }}>Table {chosenTable.tableNumber}</p>
                          <p className="text-xs text-gray-500">{chosenTable.capacity} seats · {chosenTable.floor || 'Main floor'}{chosenTable.section ? ` · ${chosenTable.section}` : ''}</p>
                        </div>
                      </div>
                      <Badge className="text-[10px]" style={{ background: (TABLE_STATUS_STYLE[chosenTable.status] || TABLE_STATUS_STYLE.available).bg, color: (TABLE_STATUS_STYLE[chosenTable.status] || TABLE_STATUS_STYLE.available).color }}>
                        {(TABLE_STATUS_STYLE[chosenTable.status] || TABLE_STATUS_STYLE.available).label}
                      </Badge>
                    </div>
                    {chosenTable.tableId === result.recommended?.tableId && (
                      <p className="text-xs text-gray-500 mt-2">Best match for a party of {partySize}.</p>
                    )}
                  </div>
                )}

                {result.guest && (
                  <div className="flex items-center gap-2 rounded-lg px-3 py-2 text-xs" style={{ background: `${theme.secondary}12` }} data-testid="walkin-guest-summary">
                    <Star size={13} style={{ color: theme.secondary }} />
                    <span className="font-medium">{result.guest.name}</span>
                    {result.guest.isVip && <Badge className="text-[9px]" style={{ background: theme.accent, color: '#fff' }}>VIP</Badge>}
                    {(result.guest.allergies?.length > 0 || result.guest.dietaryRestrictions?.length > 0) && (
                      <span className="text-amber-600 flex items-center gap-1"><AlertCircle size={11} /> Dietary notes on file</span>
                    )}
                  </div>
                )}

                <div className="flex gap-2">
                  <Button className="flex-1 h-12 text-base" style={{ backgroundColor: theme.primary }} disabled={seating} onClick={seatHere} data-testid="walkin-seat-here-btn">
                    {seating ? <><RefreshCw size={16} className="mr-2 animate-spin" /> Seating…</> : <><Check size={16} className="mr-2" /> Seat Here</>}
                  </Button>
                  {alternatives.length > 0 && (
                    <Button variant="outline" className="h-12" onClick={() => setShowAlternatives(s => !s)} data-testid="walkin-view-others-btn">
                      <Users size={15} className="mr-1.5" /> {showAlternatives ? 'Hide' : 'Other Tables'}
                    </Button>
                  )}
                </div>

                {showAlternatives && (
                  <div className="space-y-1.5" data-testid="walkin-alternatives-list">
                    {alternatives.map(t => (
                      <button
                        key={t.tableId}
                        onClick={() => { setChosenTable(t); setShowAlternatives(false); }}
                        className="w-full flex items-center justify-between rounded-lg border px-3 py-2 text-sm hover:border-gray-400 transition-colors"
                        style={{ borderColor: darkMode ? '#3f3f46' : '#e5e7eb' }}
                        data-testid={`walkin-alt-${t.tableId}`}
                      >
                        <span className="flex items-center gap-2">
                          <MapPin size={13} className="text-gray-400" />
                          Table {t.tableNumber} · {t.capacity} seats{t.section ? ` · ${t.section}` : ''}
                        </span>
                        <Badge className="text-[9px]" style={{ background: (TABLE_STATUS_STYLE[t.status] || TABLE_STATUS_STYLE.available).bg, color: (TABLE_STATUS_STYLE[t.status] || TABLE_STATUS_STYLE.available).color }}>
                          {(TABLE_STATUS_STYLE[t.status] || TABLE_STATUS_STYLE.available).label}
                        </Badge>
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
