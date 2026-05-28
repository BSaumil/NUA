import React, { useState, useEffect } from 'react';
import { Users } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { useTheme } from '../contexts/ThemeContext';
import { v15API } from '../services/api';

export default function CohortRetention() {
  const { theme } = useTheme();
  const [cohorts, setCohorts] = useState([]);

  useEffect(() => { v15API.getCohortRetention().then(r => setCohorts(r.data?.cohorts || [])).catch(() => {}); }, []);

  const cellColor = (rate) => {
    if (rate === 0) return '#f9fafb';
    const t = Math.min(rate / 100, 1);
    return `rgba(99,102,241,${0.1 + t * 0.8})`;
  };

  return (
    <div className="space-y-6" data-testid="cohort-page">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Users size={22} /> Customer Cohort Retention</h1>
        <p className="text-sm text-gray-500">% of each signup-month cohort that returned in subsequent months. Darker = better retention.</p>
      </div>
      <Card>
        <CardContent className="p-6 overflow-x-auto">
          <table className="text-xs" data-testid="cohort-table">
            <thead>
              <tr>
                <th className="p-2 text-left">Cohort</th>
                <th className="p-2">Size</th>
                {[0,1,2,3,4,5].map(m => <th key={m} className="p-2">M{m}</th>)}
              </tr>
            </thead>
            <tbody>
              {cohorts.map(c => (
                <tr key={c.cohort}>
                  <td className="p-2 font-semibold">{c.cohort}</td>
                  <td className="p-2 text-center text-gray-500">{c.size}</td>
                  {c.retention.map(r => (
                    <td key={r.month} className="p-0">
                      <div className="w-16 h-10 flex items-center justify-center font-medium text-[11px]" style={{ backgroundColor: cellColor(r.rate), color: r.rate > 50 ? 'white' : '#6b7280' }} data-testid={`cohort-${c.cohort}-${r.month}`}>
                        {r.rate}%
                      </div>
                    </td>
                  ))}
                </tr>
              ))}
              {cohorts.length === 0 && <tr><td colSpan="8" className="p-12 text-center text-gray-400">No cohort data yet. Add customers to start tracking retention.</td></tr>}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
