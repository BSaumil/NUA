import React, { useMemo } from 'react';
import { Input } from '../ui/input';
import { AlertCircle, Check, MapPin } from 'lucide-react';
import { validateTable, suggestTables } from '../../lib/tableNumber';

const STATUS_TONE = {
  ok:      { border: '#10b981', text: '#047857' },
  unknown: { border: '#ef4444', text: '#b91c1c' },
};

/**
 * Dine-in table entry that validates against the floor plan as you type.
 *
 * A wrong table number is silent damage — the food goes out, the docket says
 * table 9, and nobody finds out until a guest is waiting. So an unrecognised
 * number is surfaced immediately and the caller blocks checkout on it, rather
 * than letting the order through and hoping someone notices.
 */
export default function TableNumberField({
  value, onChange, tables = [], configured = false, disabled = false,
}) {
  const result = useMemo(
    () => validateTable(value, tables, configured),
    [value, tables, configured]
  );
  const suggestions = useMemo(
    () => (result.status === 'unknown' ? suggestTables(value, tables) : []),
    [result.status, value, tables]
  );
  const tone = STATUS_TONE[result.status];
  const listId = 'pos-floor-tables';

  return (
    <div className="flex flex-col gap-1" data-testid="table-row">
      <div className="flex gap-2 items-center">
        <span className="text-xs text-gray-500 whitespace-nowrap">Table #</span>
        <div className="relative flex-1">
          <Input
            list={configured ? listId : undefined}
            placeholder={configured ? 'Type or pick a table' : 'e.g. 12, Patio-A, Bar-3'}
            value={value}
            disabled={disabled}
            onChange={e => onChange(e.target.value)}
            className="h-8 text-xs pr-7"
            style={tone ? { borderColor: tone.border } : undefined}
            aria-invalid={result.status === 'unknown'}
            data-testid="table-input"
            data-table-status={result.status}
          />
          {result.status === 'ok' && (
            <Check size={13} className="absolute right-2 top-1/2 -translate-y-1/2" style={{ color: STATUS_TONE.ok.text }} />
          )}
          {result.status === 'unknown' && (
            <AlertCircle size={13} className="absolute right-2 top-1/2 -translate-y-1/2" style={{ color: STATUS_TONE.unknown.text }} />
          )}
        </div>
      </div>

      {/* Native datalist keeps the picker usable on a tablet without stealing
          the ability to just type a number fast on a busy service. */}
      {configured && (
        <datalist id={listId}>
          {tables.map(t => (
            <option key={t.id || t.number} value={String(t.number)}>
              {[t.section, t.capacity ? `seats ${t.capacity}` : null].filter(Boolean).join(' · ')}
            </option>
          ))}
        </datalist>
      )}

      {result.status === 'ok' && (
        <p className="text-[10px] flex items-center gap-1 pl-[52px]" style={{ color: STATUS_TONE.ok.text }} data-testid="table-ok">
          <MapPin size={9} />
          {result.table.section || 'main'}
          {result.table.capacity ? ` · seats ${result.table.capacity}` : ''}
          {result.table.status && result.table.status !== 'available'
            ? ` · currently ${result.table.status}` : ''}
        </p>
      )}

      {result.status === 'unknown' && (
        <div className="pl-[52px]" data-testid="table-error">
          <p className="text-[10px] font-medium" style={{ color: STATUS_TONE.unknown.text }}>
            {result.message}
          </p>
          {suggestions.length > 0 && (
            <div className="flex flex-wrap items-center gap-1 mt-0.5">
              <span className="text-[10px] text-gray-500">Did you mean</span>
              {suggestions.map(n => (
                <button
                  key={n}
                  type="button"
                  onClick={() => onChange(String(n))}
                  className="text-[10px] px-1.5 py-0.5 rounded border bg-white hover:bg-gray-50"
                  data-testid={`table-suggest-${n}`}
                >
                  {n}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
