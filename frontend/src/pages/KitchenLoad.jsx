import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { aiWave2API } from '../services/api';
import { useToast } from '../hooks/use-toast';
import { useTheme } from '../contexts/ThemeContext';
import { ChefHat, RefreshCw, AlertCircle, ArrowRight } from 'lucide-react';

export default function KitchenLoad() {
  const { theme } = useTheme();
  const { toast } = useToast();
  const [data, setData] = useState({ stations: [], suggestions: [] });
  const [loading, setLoading] = useState(true);

  const fetch = async () => {
    setLoading(true);
    try { const r = await aiWave2API.kitchenLoad(); setData(r.data || { stations: [], suggestions: [] }); }
    catch { toast({ title: 'Error', description: 'Failed to load kitchen state', variant: 'destructive' }); }
    finally { setLoading(false); }
  };
  useEffect(() => {
    fetch();
    const id = setInterval(fetch, 30000); // auto-refresh every 30s
    return () => clearInterval(id);
  }, []);

  const maxItems = Math.max(...data.stations.map(s => s.items), 1);

  return (
    <div className="space-y-6" data-testid="kitchen-load-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
            <ChefHat className="text-orange-600" /> Kitchen Load Balancing
          </h1>
          <p className="text-sm text-gray-500 mt-1">Live station load · auto-refresh every 30s</p>
        </div>
        <Button onClick={fetch} variant="outline" data-testid="kload-refresh"><RefreshCw size={14} className="mr-1.5" /> Refresh</Button>
      </div>

      {loading ? <div className="text-center py-20 text-gray-400">Reading kitchen…</div> : (
        <>
          {data.suggestions.length > 0 && (
            <Card className="border-amber-200 bg-amber-50">
              <CardContent className="p-5">
                <h2 className="text-sm font-bold uppercase tracking-widest text-amber-800 mb-3 flex items-center gap-2"><AlertCircle size={14} /> Recommendations</h2>
                <div className="space-y-2" data-testid="suggestions">
                  {data.suggestions.map((s, i) => (
                    <div key={i} className="flex items-start gap-2 text-sm" data-testid={`suggestion-${i}`}>
                      {s.action === 'rebalance' ? (
                        <Badge className="bg-blue-100 text-blue-700 hover:bg-blue-100">
                          {s.from} <ArrowRight size={10} className="mx-1" /> {s.to}
                        </Badge>
                      ) : (
                        <Badge className="bg-red-100 text-red-700 hover:bg-red-100">{s.station}</Badge>
                      )}
                      <span className="text-amber-900">{s.reason}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="stations-grid">
            {data.stations.length === 0 ? (
              <div className="col-span-full text-center py-12 text-gray-400">All clear — no open tickets</div>
            ) : data.stations.map(s => {
              const hot = s.oldestWaitMin > 15;
              return (
                <Card key={s.station} className={hot ? 'border-red-300 shadow-red-100 shadow' : ''} data-testid={`station-${s.station}`}>
                  <CardContent className="p-5">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-bold">{s.station}</h3>
                      {hot && <Badge className="bg-red-100 text-red-700 hover:bg-red-100 text-[10px]">HOT</Badge>}
                    </div>
                    <div className="space-y-3">
                      <div>
                        <div className="flex items-baseline justify-between">
                          <span className="text-3xl font-bold">{s.items}</span>
                          <span className="text-xs text-gray-500">items</span>
                        </div>
                        <div className="h-2 bg-gray-100 rounded mt-1.5 overflow-hidden">
                          <div className="h-full transition-all" style={{ width: `${(s.items / maxItems) * 100}%`, background: hot ? '#dc2626' : theme.primary }} />
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-3 text-xs">
                        <div>
                          <div className="text-gray-500">Open Orders</div>
                          <div className="font-bold text-lg">{s.orders}</div>
                        </div>
                        <div>
                          <div className="text-gray-500">Oldest Wait</div>
                          <div className={`font-bold text-lg ${hot ? 'text-red-600' : ''}`}>{s.oldestWaitMin} min</div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
