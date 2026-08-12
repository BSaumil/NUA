import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Check, Loader2, X } from 'lucide-react';
import { Button } from '../components/ui/button';
import { stripeAPI, cryptoAPI } from '../services/api';

// Stripe templates {CHECKOUT_SESSION_ID} into the redirect URL itself, so
// this page gets the session id back as ?session_id=. Coinbase Commerce
// has no equivalent templating — it just redirects to the bare URL with
// nothing appended — so the crypto checkout route puts the one thing it
// does know ahead of time, order_id, into the URL instead, and this page
// resolves that to the actual charge via checkStatusByOrder.

export default function PaymentSuccess() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('checking'); // checking | paid | failed
  const provider = searchParams.get('provider') === 'crypto' ? 'crypto' : 'stripe';
  const sessionId = searchParams.get('session_id');
  const orderId = searchParams.get('order_id');

  useEffect(() => {
    const pollKey = provider === 'crypto' ? orderId : sessionId;
    if (!pollKey) { setStatus('failed'); return; }
    let attempts = 0;
    const poll = async () => {
      if (attempts >= 5) { setStatus('failed'); return; }
      attempts++;
      try {
        const res = provider === 'crypto'
          ? await cryptoAPI.checkStatusByOrder(orderId)
          : await stripeAPI.checkStatus(sessionId);
        if (res.data.configured === false) { setStatus('failed'); return; }
        if (res.data.paymentStatus === 'paid') { setStatus('paid'); return; }
        if (res.data.status === 'expired') { setStatus('failed'); return; }
        setTimeout(poll, 2000);
      } catch { setTimeout(poll, 2000); }
    };
    poll();
  }, [sessionId, orderId, provider]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50" data-testid="payment-success-page">
      <div className="text-center max-w-sm p-8">
        {status === 'checking' && (
          <>
            <Loader2 size={48} className="mx-auto mb-4 text-blue-500 animate-spin" />
            <h1 className="text-2xl font-bold mb-2">Processing Payment...</h1>
            <p className="text-gray-500">Please wait while we confirm your payment.</p>
          </>
        )}
        {status === 'paid' && (
          <>
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Check size={32} className="text-green-600" />
            </div>
            <h1 className="text-2xl font-bold mb-2">Payment Successful!</h1>
            <p className="text-gray-500 mb-6">Your payment has been processed.</p>
            <Button onClick={() => navigate('/pos')} className="bg-emerald-600 hover:bg-emerald-700 text-white"
              data-testid="back-to-pos-btn">
              Back to POS
            </Button>
          </>
        )}
        {status === 'failed' && (
          <>
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <X size={32} className="text-red-600" />
            </div>
            <h1 className="text-2xl font-bold mb-2">Payment Issue</h1>
            <p className="text-gray-500 mb-6">There was an issue with your payment. Please try again.</p>
            <Button onClick={() => navigate('/pos')} variant="outline" data-testid="retry-btn">
              Return to POS
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
