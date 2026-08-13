import React, { useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { v25API, voiceAPI } from '../../services/api';
import { useTheme } from '../../contexts/ThemeContext';
import { MessageSquare, PhoneCall } from 'lucide-react';
import { useToast } from '../../hooks/use-toast';

export default function Concierge() {
  const { theme } = useTheme();
  const { toast } = useToast();
  const [msg, setMsg] = useState(''); const [resp, setResp] = useState(null); const [loading, setLoading] = useState(false);
  const [calling, setCalling] = useState(false);
  const send = async () => {
    if (!msg.trim()) return;
    setLoading(true);
    try { const r = await v25API.concierge(msg); setResp(r.data); } finally { setLoading(false); }
  };
  const callToConfirm = async () => {
    if (!resp?.matchedCustomer?.id) return;
    setCalling(true);
    try {
      await voiceAPI.call({
        customerId: resp.matchedCustomer.id, purpose: 'confirm_booking',
        context: { message: resp.reply },
      });
      toast({ title: 'Calling now to confirm the booking.' });
    } catch (e) {
      toast({ title: 'Could not place the call', description: e?.response?.data?.detail || 'Try again', variant: 'destructive' });
    } finally { setCalling(false); }
  };
  return (
    <div className="space-y-6" data-testid="concierge-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><MessageSquare className="text-purple-600" /> AI Concierge</h1>
      <Card><CardContent className="p-5 space-y-3">
        <textarea className="w-full p-3 border rounded text-sm" rows={3} placeholder="e.g. Need a table for 6 tonight at 7:30, John needs gluten-free" value={msg} onChange={e => setMsg(e.target.value)} data-testid="concierge-input" />
        <Button onClick={send} disabled={loading} style={{ background: theme.primary }} data-testid="concierge-send">{loading ? 'Thinking…' : 'Process'}</Button>
        {resp && (
          <div className="p-4 bg-purple-50 border border-purple-200 rounded space-y-1" data-testid="concierge-response">
            <p className="text-sm font-bold">Intent: <Badge>{resp.intent}</Badge> {resp.created && <Badge className="bg-emerald-600">Reservation: {resp.reservationId}</Badge>}</p>
            <p className="text-sm">{resp.reply}</p>
            {resp.matchedCustomer && (
              <p className="text-xs text-purple-700">
                Matched existing guest: {resp.matchedCustomer.name}{resp.matchedCustomer.isVip ? ' (VIP)' : ''}
              </p>
            )}
            {resp.created && resp.matchedCustomer?.id && (
              <Button size="sm" variant="outline" onClick={callToConfirm} disabled={calling}
                className="mt-1" data-testid="concierge-call-btn">
                <PhoneCall size={14} className="mr-1.5" />
                {calling ? 'Calling…' : 'Call to confirm'}
              </Button>
            )}
          </div>
        )}
      </CardContent></Card>
    </div>
  );
}
