import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { v25API } from '../../services/api';
import { useTheme } from '../../contexts/ThemeContext';
import { useToast } from '../../hooks/use-toast';
import { Smartphone } from 'lucide-react';
import { useLanguage } from '../../i18n/useLanguage';
import { LanguageSelector } from '../../i18n/LanguageSelector';

function productName(p, lang) {
  return p?.translations?.[lang]?.name || p.name;
}

export default function KioskMode() {
  const { theme } = useTheme(); const { toast } = useToast();
  const { lang, setLang, t, dir, languages } = useLanguage('nua_kiosk_lang');
  const [products, setProducts] = useState([]);
  const [session, setSession] = useState(null);
  const [cart, setCart] = useState([]);
  useEffect(() => { fetch(`${process.env.REACT_APP_BACKEND_URL}/api/products`).then(r => r.json()).then(setProducts).catch(() => {}); }, []);
  const start = async () => { const r = await v25API.kioskStart({ guests: 2 }); setSession(r.data); setCart([]); };
  const add = (p) => { setCart([...cart, p]); v25API.kioskAdd(session.id, { productId: p.id, name: p.name, price: p.price, quantity: 1 }); };
  const checkout = async () => { await v25API.kioskCheckout(session.id); toast({ title: t('kiosk.orderSent') }); setSession(null); setCart([]); };
  return (
    <div className="space-y-6" dir={dir} data-testid="kiosk-page">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Smartphone className="text-blue-600" /> {t('kiosk.title')}</h1>
        <div className="flex items-center gap-3">
          <LanguageSelector lang={lang} setLang={setLang} languages={languages} variant="light" label={t('common.language')} />
          {!session ? <Button onClick={start} style={{ background: theme.primary }} data-testid="kiosk-start">{t('kiosk.startOrder')}</Button> :
            <Button onClick={checkout} style={{ background: theme.primary }} data-testid="kiosk-checkout">{t('kiosk.checkout')} ({cart.length})</Button>}
        </div>
      </div>
      {session && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {products.slice(0, 12).map(p => (
            <button key={p.id} onClick={() => add(p)} className="border rounded-xl p-4 hover:shadow-md hover:-translate-y-0.5 transition-all text-left" data-testid={`kiosk-prod-${p.id}`}>
              <p className="font-bold">{productName(p, lang)}</p><p className="text-lg" style={{ color: theme.primary }}>${p.price}</p>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
