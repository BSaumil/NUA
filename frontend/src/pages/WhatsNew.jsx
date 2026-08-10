import React, { useState, useEffect, useCallback } from 'react';
import { changelogAPI } from '../services/api';
import { toast } from 'sonner';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs';
import { Sparkles, Wrench, Bug, Shield, Rocket, Calendar } from 'lucide-react';

const CATEGORY_META = {
  feature: { label: 'New', icon: Sparkles, className: 'bg-emerald-100 text-emerald-700' },
  improvement: { label: 'Improved', icon: Wrench, className: 'bg-blue-100 text-blue-700' },
  fix: { label: 'Fixed', icon: Bug, className: 'bg-amber-100 text-amber-700' },
  security: { label: 'Security', icon: Shield, className: 'bg-rose-100 text-rose-700' },
};

const AUDIENCE_LABEL = { owner: 'Admin', staff: 'Staff', guest: 'Guest-facing' };

function EntryCard({ entry }) {
  const meta = CATEGORY_META[entry.category] || CATEGORY_META.feature;
  const Icon = meta.icon;
  return (
    <Card data-testid={`changelog-entry-${entry.id}`}>
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${meta.className}`}>
            <Icon size={16} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-semibold">{entry.title}</h3>
              <Badge className={`text-[10px] ${meta.className}`}>{meta.label}</Badge>
              <Badge variant="outline" className="text-[10px]">{entry.area}</Badge>
              {entry.audience !== 'owner' && (
                <Badge variant="outline" className="text-[10px] text-slate-500">{AUDIENCE_LABEL[entry.audience]}</Badge>
              )}
            </div>
            <p className="text-sm text-slate-500 mt-1">{entry.description}</p>
            {entry.releasedAt && (
              <p className="text-xs text-slate-400 mt-1.5 flex items-center gap-1">
                <Calendar size={11} /> {new Date(entry.releasedAt).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function WhatsNew() {
  const [tab, setTab] = useState('week');
  const [entries, setEntries] = useState([]);
  const [upcoming, setUpcoming] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (which) => {
    setLoading(true);
    try {
      if (which === 'upcoming') {
        setUpcoming((await changelogAPI.upcoming()).data);
      } else {
        const windowParam = which === 'all' ? undefined : which;
        setEntries((await changelogAPI.list(windowParam)).data);
      }
    } catch { toast.error("Could not load what's new"); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(tab); }, [tab, load]);
  useEffect(() => {
    changelogAPI.summary().then(r => setSummary(r.data)).catch(() => {});
  }, []);

  return (
    <div className="space-y-4" data-testid="whats-new-page">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2"><Rocket size={22} /> What's New</h1>
        <p className="text-sm text-slate-500">Everything that's shipped in NUA POS recently, and what's coming next.</p>
      </div>

      {summary && (
        <div className="grid grid-cols-3 gap-3">
          <Card><CardContent className="p-3 text-center">
            <p className="text-xl font-bold" data-testid="summary-this-week">{summary.thisWeek}</p>
            <p className="text-[11px] text-slate-500 uppercase tracking-wide">This week</p>
          </CardContent></Card>
          <Card><CardContent className="p-3 text-center">
            <p className="text-xl font-bold" data-testid="summary-this-month">{summary.thisMonth}</p>
            <p className="text-[11px] text-slate-500 uppercase tracking-wide">This month</p>
          </CardContent></Card>
          <Card><CardContent className="p-3 text-center">
            <p className="text-xl font-bold text-violet-600" data-testid="summary-upcoming">{summary.upcoming}</p>
            <p className="text-[11px] text-slate-500 uppercase tracking-wide">Upcoming</p>
          </CardContent></Card>
        </div>
      )}

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="week" data-testid="tab-week">This Week</TabsTrigger>
          <TabsTrigger value="month" data-testid="tab-month">This Month</TabsTrigger>
          <TabsTrigger value="all" data-testid="tab-all">All Time</TabsTrigger>
          <TabsTrigger value="upcoming" data-testid="tab-upcoming">Upcoming</TabsTrigger>
        </TabsList>

        {['week', 'month', 'all'].map(w => (
          <TabsContent key={w} value={w} className="space-y-2 mt-3">
            {loading && <p className="text-center text-slate-400 py-8">Loading…</p>}
            {!loading && entries.length === 0 && (
              <Card className="border-dashed"><CardContent className="p-8 text-center text-slate-400">
                Nothing shipped in this window yet.
              </CardContent></Card>
            )}
            {!loading && entries.map(e => <EntryCard key={e.id} entry={e} />)}
          </TabsContent>
        ))}

        <TabsContent value="upcoming" className="space-y-2 mt-3">
          {loading && <p className="text-center text-slate-400 py-8">Loading…</p>}
          {!loading && upcoming.length === 0 && (
            <Card className="border-dashed"><CardContent className="p-8 text-center text-slate-400">
              Nothing on the roadmap right now.
            </CardContent></Card>
          )}
          {!loading && upcoming.map(e => <EntryCard key={e.id} entry={e} />)}
        </TabsContent>
      </Tabs>
    </div>
  );
}
