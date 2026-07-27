import React, { useState, useEffect } from 'react';
import { Trophy, TrendingUp, DollarSign, Clock, Target, Award, Star } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { useTheme } from '../contexts/ThemeContext';
import { gamificationAPI, advancedAPI } from '../services/api';
import { toast } from 'sonner';

const MEDALS = ['', '#FFD700', '#C0C0C0', '#CD7F32'];

export default function StaffLeaderboard() {
  const { theme } = useTheme();
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);
  const [distributing, setDistributing] = useState(false);

  const load = () => {
    setError(false);
    gamificationAPI.getLeaderboard().then(r => setData(r.data)).catch(() => setError(true));
  };
  useEffect(load, []);

  const handleSmartDistribute = async () => {
    setDistributing(true);
    try {
      const res = await gamificationAPI.smartDistributeTips();
      if (res.data.distributions) {
        toast.success(`Distributed $${res.data.poolTotal} to ${res.data.distributions.length} staff based on performance`);
      } else {
        toast.info(res.data.message);
      }
    } catch { toast.error('Failed'); }
    setDistributing(false);
  };

  if (error) return (
    <div className="flex flex-col items-center gap-3 py-12">
      <p className="text-gray-400">Couldn't load the leaderboard.</p>
      <Button variant="outline" onClick={load} data-testid="leaderboard-retry">Retry</Button>
    </div>
  );
  if (!data) return <div className="flex justify-center py-12"><div className="animate-pulse text-gray-400">Loading leaderboard...</div></div>;

  return (
    <div className="space-y-6" data-testid="leaderboard-page">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center bg-gradient-to-br from-amber-400 to-orange-500">
            <Trophy size={24} className="text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold" style={{ color: theme.text }}>Staff Leaderboard</h1>
            <p className="text-sm text-gray-500">Performance rankings & smart tip distribution</p>
          </div>
        </div>
        <Button onClick={handleSmartDistribute} disabled={distributing} style={{ backgroundColor: theme.primary }} data-testid="smart-distribute-btn">
          <DollarSign size={16} className="mr-1" /> Smart Tip Distribute
        </Button>
      </div>

      {/* Podium - Top 3 */}
      {data.leaderboard.length >= 3 && (
        <div className="grid grid-cols-3 gap-4">
          {[1, 0, 2].map(idx => {
            const s = data.leaderboard[idx];
            if (!s) return null;
            const isFirst = idx === 0;
            return (
              <Card key={s.id} className={`${isFirst ? 'ring-2 ring-amber-400 shadow-lg' : ''}`} data-testid={`podium-${s.rank}`}>
                <CardContent className="p-6 text-center">
                  <div className="w-16 h-16 mx-auto rounded-full flex items-center justify-center text-2xl font-bold text-white mb-3"
                    style={{ backgroundColor: MEDALS[s.rank] || theme.primary }}>
                    {s.rank === 1 ? <Trophy size={28} /> : s.rank}
                  </div>
                  <h3 className="font-bold text-lg">{s.name}</h3>
                  <Badge variant="outline" className="capitalize text-xs mt-1">{s.role}</Badge>
                  <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                    <div className="bg-gray-50 rounded p-2"><p className="text-gray-500">Sales</p><p className="font-bold">${s.totalSales}</p></div>
                    <div className="bg-gray-50 rounded p-2"><p className="text-gray-500">Tips</p><p className="font-bold text-emerald-600">${s.totalTips}</p></div>
                    <div className="bg-gray-50 rounded p-2"><p className="text-gray-500">$/Hour</p><p className="font-bold">${s.salesPerHour}</p></div>
                    <div className="bg-gray-50 rounded p-2"><p className="text-gray-500">Score</p><p className="font-bold" style={{ color: theme.primary }}>{s.performanceScore}</p></div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Full Leaderboard Table */}
      <Card><CardContent className="p-0"><div className="overflow-x-auto">
        <table className="w-full text-sm" data-testid="leaderboard-table">
          <thead className="bg-gray-50"><tr>
            <th className="text-left p-3 font-medium text-gray-500">Rank</th>
            <th className="text-left p-3 font-medium text-gray-500">Staff</th>
            <th className="text-right p-3 font-medium text-gray-500">Sales</th>
            <th className="text-right p-3 font-medium text-gray-500">Transactions</th>
            <th className="text-right p-3 font-medium text-gray-500">Tips</th>
            <th className="text-right p-3 font-medium text-gray-500">Hours</th>
            <th className="text-right p-3 font-medium text-gray-500">$/Hour</th>
            <th className="text-right p-3 font-medium text-gray-500">Score</th>
          </tr></thead>
          <tbody>
            {data.leaderboard.map(s => (
              <tr key={s.id} className="border-t hover:bg-gray-50" data-testid={`lb-row-${s.rank}`}>
                <td className="p-3">
                  <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white"
                    style={{ backgroundColor: MEDALS[s.rank] || '#6B7280' }}>{s.rank}</div>
                </td>
                <td className="p-3"><span className="font-medium">{s.name}</span> <Badge variant="outline" className="capitalize text-[10px] ml-1">{s.role}</Badge></td>
                <td className="p-3 text-right font-bold">${s.totalSales}</td>
                <td className="p-3 text-right">{s.totalTransactions}</td>
                <td className="p-3 text-right text-emerald-600">${s.totalTips}</td>
                <td className="p-3 text-right">{s.totalHours}h</td>
                <td className="p-3 text-right font-medium">${s.salesPerHour}</td>
                <td className="p-3 text-right font-bold" style={{ color: theme.primary }}>{s.performanceScore}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div></CardContent></Card>
    </div>
  );
}
