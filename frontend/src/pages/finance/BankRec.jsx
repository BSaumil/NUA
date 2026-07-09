import React, { useState, useEffect, useCallback } from 'react';
import { financeAPI } from '../../services/api';
import { toast } from 'sonner';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '../../components/ui/select';
import { FMT, today } from './helpers';

const BankRec = () => {
  const [accounts, setAccounts] = useState([]);
  const [code, setCode] = useState('1000');
  const [rows, setRows] = useState([]);

  useEffect(() => {
    financeAPI.listAccounts().then(r => setAccounts(r.data.filter(a => a.isBank)));
  }, []);

  const load = useCallback(async () => {
    try { setRows((await financeAPI.bankStatement(code)).data); }
    catch { toast.error('Failed to load'); }
  }, [code]);
  useEffect(() => { load(); }, [load]);

  const importSample = async () => {
    const sample = {
      accountCode: code,
      lines: [
        { statementDate: today(), description: 'Card settlement', amount: 121, externalId: `demo-${Date.now()}` },
      ],
    };
    try { await financeAPI.importBank(sample); toast.success('Sample line imported'); load(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  const match = async (lineId, jid) => {
    try { await financeAPI.matchBank(lineId, jid); toast.success('Matched'); load(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };
  const ignore = async (lineId) => {
    try { await financeAPI.ignoreBank(lineId); toast.success('Ignored'); load(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  return (
    <div className="space-y-4" data-testid="bank-rec-page">
      <div className="flex gap-2 items-center">
        <Select value={code} onValueChange={setCode}>
          <SelectTrigger className="w-64" data-testid="bank-account-select"><SelectValue /></SelectTrigger>
          <SelectContent>
            {accounts.map(a => <SelectItem key={a.code} value={a.code}>{a.code} — {a.name}</SelectItem>)}
          </SelectContent>
        </Select>
        <Button size="sm" variant="outline" onClick={importSample} data-testid="bank-import-sample">Import demo line</Button>
      </div>
      <Card><CardContent className="p-0">
        <table className="w-full text-sm">
          <thead className="bg-slate-50"><tr>
            <th className="p-2 pl-4 text-left text-xs text-slate-500">Date</th>
            <th className="p-2 text-left text-xs text-slate-500">Description</th>
            <th className="p-2 text-right text-xs text-slate-500">Amount</th>
            <th className="p-2 text-left text-xs text-slate-500">Suggested match</th>
            <th className="p-2 pr-4 text-center text-xs text-slate-500">Actions</th>
          </tr></thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.id} className="border-t">
                <td className="p-2 pl-4">{r.statementDate}</td>
                <td className="p-2">{r.description}</td>
                <td className={`p-2 text-right ${r.amount >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>{FMT(r.amount)}</td>
                <td className="p-2 text-xs text-slate-500">
                  {r.matchedJournalLineId ? <Badge className="bg-emerald-500">Matched</Badge> :
                    r.ignored ? <Badge variant="outline">Ignored</Badge> :
                    (r.suggestedMatches?.[0] ? <span>{r.suggestedMatches[0].journalNumber} · {r.suggestedMatches[0].memo}</span> : '—')}
                </td>
                <td className="p-2 pr-4 text-center">
                  {!r.matchedJournalLineId && !r.ignored && r.suggestedMatches?.[0] && (
                    <Button size="sm" variant="ghost" onClick={() => match(r.id, r.suggestedMatches[0].journalId)} data-testid={`bank-match-${r.id.slice(0,6)}`}>Match</Button>
                  )}
                  {!r.matchedJournalLineId && !r.ignored && (
                    <Button size="sm" variant="ghost" className="text-slate-400" onClick={() => ignore(r.id)}>Ignore</Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="text-center text-slate-400 py-8">No statement lines. Import a bank export or use demo.</p>}
      </CardContent></Card>
    </div>
  );
};

export default BankRec;
