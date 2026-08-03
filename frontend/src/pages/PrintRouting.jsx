import React, { useState, useEffect } from 'react';
import { Printer, Plus, Trash2, Save, ArrowUp, ArrowDown, CheckCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { useTheme } from '../contexts/ThemeContext';
import { gamificationAPI, coursingAPI } from '../services/api';
import { toast } from 'sonner';
import { stationLabel, printDocket, groupByCategory } from '../services/docket';
import PrinterHealthPanel from '../components/settings/PrinterHealthPanel';

export default function PrintRouting() {
  const { theme } = useTheme();
  const [config, setConfig] = useState(null);
  const [queue, setQueue] = useState([]);
  const [newRoute, setNewRoute] = useState({ category: '', printer: '', priority: 2 });

  useEffect(() => {
    gamificationAPI.getPrintRouting()
      .then(r => {
        const cfg = r.data || {};
        // Defensive: if the backend somehow returns a legacy dict-shaped
        // `routes`, coerce here so `config.routes.map(...)` never crashes.
        if (cfg.routes && !Array.isArray(cfg.routes)) {
          cfg.routes = Object.entries(cfg.routes).map(([category, printer]) => ({
            category: String(category), printer: String(printer), priority: 2,
          }));
        }
        cfg.routes = Array.isArray(cfg.routes) ? cfg.routes : [];
        setConfig(cfg);
      })
      .catch(() => setConfig({ enabled: true, routes: [], defaultPrinter: '', defaultPriority: 2 }));
    gamificationAPI.getPrintQueue().then(r => setQueue(Array.isArray(r.data) ? r.data : [])).catch(() => {});
  }, []);

  const saveConfig = async () => {
    try { await gamificationAPI.savePrintRouting(config); toast.success('Print routing saved'); } catch { toast.error('Failed'); }
  };

  const addRoute = () => {
    if (!newRoute.category || !newRoute.printer) return;
    setConfig({ ...config, routes: [...(config.routes || []), { ...newRoute }] });
    setNewRoute({ category: '', printer: '', priority: 2 });
  };

  const removeRoute = (idx) => {
    const routes = [...config.routes]; routes.splice(idx, 1);
    setConfig({ ...config, routes });
  };

  /**
   * Print to the real station printer when one is configured, and fall back
   * to the browser dialog when it isn't — a venue that hasn't set up an IP
   * still prints exactly the way it does today.
   */
  const printJob = async (job) => {
    try {
      const r = await coursingAPI.printEscpos(job.id);
      if (r.data?.sent) {
        toast.success(`Sent to ${job.printer} (${r.data.bytes} bytes)`);
        setQueue(q => q.filter(j => j.id !== job.id));
        return;
      }
      toast(`${job.printer}: ${r.data?.reason || 'no device'} — using the browser dialog`);
    } catch {
      // Older backend or the endpoint is unreachable — browser it is.
    }
    printDocket(job);
  };

  const completeJob = async (id) => {
    try { await gamificationAPI.completePrintJob(id); setQueue(queue.filter(j => j.id !== id)); toast.success('Job completed'); } catch {}
  };

  if (!config) return <div className="flex justify-center py-12"><div className="animate-pulse text-gray-400">Loading...</div></div>;

  return (
    <div className="space-y-6" data-testid="print-routing-page">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold" style={{ color: theme.text }}>Print Routing</h1><p className="text-sm text-gray-500">Category-wise printer routing with priority</p></div>
        <Button onClick={saveConfig} style={{ backgroundColor: theme.primary }} data-testid="save-routing-btn"><Save size={16} className="mr-1" /> Save Configuration</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Routing Rules */}
        <Card><CardHeader><CardTitle className="text-sm">Category → Printer Routing</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {(config.routes || []).map((r, i) => (
            <div key={i} className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg" data-testid={`route-${i}`}>
              <Badge variant="outline" className="text-xs">{r.category}</Badge>
              <span className="text-gray-400">→</span>
              <span className="text-sm font-medium flex-1">{r.printer}</span>
              <Badge className={`text-[10px] ${r.priority === 1 ? 'bg-red-100 text-red-700' : r.priority === 2 ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'}`}>
                P{r.priority}
              </Badge>
              <Button variant="ghost" size="sm" className="text-red-500 h-7 w-7 p-0" onClick={() => removeRoute(i)}><Trash2 size={12} /></Button>
            </div>
          ))}
          <div className="flex gap-2 pt-2 border-t">
            <Input placeholder="Category" className="flex-1 h-8 text-sm" value={newRoute.category} onChange={e => setNewRoute({ ...newRoute, category: e.target.value })} data-testid="new-route-category" />
            <Input placeholder="Printer" className="flex-1 h-8 text-sm" value={newRoute.printer} onChange={e => setNewRoute({ ...newRoute, printer: e.target.value })} data-testid="new-route-printer" />
            <select className="h-8 text-sm border rounded px-2" value={newRoute.priority} onChange={e => setNewRoute({ ...newRoute, priority: parseInt(e.target.value) })}>
              <option value={1}>P1 (Rush)</option><option value={2}>P2 (Normal)</option><option value={3}>P3 (Low)</option>
            </select>
            <Button size="sm" variant="outline" className="h-8" onClick={addRoute} data-testid="add-route-btn"><Plus size={14} /></Button>
          </div>
          <div className="pt-2">
            <label className="text-xs font-medium text-gray-500">Default Printer</label>
            <Input className="h-8 text-sm mt-1" value={config.defaultPrinter || ''} onChange={e => setConfig({ ...config, defaultPrinter: e.target.value })} data-testid="default-printer" />
          </div>
        </CardContent></Card>

        <PrinterHealthPanel />

        {/* Live Print Queue */}
        <Card><CardHeader><CardTitle className="text-sm flex items-center gap-2"><Printer size={16} /> Print Queue</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {queue.length === 0 && <p className="text-gray-400 text-sm text-center py-6">No jobs in queue</p>}
          {queue.map(job => (
            <div key={job.id} className="p-3 border rounded-lg" data-testid={`job-${job.id}`}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Badge className={`text-[10px] ${job.priority === 1 ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>P{job.priority}</Badge>
                  <span className="text-sm font-medium">{job.printer}</span>
                </div>
                <div className="flex items-center gap-2">
                  {job.tableNumber && <Badge variant="outline" className="text-[10px]">Table {job.tableNumber}</Badge>}
                  <Button size="sm" variant="outline" className="h-6 text-xs" onClick={() => printJob(job)} data-testid={`print-${job.id}`}><Printer size={12} className="mr-1" /> Print</Button>
                  <Button size="sm" variant="outline" className="h-6 text-xs" onClick={() => completeJob(job.id)} data-testid={`complete-${job.id}`}><CheckCircle size={12} className="mr-1" /> Done</Button>
                </div>
              </div>
              {/* Own items, grouped by category — same order they print in. */}
              <div className="space-y-0.5">
                {groupByCategory(job.items).map((g, gi) => (
                  <div key={gi}>
                    <p className="text-[9px] uppercase tracking-wider text-gray-400 mt-1">{g.category}</p>
                    {g.items.map((item, i) => (
                      <p key={i} className="text-xs text-gray-600">• {item.productName || item.name} x{item.quantity}</p>
                    ))}
                  </div>
                ))}
              </div>
              {/* Every section this order fires from — own station highlighted,
                  so each station sees what else is coming and from where. */}
              {(job.orderStations || []).length > 0 && (
                <div className="flex items-center gap-1 mt-2 pt-2 border-t border-dashed" data-testid={`sections-${job.id}`}>
                  <span className="text-[9px] uppercase tracking-wider text-gray-400">Sections:</span>
                  {job.orderStations.map((s, i) => (
                    <span key={i}
                      className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${stationLabel(s) === stationLabel(job.printer) ? 'bg-gray-900 text-white border-gray-900' : 'bg-white text-gray-600 border-gray-300'}`}>
                      {stationLabel(s)}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </CardContent></Card>
      </div>
    </div>
  );
}
