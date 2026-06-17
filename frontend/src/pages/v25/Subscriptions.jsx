import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { v25API } from '../../services/api';
import { useTheme } from '../../contexts/ThemeContext';
import { Star } from 'lucide-react';

export default function Subscriptions() {
  const { theme } = useTheme();
  const [plans, setPlans] = useState([]); const [members, setMembers] = useState([]);
  useEffect(() => { v25API.subPlans().then(r => setPlans(r.data || [])); v25API.subMembers().then(r => setMembers(r.data || [])); }, []);
  return (
    <div className="space-y-6" data-testid="subs-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Star className="text-yellow-500" /> Subscription Memberships</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {plans.map(p => (
          <Card key={p.id} className="bg-gradient-to-br from-amber-50 to-yellow-100"><CardContent className="p-5">
            <p className="font-bold text-lg">{p.name}</p>
            <p className="text-3xl font-bold mt-2">${p.priceMonthly}<span className="text-sm text-gray-500">/mo</span></p>
            <ul className="text-sm mt-3 space-y-1">{(p.perks || []).map((perk, i) => <li key={i}>· {perk}</li>)}</ul>
            <Badge className="mt-3">{members.filter(m => m.planId === p.id).length} members</Badge>
          </CardContent></Card>
        ))}
      </div>
    </div>
  );
}
