import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, AlertTriangle, Sparkles, Loader2, BarChart3 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { useTheme } from '../contexts/ThemeContext';
import { gamificationAPI } from '../services/api';
import { toast } from 'sonner';

export default function QuarterlyReview() {
  const { theme } = useTheme();
  const [data, setData] = useState(null);
  const [aiSuggestions, setAiSuggestions] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);

  useEffect(() => { gamificationAPI.getQuarterlyReview().then(r => setData(r.data)).catch(() => {}); }, []);

  const generateAlternatives = async () => {
    if (!data?.underperformers?.length && !data?.worstSellers?.length) { toast.info('No underperforming items'); return; }
    setAiLoading(true);
    try {
      const items = data.underperformers?.length ? data.underperformers : data.worstSellers;
      const res = await gamificationAPI.getAIAlternatives(items);
      setAiSuggestions(res.data);
    } catch { toast.error('Failed'); }
    setAiLoading(false);
  };

  if (!data) return <div className="flex justify-center py-12"><div className="animate-pulse text-gray-400">Loading quarterly review...</div></div>;

  return (
    <div className="space-y-6" data-testid="quarterly-review-page">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold" style={{ color: theme.text }}>Quarterly Menu Review</h1><p className="text-sm text-gray-500">Top/worst sellers with AI replacement suggestions</p></div>
        <Button onClick={generateAlternatives} disabled={aiLoading} style={{ backgroundColor: theme.primary }} data-testid="ai-alternatives-btn">
          {aiLoading ? <><Loader2 size={16} className="mr-1 animate-spin" /> Analyzing...</> : <><Sparkles size={16} className="mr-1" /> AI Alternatives</>}
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Top Sellers */}
        <Card><CardHeader><CardTitle className="text-sm flex items-center gap-2 text-emerald-700"><TrendingUp size={16} /> Top Sellers</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {(data.topSellers || []).map((item, i) => (
            <div key={i} className="flex items-center justify-between p-2 bg-emerald-50 rounded-lg" data-testid={`top-${i}`}>
              <div className="flex items-center gap-3">
                <div className="w-7 h-7 rounded-full bg-emerald-600 text-white flex items-center justify-center text-xs font-bold">{i + 1}</div>
                <div><p className="text-sm font-medium">{item.name}</p><p className="text-[10px] text-gray-500">{item.category} • {item.qtySold} sold</p></div>
              </div>
              <div className="text-right">
                <p className="text-sm font-bold text-emerald-700">${item.revenue.toFixed(2)}</p>
                <p className="text-[10px] text-gray-500">{item.margin}% margin</p>
              </div>
            </div>
          ))}
        </CardContent></Card>

        {/* Worst Sellers */}
        <Card><CardHeader><CardTitle className="text-sm flex items-center gap-2 text-red-700"><TrendingDown size={16} /> Worst Sellers</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {(data.worstSellers || []).map((item, i) => (
            <div key={i} className="flex items-center justify-between p-2 bg-red-50 rounded-lg" data-testid={`worst-${i}`}>
              <div className="flex items-center gap-3">
                <AlertTriangle size={16} className="text-red-500" />
                <div><p className="text-sm font-medium">{item.name}</p><p className="text-[10px] text-gray-500">{item.category} • {item.qtySold} sold</p></div>
              </div>
              <div className="text-right">
                <p className="text-sm font-bold text-red-600">${item.revenue.toFixed(2)}</p>
                <p className="text-[10px] text-gray-500">{item.margin}% margin</p>
              </div>
            </div>
          ))}
          {(!data.worstSellers || data.worstSellers.length === 0) && <p className="text-gray-400 text-sm text-center py-4">No data yet</p>}
        </CardContent></Card>
      </div>

      {/* Underperformers */}
      {data.underperformers?.length > 0 && (
        <Card className="border-amber-200"><CardHeader><CardTitle className="text-sm flex items-center gap-2 text-amber-700"><AlertTriangle size={16} /> Low Margin Items (under 20%)</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {data.underperformers.map((item, i) => (
              <div key={i} className="p-3 bg-amber-50 rounded-lg text-center">
                <p className="text-sm font-medium">{item.name}</p>
                <p className="text-xs text-amber-700">{item.margin}% margin</p>
                <p className="text-xs text-gray-500">${item.price} / cost: ${item.cost}</p>
              </div>
            ))}
          </div>
        </CardContent></Card>
      )}

      {/* AI Suggestions */}
      {aiSuggestions && (
        <Card className="border-violet-200"><CardHeader><CardTitle className="text-sm flex items-center gap-2 text-violet-700"><Sparkles size={16} /> AI Replacement Suggestions</CardTitle></CardHeader>
        <CardContent>
          <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap" data-testid="ai-suggestions-content">
            {aiSuggestions.suggestions}
          </div>
        </CardContent></Card>
      )}
    </div>
  );
}
