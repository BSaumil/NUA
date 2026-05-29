import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { aiWave2API } from '../services/api';
import { useToast } from '../hooks/use-toast';
import { useTheme } from '../contexts/ThemeContext';
import { Users, RefreshCw, TrendingUp } from 'lucide-react';

export default function LaborForecast() {
  const { theme } = useTheme();
  const { toast } = useToast();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedDay, setSelectedDay] = useState(0);

  const fetch = async () => {
    setLoading(true);
    try { const r = await aiWave2API.laborForecast(); setData(r.data); }
    catch { toast({ title: 'Error', description: 'Failed to load forecast', variant: 'destructive' }); }
    finally { setLoading(false); }
  };
  useEffect(() => { fetch(); }, []);

  const day = data?.forecast?.[selectedDay];
  const maxStaff = day ? Math.max(...day.hours.map(h => h.total), 1) : 1;

  return (
    <div className="space-y-6" data-testid="labor-forecast-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
            <Users className="text-indigo-600" /> Predictive Labor Forecast
          </h1>
          <p className="text-sm text-gray-500 mt-1">Next 7 days · based on {data?.weeks_analyzed || 8} weeks of history</p>
        </div>
        <Button onClick={fetch} variant="outline" data-testid="forecast-refresh"><RefreshCw size={14} className="mr-1.5" /> Refresh</Button>
      </div>

      {loading ? (
        <div className="text-center py-20 text-gray-400">Forecasting…</div>
      ) : data?.forecast ? (
        <>
          <div className="flex gap-2 overflow-x-auto" data-testid="day-tabs">
            {data.forecast.map((d, i) => (
              <button key={d.date} onClick={() => setSelectedDay(i)}
                className={`flex-shrink-0 px-4 py-2.5 rounded-xl border transition-all min-w-[110px] text-left ${selectedDay === i ? 'border-transparent text-white shadow-md' : 'border-gray-200 bg-white hover:border-gray-300'}`}
                style={selectedDay === i ? { background: theme.primary } : {}}
                data-testid={`day-tab-${i}`}>
                <div className="text-[10px] uppercase tracking-widest opacity-70">{d.dayOfWeek.slice(0, 3)}</div>
                <div className="font-bold text-sm">{d.date.slice(5)}</div>
                <div className={`text-xs ${selectedDay === i ? 'text-white/80' : 'text-gray-500'}`}>{d.totalStaffHours}h</div>
              </button>
            ))}
          </div>

          {day && (
            <Card>
              <CardContent className="p-5">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="font-bold text-lg">{day.dayOfWeek} · {day.date}</h2>
                    <p className="text-xs text-gray-500">Peak hour: {day.peakHour}:00 · Total staff-hours: {day.totalStaffHours}</p>
                  </div>
                  <TrendingUp className="text-emerald-500" />
                </div>
                <div className="space-y-2" data-testid="hour-block">
                  {day.hours.map(h => (
                    <div key={h.hour} className="flex items-center gap-3" data-testid={`hour-${h.hour}`}>
                      <span className="text-xs font-mono w-12 text-gray-500">{String(h.hour).padStart(2, '0')}:00</span>
                      <div className="flex-1 bg-gray-100 rounded h-7 relative overflow-hidden">
                        <div className="h-full transition-all flex items-center px-2 text-[11px] text-white font-medium"
                          style={{ width: `${(h.total / maxStaff) * 100}%`, background: theme.primary }}>
                          {h.total > 0 ? `${h.foh}F + ${h.boh}B` : ''}
                        </div>
                      </div>
                      <span className="text-xs text-gray-500 w-24 text-right">{h.avgOrders} orders</span>
                      <span className="text-xs text-gray-400 w-24 text-right">${h.avgRevenue.toFixed(0)}</span>
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
