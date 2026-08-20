import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { GitPullRequest, RefreshCw, CheckCircle2, AlertTriangle, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { repoSyncAPI } from '../../services/api';

/**
 * Owner-only card: shows the daily GitHub auto-sync history so the platform's
 * "self-updating at 4am AEST" behaviour is visible on the dashboard rather
 * than buried behind an admin endpoint.
 */
export default function SyncHistoryCard() {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const r = await repoSyncAPI.status(5);
      setData(r.data);
    } catch { /* silently hide the card if not owner */ }
  };

  useEffect(() => { load(); }, []);

  const runNow = async () => {
    setBusy(true);
    try {
      const r = await repoSyncAPI.run();
      const d = r.data || {};
      if (d.status === 'ok' && (d.newCommits || 0) > 0) {
        toast.success(`Synced ${d.newCommits} new commit${d.newCommits === 1 ? '' : 's'}`);
      } else if (d.status === 'ok') {
        toast.info('Already up to date');
      } else {
        toast.error(`Sync failed: ${d.error || d.status}`);
      }
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Sync failed');
    } finally {
      setBusy(false);
    }
  };

  if (!data) return null;

  const rows = (data.recent || []).slice(0, 5);
  const lastOk = rows.find(r => r.status === 'ok');
  const totalCommits = rows.reduce((n, r) => n + (r.newCommits || 0), 0);

  return (
    <Card data-testid="sync-history-card">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2 text-indigo-600">
            <GitPullRequest size={14} /> Platform sync
            <Badge variant="outline" className="text-[10px] ml-1">
              {data.hourLocal?.toString().padStart(2, '0')}:00 {data.timezone?.split('/')[1]}
            </Badge>
          </CardTitle>
          <Button
            size="sm"
            variant="ghost"
            onClick={runNow}
            disabled={busy}
            data-testid="sync-run-now"
            className="h-7 text-xs"
          >
            <RefreshCw size={12} className={`mr-1 ${busy ? 'animate-spin' : ''}`} />
            {busy ? 'Syncing…' : 'Sync now'}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="text-xs space-y-1.5">
        {rows.length === 0 && (
          <div className="text-gray-500 py-2">
            No sync activity yet — the first automatic sync runs at 4am AEST.
          </div>
        )}
        {rows.length > 0 && lastOk && (
          <div className="rounded bg-indigo-50/60 border border-indigo-100 p-2 mb-1.5">
            <div className="flex items-center gap-1.5 text-indigo-700 font-medium">
              <Sparkles size={11} />
              {totalCommits > 0
                ? `${totalCommits} feature${totalCommits === 1 ? '' : 's'} shipped in the last ${rows.length} sync${rows.length === 1 ? '' : 's'}.`
                : 'Platform is fully up to date.'}
            </div>
          </div>
        )}
        {rows.map((r, idx) => {
          const ok = r.status === 'ok';
          return (
            <div key={idx} className="flex items-start gap-2 border-b pb-1.5 last:border-b-0" data-testid={`sync-row-${idx}`}>
              {ok ? (
                <CheckCircle2 size={12} className="text-emerald-500 mt-0.5 shrink-0" />
              ) : (
                <AlertTriangle size={12} className="text-amber-500 mt-0.5 shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{r.date}</span>
                  {(r.newCommits || 0) > 0 && (
                    <Badge className="bg-emerald-100 text-emerald-700 border border-emerald-200 text-[10px]">
                      +{r.newCommits} commit{r.newCommits === 1 ? '' : 's'}
                    </Badge>
                  )}
                  {!ok && <span className="text-amber-700">{r.status}</span>}
                </div>
                {r.note && <div className="text-gray-500 text-[11px]">{r.note}</div>}
                {r.error && <div className="text-red-600 text-[11px] truncate" title={r.error}>{r.error}</div>}
                {(r.sampleCommits || []).slice(0, 2).map((c, i) => (
                  <div key={i} className="text-gray-600 text-[11px] truncate" title={c}>
                    · {c.replace(/^[a-f0-9]{7,10}\s/, '')}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
