import React, { useEffect, useState } from 'react';
import { v25API, v26API } from '../../services/api';
import { Monitor, Flame } from 'lucide-react';
import { useLanguage } from '../../i18n/useLanguage';
import { LanguageSelector } from '../../i18n/LanguageSelector';

function itemName(item, lang) {
  return item?.translations?.[lang]?.name || item.name;
}

export default function CFD() {
  const [data, setData] = useState({ cart: [] });
  const [fetchedAt, setFetchedAt] = useState(null);
  const [nowTick, setNowTick] = useState(Date.now());
  const { lang, setLang, t, dir, languages } = useLanguage('nua_cfd_lang');
  useEffect(() => {
    const tick = () => v26API.cfdEnriched()
      .then(r => { setData(r.data || { cart: [] }); setFetchedAt(Date.now()); })
      .catch(() => v25API.cfdCurrent().then(r => { setData(r.data || { cart: [] }); setFetchedAt(Date.now()); }));
    tick();
    const id = setInterval(tick, 5000);
    return () => clearInterval(id);
  }, []);
  // Ticks the promo countdown down to the second between 5s data refreshes,
  // instead of the display jumping in 5-second steps.
  useEffect(() => {
    const id = setInterval(() => setNowTick(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  const total = (data.cart || []).reduce((s, i) => s + (i.price || 0) * (i.quantity || 1), 0);
  const activePromotions = (data.activePromotions || []).map(p => {
    if (p.endsInMinutes == null || fetchedAt == null) return { ...p, remainingLabel: null };
    const elapsedSec = Math.max(0, Math.floor((nowTick - fetchedAt) / 1000));
    const remainingSec = Math.max(0, p.endsInMinutes * 60 - elapsedSec);
    const m = Math.floor(remainingSec / 60), s = remainingSec % 60;
    return { ...p, remainingLabel: `${m}:${String(s).padStart(2, '0')}`, remainingSec };
  }).filter(p => p.remainingSec == null || p.remainingSec > 0);
  return (
    <div className="min-h-screen bg-black text-white p-8 -m-6" dir={dir} data-testid="cfd-page">
      <div className="flex justify-between items-start mb-6">
        <h1 className="text-5xl font-bold flex items-center gap-3"><Monitor /> {t('cfd.welcome')}</h1>
        <div className="flex items-start gap-4">
          {data.tableNumber && <div className="text-right">
            <p className="text-xs text-gray-400 uppercase tracking-widest">{t('cfd.table')}</p>
            <p className="text-4xl font-bold text-amber-400">{data.tableNumber}</p>
          </div>}
          <LanguageSelector lang={lang} setLang={setLang} languages={languages} variant="dark" label={t('common.language')} />
        </div>
      </div>
      {activePromotions.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-2" data-testid="cfd-active-promotions">
          {activePromotions.map(p => (
            <div key={p.id} className="flex items-center gap-2 bg-gradient-to-r from-orange-600 to-red-600 rounded-xl px-4 py-2.5" data-testid={`cfd-promo-${p.id}`}>
              <Flame size={20} className="text-yellow-200" />
              <span className="font-bold text-lg">{p.name}</span>
              {p.pricingMode === 'percentage' && p.discount > 0 && (
                <span className="text-yellow-200 font-bold">{p.discount}% OFF</span>
              )}
              {p.remainingLabel && (
                <span className="text-sm bg-black/25 rounded-full px-2.5 py-0.5 font-mono">ends in {p.remainingLabel}</span>
              )}
            </div>
          ))}
        </div>
      )}
      {data.customerName && (
        <p className="text-2xl text-amber-300 mb-4" data-testid="cfd-customer">
          {data.isMember ? '★ ' : ''}{data.customerName}{data.membershipTier ? ` · ${data.membershipTier}` : ''}
        </p>
      )}
      <div className="space-y-3">
        {(data.cart || []).map((it, i) => (
          <div key={i} className="flex justify-between text-2xl border-b border-gray-700 pb-2">
            <span>{it.quantity || 1}× {itemName(it, lang)}</span>
            <span>${((it.price || 0) * (it.quantity || 1)).toFixed(2)}</span>
          </div>
        ))}
      </div>
      <div className="mt-8 text-5xl font-bold flex justify-between border-t-2 border-white pt-4">
        <span>{t('common.total').toUpperCase()}</span><span>${total.toFixed(2)}</span>
      </div>
      {data.pointsEarned > 0 && (
        <p className="mt-6 text-2xl text-emerald-400" data-testid="points-earned">
          {t('cfd.pointsEarned', { n: data.pointsEarned })}
        </p>
      )}
      {data.pointsMissed > 0 && !data.customerName && (
        <p className="mt-6 text-xl text-orange-400" data-testid="points-missed">
          {t('cfd.pointsMissed', { n: data.pointsMissed })}
        </p>
      )}
      {data.splitInProgress && (data.splitParts || []).length > 0 && (
        <div className="mt-8 border-t-2 border-white pt-4" data-testid="cfd-split">
          <p className="text-2xl font-bold text-amber-400 mb-3">{t('cfd.splitPayment')}</p>
          <div className="space-y-2">
            {data.splitParts.map((s, i) => (
              <div key={i} className="flex justify-between items-center text-xl" data-testid={`cfd-split-part-${i}`}>
                <span>{s.payerName}</span>
                <span className="flex items-center gap-3">
                  <span>${Number(s.amount || 0).toFixed(2)}</span>
                  <span className={`text-sm px-2 py-0.5 rounded-full ${s.status === 'confirmed' ? 'bg-emerald-900 text-emerald-300' : 'bg-gray-800 text-gray-400'}`}>
                    {s.status === 'confirmed' ? t('cfd.paid') : t('cfd.waiting')}
                  </span>
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
