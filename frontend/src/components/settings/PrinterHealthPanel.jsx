import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Printer } from 'lucide-react';
import { coursingAPI } from '../../services/api';
import { toast } from 'sonner';

/**
 * Pre-service check for station printers.
 *
 * A printer that's off or unplugged fails one docket at a time in the middle
 * of service, which is the worst possible moment to find out. This turns that
 * into something you check at 4pm.
 */
export default function PrinterHealthPanel() {
  const [health, setHealth] = useState(null);
  const [checking, setChecking] = useState(false);

  const checkPrinters = async () => {
    setChecking(true);
    try {
      const r = await coursingAPI.printHealth();
      setHealth(r.data);
      const down = (r.data.printers || []).filter(p => p.reachable === false);
      if (down.length) toast.error(`${down.length} printer(s) unreachable`);
      else if ((r.data.printers || []).length) toast.success('All station printers reachable');
      else toast('No station printers configured — dockets use the browser dialog');
    } catch { toast.error('Could not check printers'); }
    finally { setChecking(false); }
  };

  const selfTest = async (printer) => {
    try {
      const r = await coursingAPI.printSelfTest(printer);
      if (r.data?.sent) toast.success(`Test page sent to ${printer}`);
      else toast.error(r.data?.error || `Could not reach ${printer}`);
    } catch (e) { toast.error(e.response?.data?.detail || 'Test failed'); }
  };

  return (
    <Card data-testid="printer-health-panel">
      <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center justify-between">
        <span className="flex items-center gap-2"><Printer size={16} /> Station Printers</span>
        <Button size="sm" variant="outline" className="h-7 text-xs" onClick={checkPrinters}
          disabled={checking} data-testid="check-printers">
          {checking ? 'Checking…' : 'Check all'}
        </Button>
      </CardTitle></CardHeader>
      <CardContent className="space-y-2">
        {health === null && (
          <p className="text-gray-400 text-xs text-center py-3">
            Run a check before service so a dead printer isn't discovered one docket at a time.
          </p>
        )}
        {health && health.printers.length === 0 && (
          <p className="text-gray-400 text-xs text-center py-3">
            No station printers configured — dockets use the browser print dialog.
          </p>
        )}
        {(health?.printers || []).map(p => (
          <div key={p.printer} className="flex items-center gap-2 p-2 rounded-lg border"
            data-testid={`printer-${p.printer}`}>
            <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
              p.reachable === true ? 'bg-emerald-500'
              : p.reachable === false ? 'bg-red-500' : 'bg-gray-300'}`} />
            <span className="text-sm font-medium flex-1 truncate">{p.printer}</span>
            <span className="text-[10px] text-gray-500">
              {p.host ? `${p.host}:${p.port}` : 'no device'}
            </span>
            {p.reachable === true && (
              <Badge className="text-[10px] bg-emerald-100 text-emerald-700">{p.latencyMs}ms</Badge>
            )}
            {p.reachable === false && (
              <Badge className="text-[10px] bg-red-100 text-red-700" title={p.error}>unreachable</Badge>
            )}
            {p.host && (
              <Button size="sm" variant="outline" className="h-6 text-[10px]"
                onClick={() => selfTest(p.printer)} data-testid={`selftest-${p.printer}`}>
                Test page
              </Button>
            )}
          </div>
        ))}
        {health && health.printers.length > 0 && (
          <p className="text-[10px] text-gray-500 pt-1">
            A test page prints the column ruler and accented characters, so a wrong
            width or codepage shows on the paper instead of being guessed at.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
