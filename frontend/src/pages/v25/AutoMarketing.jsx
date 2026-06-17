import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { v25API } from '../../services/api';
import { useTheme } from '../../contexts/ThemeContext';
import { useToast } from '../../hooks/use-toast';
import { Sparkles } from 'lucide-react';

export default function AutoMarketing() {
  const { theme } = useTheme(); const { toast } = useToast();
  const [campaigns, setCampaigns] = useState([]);
  const [running, setRunning] = useState(false);
  const load = () => v25API.listMarketing().then(r => setCampaigns(r.data || []));
  useEffect(() => { load(); }, []);
  const run = async (aud) => {
    setRunning(true);
    try { await v25API.autoMarketing(aud); toast({ title: 'Campaign drafted' }); await load(); }
    catch { toast({ title: 'Error', variant: 'destructive' }); }
    finally { setRunning(false); }
  };
  return (
    <div className="space-y-6" data-testid="auto-marketing-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Sparkles className="text-pink-600" /> Autonomous Marketing</h1>
      <div className="flex gap-2 flex-wrap">
        {['all', 'VIP', 'Gold', 'Silver'].map(a => (
          <Button key={a} onClick={() => run(a)} disabled={running} variant="outline" data-testid={`run-${a}`}>{running ? 'Drafting…' : `Run for ${a}`}</Button>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="campaigns-list">
        {campaigns.map(c => (
          <Card key={c.id} data-testid={`campaign-${c.id}`}>
            <CardContent className="p-5">
              <div className="flex items-center justify-between mb-2"><Badge>{c.audience}</Badge><span className="text-xs text-gray-500">{c.recipients} recipients</span></div>
              <p className="font-semibold">{c.emailSubject}</p>
              <p className="text-sm text-gray-600 mt-1">{c.emailBody}</p>
              <p className="text-xs text-gray-500 mt-2 italic">SMS: {c.sms}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
