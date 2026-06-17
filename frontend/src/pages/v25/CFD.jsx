import React, { useEffect, useState } from 'react';
import { v25API, v26API } from '../../services/api';
import { Monitor } from 'lucide-react';

export default function CFD() {
  const [data, setData] = useState({ cart: [] });
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
    <div className="min-h-screen bg-black text-white p-8 -m-6" data-testid="cfd-page">
      <div className="flex justify-between items-start mb-6">
        <h1 className="text-5xl font-bold flex items-center gap-3"><Monitor /> Welcome</h1>
        {data.tableNumber && <div className="text-right">
          <p className="text-xs text-gray-400 uppercase tracking-widest">Table</p>
          <p className="text-4xl font-bold text-amber-400">{data.tableNumber}</p>
        </div>}
      </div>
      {data.customerName && (
        <p className="text-2xl text-amber-300 mb-4" data-testid="cfd-customer">
          {data.isMember ? '★ ' : ''}{data.customerName}{data.membershipTier ? ` · ${data.membershipTier}` : ''}
        </p>
      )}
      <div className="space-y-3">
        {(data.cart || []).map((it, i) => (
          <div key={i} className="flex justify-between text-2xl border-b border-gray-700 pb-2">
            <span>{it.quantity || 1}× {it.name}</span>
            <span>${((it.price || 0) * (it.quantity || 1)).toFixed(2)}</span>
          </div>
        ))}
      </div>
      <div className="mt-8 text-5xl font-bold flex justify-between border-t-2 border-white pt-4">
        <span>TOTAL</span><span>${total.toFixed(2)}</span>
      </div>
      {data.pointsEarned > 0 && (
        <p className="mt-6 text-2xl text-emerald-400" data-testid="points-earned">
          You&apos;ll earn {data.pointsEarned} points
        </p>
      )}
      {data.pointsMissed > 0 && !data.customerName && (
        <p className="mt-6 text-xl text-orange-400" data-testid="points-missed">
          Sign up to earn {data.pointsMissed} points — ask staff to add you!
        </p>
      )}
    </div>
  );
}
