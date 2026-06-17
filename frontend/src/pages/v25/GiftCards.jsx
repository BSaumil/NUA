import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { v25API } from '../../services/api';
import { useTheme } from '../../contexts/ThemeContext';
import { useToast } from '../../hooks/use-toast';
import { Gift } from 'lucide-react';

export default function GiftCards() {
  const { theme } = useTheme(); const { toast } = useToast();
  const [cards, setCards] = useState([]);
  const [amount, setAmount] = useState(50);
  const load = () => v25API.giftCards().then(r => setCards(r.data || []));
  useEffect(() => { load(); }, []);
  const issue = async () => {
    const recipientName = prompt('Recipient name?') || 'Guest';
    await v25API.issueGift({ amount, recipientName, bonus: amount >= 100 ? 20 : 0, occasion: 'general' });
    toast({ title: 'Gift card issued' }); load();
  };
  return (
    <div className="space-y-6" data-testid="gift-cards-page">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Gift className="text-rose-600" /> Smart Gift Cards</h1>
        <div className="flex gap-2 items-center">
          <Input type="number" value={amount} onChange={e => setAmount(parseFloat(e.target.value) || 0)} className="w-24" />
          <Button onClick={issue} style={{ background: theme.primary }} data-testid="issue-gift">Issue</Button>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {cards.map(c => (
          <Card key={c.id} className="bg-gradient-to-br from-rose-50 to-pink-100" data-testid={`gift-${c.id}`}>
            <CardContent className="p-5">
              <p className="text-xs text-gray-500">{c.occasion} · {c.recipientName}</p>
              <p className="font-mono text-lg mt-1">{c.code}</p>
              <p className="text-2xl font-bold mt-2">${c.amount}{c.bonus > 0 && <span className="text-sm text-emerald-600"> +${c.bonus}</span>}</p>
              <Badge variant="outline" className="mt-2">{c.status}</Badge>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
