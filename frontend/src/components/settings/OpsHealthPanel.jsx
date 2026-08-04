import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { useTheme } from '../../contexts/ThemeContext';
import { opsAPI } from '../../services/api';
import { Activity, AlertTriangle, RefreshCw, CheckCircle2, XCircle, HelpCircle } from 'lucide-react';

/**
 * "Is the backend okay" for someone who has never opened a terminal.
 *
 * Before this there was no way for an owner to know a background job had
 * been silently failing since 3am other than a vague sense that something
 * felt off — the only record of an unhandled exception was whatever
 * terminal happened to be tailing stdout at that exact second.
 */
const statusIcon = (ok) => {
  if (ok === true) return <CheckCircle2 size={16} className="text-green-500" />;
  if (ok === false) return <XCircle size={16} className="text-red-500" />;
  return <HelpCircle size={16} className="text-gray-400" />;
};

export default function OpsHealthPanel() {
  const { theme } = useTheme();
  const [health, setHealth] = useState(null);
  const [errors, setErrors] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try { setHealth((await opsAPI.health()).data); } catch { setHealth({ status: 'unreachable', checks: {} }); }
    try { setErrors((await opsAPI.recentErrors(25)).data.errors); } catch { /* silent — owner-only, might 403 */ }
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const card = { backgroundColor: theme.cardBg || theme.background, color: theme.text };
  const healthy = health?.status === 'ok';

  return (
    <div className="space-y-4" data-testid="ops-health-panel">
      <Card style={card}>
        <CardContent className="p-6 space-y-4">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-3">
              <Activity size={22} className={healthy ? 'text-green-500' : 'text-amber-500'} />
              <div>
                <h3 className="font-bold text-lg">System health</h3>
                <p className="text-sm opacity-70">
                  {health ? `Checked ${new Date(health.time || Date.now()).toLocaleTimeString()}` : 'Checking…'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={healthy ? 'default' : 'secondary'} data-testid="ops-health-status">
                {health?.status || 'unknown'}
              </Badge>
              <Button size="sm" variant="outline" onClick={load} disabled={loading} data-testid="ops-refresh">
                <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              </Button>
            </div>
          </div>

          {health?.checks && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {Object.entries(health.checks).map(([name, check]) => (
                <div key={name} className="flex items-center gap-2 text-sm rounded-lg p-3"
                     style={{ backgroundColor: theme.background }}>
                  {statusIcon(check.ok)}
                  <span className="capitalize">{name.replace(/([A-Z])/g, ' $1').trim()}</span>
                  {typeof check.latencyMs === 'number' && (
                    <span className="ml-auto opacity-60 text-xs">{check.latencyMs}ms</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card style={card}>
        <CardContent className="p-6">
          <h3 className="font-bold mb-1 flex items-center gap-2">
            <AlertTriangle size={18} /> Recent errors
          </h3>
          <p className="text-sm opacity-70 mb-3">
            Unhandled backend errors from the last 30 days, newest first. Quote the request ID
            if you're asking for help with one of these.
          </p>
          {errors === null && <p className="text-sm opacity-60">Loading…</p>}
          {errors && errors.length === 0 && (
            <p className="text-sm opacity-60">None recorded. That's the good outcome.</p>
          )}
          {errors && errors.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left opacity-60 border-b" style={{ borderColor: theme.border || '#e5e7eb' }}>
                    <th className="py-2 pr-3">When</th>
                    <th className="py-2 pr-3">Path</th>
                    <th className="py-2 pr-3">Error</th>
                    <th className="py-2 pr-3">Request ID</th>
                  </tr>
                </thead>
                <tbody>
                  {errors.map(e => (
                    <tr key={e.requestId} className="border-b" style={{ borderColor: theme.border || '#f3f4f6' }}>
                      <td className="py-2 pr-3 whitespace-nowrap">{new Date(e.at).toLocaleString()}</td>
                      <td className="py-2 pr-3 font-mono text-xs">{e.method} {e.path}</td>
                      <td className="py-2 pr-3">{e.error}</td>
                      <td className="py-2 pr-3 font-mono text-xs opacity-60 select-all">{e.requestId}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
