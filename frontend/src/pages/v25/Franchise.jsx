import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { v25API } from '../../services/api';
import { useTheme } from '../../contexts/ThemeContext';
import { Building2, Plus } from 'lucide-react';

export default function Franchise() {
  const { theme } = useTheme();
  const [data, setData] = useState({ sites: [], recentPublications: [] });
  const [bench, setBench] = useState([]);
  const load = () => {
    v25API.franchiseDashboard().then(r => setData(r.data || { sites: [], recentPublications: [] }));
    v25API.benchmark().then(r => setBench(r.data || []));
  };
  useEffect(() => { load(); }, []);
  const add = async () => {
    const name = prompt('Site name?'); if (!name) return;
    const city = prompt('City?') || '';
    await v25API.addSite({ name, city }); load();
  };
  return (
    <div className="space-y-6" data-testid="franchise-page">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Building2 className="text-blue-600" /> Franchise Command Center</h1>
        <Button onClick={add} style={{ background: theme.primary }} data-testid="add-site"><Plus size={14} className="mr-1.5" /> Add Site</Button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {data.sites.map(s => <Card key={s.id} data-testid={`site-${s.id}`}><CardContent className="p-5"><p className="font-bold">{s.name}</p><p className="text-xs text-gray-500">{s.city}</p><Badge variant="outline" className="mt-2">{s.active ? 'active' : 'inactive'}</Badge></CardContent></Card>)}
      </div>
      <Card><CardContent className="p-0">
        <div className="px-5 py-3 border-b font-bold">Multi-Store Benchmark</div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500"><tr><th className="text-left px-5 py-3">Site</th><th className="text-right px-5 py-3">Revenue</th><th className="text-right px-5 py-3">Food %</th><th className="text-right px-5 py-3">Labour %</th><th className="text-right px-5 py-3">Guest Sat</th></tr></thead>
          <tbody>{bench.map(b => <tr key={b.siteId} className="border-t"><td className="px-5 py-3 font-medium">{b.siteName}</td><td className="px-5 py-3 text-right">${b.revenue.toLocaleString()}</td><td className="px-5 py-3 text-right">{b.foodCostPct}%</td><td className="px-5 py-3 text-right">{b.labourPct}%</td><td className="px-5 py-3 text-right">{b.guestSat} ★</td></tr>)}</tbody>
        </table>
      </CardContent></Card>
    </div>
  );
}
