import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { v25API } from '../services/api';
import { useToast } from '../hooks/use-toast';
import { useTheme } from '../contexts/ThemeContext';
import { Brain, CheckCircle, AlertCircle, Zap, TrendingUp, RefreshCw } from 'lucide-react';

export default function AshPro() {
  const { theme } = useTheme();
  const { toast } = useToast();
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);

  const fetchPlan = async () => {
    setLoading(true);
    try { const r = await v25API.ashPlan(); setPlan(r.data); }
    catch { toast({ title: 'Failed to load plan', variant: 'destructive' }); }
    finally { setLoading(false); }
  };
  useEffect(() => { fetchPlan(); }, []);

  const approve = async (actionIds = []) => {
    if (!plan) return;
    setExecuting(true);
    try {
      const r = await v25API.ashApprove(plan.id, actionIds);
      toast({ title: 'Executed', description: `${r.data.executed} action(s) approved` });
      await fetchPlan();
    } catch (e) { toast({ title: 'Failed', description: e?.response?.data?.detail || 'Approval failed', variant: 'destructive' }); }
    finally { setExecuting(false); }
  };

  return (
    <div className="space-y-6" data-testid="ash-pro-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
            <Brain className="text-violet-600" /> Ash Pro · AI General Manager
          </h1>
          <p className="text-sm text-gray-500 mt-1">One-click execution of Ash's daily plan</p>
        </div>
        <Button onClick={fetchPlan} variant="outline" data-testid="ash-refresh"><RefreshCw size={14} className="mr-1.5" /> New Plan</Button>
      </div>

      {loading ? <div className="text-center py-20 text-gray-400">Generating today's plan…</div> : plan ? (
        <>
          <Card>
            <CardContent className="p-5">
              <h2 className="font-bold mb-3">Signals</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div><p className="text-xs text-gray-500">Today's Tx</p><p className="text-2xl font-bold">{plan.signals.todaysTransactions}</p></div>
                <div><p className="text-xs text-gray-500">Bookings Today</p><p className="text-2xl font-bold">{plan.signals.bookingsToday}</p></div>
                <div><p className="text-xs text-gray-500">Booking Δ vs 7d ago</p><p className={`text-2xl font-bold ${plan.signals.bookingDeltaPct < 0 ? 'text-red-600' : 'text-emerald-600'}`}>{plan.signals.bookingDeltaPct}%</p></div>
                <div><p className="text-xs text-gray-500">Low Stock</p><p className="text-2xl font-bold">{plan.signals.lowStockItems}</p></div>
              </div>
            </CardContent>
          </Card>

          {plan.actions.length === 0 ? (
            <Card className="border-emerald-200 bg-emerald-50">
              <CardContent className="p-6 text-center text-emerald-700">
                <CheckCircle className="mx-auto mb-2" />
                <p className="font-medium">No actions needed — operations on track.</p>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="p-5">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="font-bold">Recommended Actions</h2>
                  <Button onClick={() => approve([])} disabled={executing} style={{ background: theme.primary }} data-testid="approve-all">
                    <Zap size={14} className="mr-1.5" /> {executing ? 'Executing…' : 'Approve All'}
                  </Button>
                </div>
                <div className="space-y-2" data-testid="actions-list">
                  {plan.actions.map(a => (
                    <div key={a.id} className="flex items-start gap-3 p-3 border rounded-lg hover:bg-gray-50" data-testid={`action-${a.id}`}>
                      <AlertCircle className="text-amber-500 flex-shrink-0 mt-0.5" size={16} />
                      <div className="flex-1">
                        <p className="font-medium">{a.summary}</p>
                        <p className="text-xs text-gray-500 mt-0.5"><TrendingUp size={10} className="inline mr-1" /> {a.impact}</p>
                      </div>
                      <Badge variant="outline">{a.type}</Badge>
                      <Button size="sm" variant="outline" onClick={() => approve([a.id])} disabled={executing}>Approve</Button>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      ) : null}
    </div>
  );
}
