import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { v25API } from '../../services/api';
import { useTheme } from '../../contexts/ThemeContext';
import { useToast } from '../../hooks/use-toast';
import { Star } from 'lucide-react';

export default function Reputation() {
  const { theme } = useTheme(); const { toast } = useToast();
  const [data, setData] = useState(null);
  const load = () => v25API.reputation().then(r => setData(r.data));
  useEffect(() => { load(); }, []);
  const respond = async (id) => { await v25API.respondReview(id, ''); toast({ title: 'AI response drafted' }); load(); };
  return (
    <div className="space-y-6" data-testid="reputation-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Star className="text-yellow-500" /> Reputation Center</h1>
      {data && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card><CardContent className="p-5"><p className="text-xs uppercase text-gray-500">Average</p><p className="text-3xl font-bold">{data.avgRating} ★</p></CardContent></Card>
            {data.bySource.map(s => <Card key={s.source}><CardContent className="p-5"><p className="text-xs uppercase text-gray-500">{s.source}</p><p className="text-3xl font-bold">{s.avg}</p><p className="text-xs text-gray-400">{s.count} reviews</p></CardContent></Card>)}
          </div>
          <div className="space-y-2">
            {data.reviews.map(r => (
              <Card key={r.id} data-testid={`review-${r.id}`}><CardContent className="p-4">
                <div className="flex justify-between"><p className="font-medium">{r.author} · {r.source}</p><Badge className={r.rating >= 4 ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}>{r.rating}★</Badge></div>
                <p className="text-sm mt-1 text-gray-700">{r.text}</p>
                {r.response && <p className="text-xs mt-2 italic text-gray-500">Reply: {r.response}</p>}
                {!r.responded && <Button size="sm" variant="outline" className="mt-2" onClick={() => respond(r.id)} data-testid={`respond-${r.id}`}>Draft AI Response</Button>}
              </CardContent></Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
