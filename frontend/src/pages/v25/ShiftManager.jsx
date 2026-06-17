import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { v25API } from '../../services/api';
import { useTheme } from '../../contexts/ThemeContext';
import { TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react';

export default function ShiftManager() {
  const { theme } = useTheme();
  const [data, setData] = useState({ alerts: [] });
  useEffect(() => {
    const tick = () => v25API.shiftManager().then(r => setData(r.data)).catch(() => {});
    tick(); const id = setInterval(tick, 30000); return () => clearInterval(id);
  }, []);
  return (
    <div className="space-y-6" data-testid="shift-manager-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><TrendingUp className="text-orange-600" /> AI Shift Manager</h1>
      <p className="text-sm text-gray-500">Real-time intervention alerts · auto-refresh every 30s</p>
      <div className="space-y-2">
        {data.alerts.length === 0 ? <Card><CardContent className="p-8 text-center text-emerald-600"><CheckCircle className="mx-auto mb-2" /> Service running smoothly</CardContent></Card> :
          data.alerts.map((a, i) => (
            <Card key={i} className={a.severity === 'high' ? 'border-red-300' : 'border-amber-300'} data-testid={`alert-${i}`}>
              <CardContent className="p-4 flex items-start gap-3">
                <AlertTriangle className={a.severity === 'high' ? 'text-red-600' : 'text-amber-600'} />
                <div className="flex-1"><p className="font-medium">{a.message}</p><Badge variant="outline" className="mt-1 text-[10px]">{a.type}</Badge></div>
              </CardContent>
            </Card>
          ))}
      </div>
    </div>
  );
}
