import React, { useEffect, useState } from 'react';
import { v25API, v26API } from '../../services/api';
import { Monitor } from 'lucide-react';
import { useLanguage } from '../../i18n/useLanguage';
import { LanguageSelector } from '../../i18n/LanguageSelector';

function itemName(item, lang) {
  return item?.translations?.[lang]?.name || item.name;
}

export default function CFD() {
  const [data, setData] = useState({ cart: [] });
  const { lang, setLang, t, dir, languages } = useLanguage('nua_cfd_lang');
  useEffect(() => {
    const tick = () => v26API.cfdEnriched()
      .then(r => setData(r.data || { cart: [] }))
      .catch(() => v25API.cfdCurrent().then(r => setData(r.data || { cart: [] })));
    tick();
    const id = setInterval(tick, 5000);
    return () => clearInterval(id);
  }, []);
  const total = (data.cart || []).reduce((s, i) => s + (i.price || 0) * (i.quantity || 1), 0);
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
    </div>
  );
}
