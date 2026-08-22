import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { Receipt, Check, Users, Loader2, Bitcoin, CreditCard, X, Settings, AlertCircle } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { billSplitAPI, guestSessionAPI } from '../services/api';
import { toast } from 'sonner';
import { useSplitWebSocket } from '../hooks/useSplitWebSocket';
import { LiveStatus } from '../components/split/LiveStatus';
import { GroupInvite } from '../components/split/GroupInvite';
import { AccessibilityPanel } from '../components/split/AccessibilityPanel';
import { t } from '../lib/i18n';

const TOKEN_KEY = 'nua_guest_token';
const PHONE_KEY = 'nua_guest_phone';
const mineKey = (splitId) => `nua_guest_mine_${splitId}`;

function money(n) { return `$${(n || 0).toFixed(2)}`; }

function loadMine(splitId) {
  try {
    const raw = sessionStorage.getItem(mineKey(splitId));
    if (!raw) return { lines: new Set(), slots: new Set() };
    const parsed = JSON.parse(raw);
    return { lines: new Set(parsed.lines || []), slots: new Set(parsed.slots || []) };
  } catch { return { lines: new Set(), slots: new Set() }; }
}

function saveMine(splitId, mine) {
  sessionStorage.setItem(mineKey(splitId), JSON.stringify({ lines: [...mine.lines], slots: [...mine.slots] }));
}

export default function SplitBillGuestEnhanced() {
  const { tableNumber: tableFromPath } = useParams();
  const [searchParams] = useSearchParams();
  const splitParam = searchParams.get('split');
  const inviteCodeParam = searchParams.get('inviteCode');

  const [split, setSplit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [mine, setMine] = useState({ lines: new Set(), slots: new Set() });
  const [selected, setSelected] = useState([]);
  const [equalCount, setEqualCount] = useState(4);
  const [phone, setPhone] = useState(sessionStorage.getItem(PHONE_KEY) || '');
  const [token, setToken] = useState(sessionStorage.getItem(TOKEN_KEY) || '');
  const [otpStage, setOtpStage] = useState(null);
  const [otpCode, setOtpCode] = useState('');
  const [busy, setBusy] = useState(false);
  const pollRef = useRef(null);
  const [claimedByOthers, setClaimedByOthers] = useState([]);
  const [showAccessibility, setShowAccessibility] = useState(false);
  const [group, setGroup] = useState(null);
  const [isOrganizer, setIsOrganizer] = useState(false);
  const [showPartialPayment, setShowPartialPayment] = useState(false);
  const [partialAmount, setPartialAmount] = useState('');

  // WebSocket for real-time updates
  const { connected, error: wsError, requestSync } = useSplitWebSocket(
    split?.id,
    (data) => {
      if (data.type === 'split_updated' && data.data) {
        setSplit(data.data);
        setMine(loadMine(data.data.id));
      } else if (data.type === 'item_claimed') {
        setClaimedByOthers(prev => [...prev, data.data]);
        requestSync();
      } else if (data.type === 'payment_received') {
        requestSync();
      }
    }
  );

  const load = useCallback(async () => {
    try {
      const res = splitParam
        ? await billSplitAPI.status(splitParam)
        : await billSplitAPI.getSplit(tableFromPath);
      setSplit(res.data);
      setMine(loadMine(res.data.id));

      // Load group info if exists
      if (res.data.groupMode) {
        try {
          const groupRes = await fetch(`/api/table/split/${res.data.id}/group/status`);
          const groupData = await groupRes.json();
          setGroup(groupData);
          setIsOrganizer(groupData.organizerPhone === phone);
        } catch (e) {
          console.warn('Failed to load group info');
        }
      }

      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail || t('split.errors.loadFailed', 'Couldn\'t load bill'));
    } finally {
      setLoading(false);
    }
  }, [tableFromPath, splitParam, phone]);

  useEffect(() => {
    load();
    pollRef.current = setInterval(load, 4000);
    return () => clearInterval(pollRef.current);
  }, [load]);

  // Handle invite code in URL
  useEffect(() => {
    if (inviteCodeParam && phone && split?.id) {
      const acceptInvite = async () => {
        try {
          const res = await fetch(`/api/table/split/${split.id}/group/accept-invite`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify({ inviteToken: inviteCodeParam }),
          });
          if (res.ok) {
            toast.success('Joined group!');
            load();
          }
        } catch (e) {
          console.warn('Failed to accept invite');
        }
      };
      acceptInvite();
    }
  }, [inviteCodeParam, phone, split?.id, token, load]);

  const rememberMine = (patch) => {
    setMine(prev => {
      const next = {
        lines: new Set([...prev.lines, ...(patch.lines || [])]),
        slots: new Set([...prev.slots, ...(patch.slots || [])]),
      };
      if (split?.id) saveMine(split.id, next);
      return next;
    });
  };

  const requestCode = async () => {
    if (!phone.trim()) {
      toast.error(t('split.errors.phoneRequired'));
      return;
    }
    setBusy(true);
    try {
      await guestSessionAPI.requestCode(phone.trim());
      setOtpStage('code-sent');
      toast.success(t('split.messages.codeSent', { phone }));
    } catch {
      toast.error(t('split.messages.sendCodeFailed', 'Could not send a code'));
    } finally {
      setBusy(false);
    }
  };

  const verifyCode = async () => {
    if (!otpCode.trim()) return;
    setBusy(true);
    try {
      const r = await guestSessionAPI.verify(phone.trim(), otpCode.trim());
      setToken(r.data.token);
      sessionStorage.setItem(TOKEN_KEY, r.data.token);
      sessionStorage.setItem(PHONE_KEY, phone.trim());
      setOtpStage(null);
      setOtpCode('');
      toast.success(t('split.messages.verified', 'Phone verified!'));
    } catch (e) {
      toast.error(e?.response?.data?.detail || t('split.errors.invalidCode'));
    } finally {
      setBusy(false);
    }
  };

  const chooseMode = async (mode) => {
    const table = split?.tableNumber || tableFromPath;
    setBusy(true);
    try {
      const r = await billSplitAPI.chooseMode(table, mode, equalCount);
      setSplit(r.data);
    } catch (e) {
      toast.error(e?.response?.data?.detail || t('split.errors.setModeFailed'));
    } finally {
      setBusy(false);
    }
  };

  const toggleLine = (line) => {
    if (line.status !== 'open') return;
    setSelected(prev =>
      prev.includes(line.id) ? prev.filter(id => id !== line.id) : [...prev, line.id]
    );
  };

  const claimSelected = async () => {
    if (!token) {
      toast.error(t('split.errors.verifyFirst'));
      return;
    }
    if (!selected.length) return;
    setBusy(true);
    try {
      const r = await billSplitAPI.claim(split.id, selected, token);
      setSplit(r.data.split);
      if (r.data.failed.length) {
        toast.error(t('split.messages.someItemsTaken'));
      }
      rememberMine({ lines: r.data.claimed });
      setSelected([]);
    } catch (e) {
      toast.error(e?.response?.data?.detail || t('split.errors.claimFailed'));
    } finally {
      setBusy(false);
    }
  };

  const handlePartialPayment = async () => {
    if (!token) {
      toast.error(t('split.errors.verifyFirst'));
      return;
    }
    if (!partialAmount || parseFloat(partialAmount) <= 0) {
      toast.error(t('split.errors.amountRequired'));
      return;
    }

    setBusy(true);
    try {
      const response = await fetch(`/api/table/split/${split.id}/partial-checkout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          amount: parseFloat(partialAmount),
          lineIds: selected,
          totalAmount: selected.reduce((sum, id) => {
            const line = split.lines.find(l => l.id === id);
            return sum + (line?.unitPrice || 0);
          }, 0),
        }),
      });

      if (response.ok) {
        toast.success(t('split.tab.tabCreated'));
        setShowPartialPayment(false);
        setPartialAmount('');
        load();
      }
    } catch (e) {
      toast.error('Failed to create tab');
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 max-w-md mx-auto text-center">
        <AlertCircle size={32} className="mx-auto text-red-500 mb-2" />
        <p className="text-red-700 font-medium">{error}</p>
      </div>
    );
  }

  const myLines = split?.lines.filter(l => mine.lines.has(l.id)) || [];
  const myClaimedLines = myLines.filter(l => l.status === 'claimed');
  const myAmount = myClaimedLines.reduce((sum, l) => sum + (l.unitPrice || 0), 0);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-4">
      {/* Accessibility Button */}
      <div className="fixed top-4 right-4 z-40">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowAccessibility(!showAccessibility)}
          className="gap-1"
          aria-label="Accessibility settings"
        >
          <Settings size={16} />
          <span className="sr-only">Settings</span>
        </Button>
      </div>

      {/* Accessibility Panel */}
      {showAccessibility && (
        <AccessibilityPanel onClose={() => setShowAccessibility(false)} />
      )}

      <div className="max-w-2xl mx-auto space-y-4">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">
            {t('split.title')}
          </h1>
          <p className="text-gray-600">{t('split.subtitle')}</p>
        </div>

        {/* Connection Status */}
        {wsError && !connected && (
          <div className="p-3 bg-amber-50 border border-amber-200 rounded text-sm text-amber-800">
            {wsError}
          </div>
        )}

        {/* Live Status */}
        {split?.id && (
          <LiveStatus split={split} connected={connected} claimedByOthers={claimedByOthers} />
        )}

        {/* Split Mode Selection */}
        {!split?.mode && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t('split.mode')}</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-2">
              <Button
                variant="outline"
                onClick={() => chooseMode('items')}
                disabled={busy}
                className="flex flex-col items-center gap-1 h-auto py-3"
              >
                <Receipt size={20} />
                {t('split.items')}
              </Button>
              <Button
                variant="outline"
                onClick={() => chooseMode('equal')}
                disabled={busy}
                className="flex flex-col items-center gap-1 h-auto py-3"
              >
                <Users size={20} />
                {t('split.equal')}
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Items Grid */}
        {split?.mode === 'items' && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                {t('split.selectItems')} ({selected.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-64 overflow-y-auto">
                {split?.lines?.map(line => (
                  <button
                    key={line.id}
                    onClick={() => toggleLine(line)}
                    disabled={line.status !== 'open'}
                    className={`p-3 rounded-lg border-2 text-left transition ${
                      line.status === 'paid'
                        ? 'bg-gray-100 border-gray-300 cursor-not-allowed opacity-50'
                        : line.status === 'claimed'
                        ? 'bg-yellow-50 border-yellow-300 cursor-not-allowed'
                        : selected.includes(line.id)
                        ? 'bg-blue-50 border-blue-400'
                        : 'bg-white border-gray-300 hover:border-blue-400'
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-medium text-sm">{line.productName}</p>
                        <p className="text-xs text-gray-600">{line.category}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-bold">{money(line.unitPrice)}</p>
                        <p className="text-xs text-gray-600">
                          {line.status === 'open' ? t('split.status.open') : line.status}
                        </p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>

              {selected.length > 0 && (
                <div className="mt-4 pt-4 border-t">
                  <p className="text-sm text-gray-600 mb-2">
                    Your share: {money(selected.reduce((sum, id) => {
                      const line = split.lines.find(l => l.id === id);
                      return sum + (line?.unitPrice || 0);
                    }, 0))}
                  </p>
                  <Button
                    onClick={claimSelected}
                    disabled={busy || !token}
                    className="w-full gap-1"
                  >
                    {busy ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
                    {t('split.claim')}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Phone Verification */}
        {!token && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t('split.phone')}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {!otpStage ? (
                <>
                  <Input
                    type="tel"
                    placeholder={t('split.enterPhone')}
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    disabled={busy}
                  />
                  <Button onClick={requestCode} disabled={busy} className="w-full">
                    {busy && <Loader2 size={16} className="animate-spin mr-2" />}
                    {t('split.sendCode')}
                  </Button>
                </>
              ) : (
                <>
                  <Input
                    type="text"
                    placeholder={t('split.enterCode')}
                    value={otpCode}
                    onChange={(e) => setOtpCode(e.target.value)}
                    disabled={busy}
                    maxLength="6"
                  />
                  <Button onClick={verifyCode} disabled={busy || !otpCode} className="w-full">
                    {busy && <Loader2 size={16} className="animate-spin mr-2" />}
                    {t('split.verify')}
                  </Button>
                </>
              )}
            </CardContent>
          </Card>
        )}

        {/* Group Coordination */}
        {split?.id && (
          <GroupInvite
            splitId={split.id}
            groupId={group?.id}
            isOrganizer={isOrganizer}
            participants={group?.participants || []}
          />
        )}

        {/* Partial Payment Tab */}
        {token && myClaimedLines.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                {t('split.tab.title')} - {money(myAmount)}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {!showPartialPayment ? (
                <div className="space-y-2">
                  <Button onClick={() => setShowPartialPayment(true)} variant="outline" className="w-full">
                    {t('split.tab.partial')}
                  </Button>
                  <Button className="w-full gap-1" onClick={() => {}}>
                    <CreditCard size={16} />
                    {t('split.pay')}
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  <Input
                    type="number"
                    placeholder={t('split.tab.amountToPay')}
                    value={partialAmount}
                    onChange={(e) => setPartialAmount(e.target.value)}
                    min="0"
                    step="0.01"
                    max={myAmount}
                  />
                  <div className="text-sm text-gray-600">
                    {t('split.tab.remaining')}: {money(myAmount - (parseFloat(partialAmount) || 0))}
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <Button
                      variant="outline"
                      onClick={() => setShowPartialPayment(false)}
                    >
                      Cancel
                    </Button>
                    <Button onClick={handlePartialPayment} disabled={busy}>
                      Pay {money(parseFloat(partialAmount) || 0)}
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
