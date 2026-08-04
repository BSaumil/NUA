import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { Save, Plus, Trash2, Flame, Info, Timer, Users, LayoutGrid } from 'lucide-react';
import { coursingAPI, categoriesAPI } from '../../services/api';
import { toast } from 'sonner';

// Stages the floor plan already paces tables through (table_courses).
const PACING_STAGES = ['seated', 'drinks', 'entree', 'main', 'dessert', 'coffee', 'check'];

const ORDER_TYPES = [
  { key: 'takeaway', label: 'Takeaway' },
  { key: 'delivery', label: 'Delivery' },
  { key: 'dine-in',  label: 'Dine-in' },
];

/**
 * Owner/manager control panel for coursing.
 *
 * The master switch is the important control: a takeaway-only venue leaves it
 * off and the POS stays exactly as it was — no course groups, no course
 * selectors, no Send-to-Kitchen bar.
 */
export default function CoursingSettings({ theme, canEdit }) {
  const [config, setConfig] = useState(null);
  const [categories, setCategories] = useState([]);
  const [saving, setSaving] = useState(false);
  const [newCourse, setNewCourse] = useState('');
  // Half-built timing rules, kept out of the saved config until complete.
  const [timingDraft, setTimingDraft] = useState({});

  useEffect(() => {
    coursingAPI.getConfig().then(r => setConfig(r.data)).catch(() => setConfig(null));
    categoriesAPI.getAll()
      .then(r => setCategories((r.data || []).map(c => c.name || c).filter(Boolean)))
      .catch(() => setCategories([]));
  }, []);

  if (!config) return <div className="text-gray-400 py-8 text-center">Loading coursing settings…</div>;

  const patch = (next) => setConfig({ ...config, ...next });

  const save = async () => {
    setSaving(true);
    try {
      const r = await coursingAPI.updateConfig(config);
      setConfig(r.data);
      toast.success('Coursing settings saved');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Could not save');
    } finally { setSaving(false); }
  };

  const addCourse = () => {
    const label = newCourse.trim();
    if (!label) return;
    const nextKey = Math.max(0, ...config.courses.map(c => Number(c.key))) + 1;
    patch({ courses: [...config.courses, { key: nextKey, label }] });
    setNewCourse('');
  };

  const removeCourse = (key) => {
    if (config.courses.length <= 1) {
      toast.error('Keep at least one course');
      return;
    }
    const courses = config.courses.filter(c => Number(c.key) !== Number(key));
    // Drop any category mappings pointing at the course just deleted, so the
    // POS can't stamp an item with a course that no longer exists.
    const categoryCourses = Object.fromEntries(
      Object.entries(config.categoryCourses || {}).filter(([, v]) => Number(v) !== Number(key))
    );
    const defaultCourse = Number(config.defaultCourse) === Number(key)
      ? Number(courses[0].key) : config.defaultCourse;
    patch({ courses, categoryCourses, defaultCourse });
  };

  const setCategoryCourse = (cat, value) => {
    const next = { ...(config.categoryCourses || {}) };
    if (value === '') delete next[cat];
    else next[cat] = parseInt(value, 10);
    patch({ categoryCourses: next });
  };

  /**
   * A timing rule needs both a delay and a course to count from, and the two
   * get typed one at a time. `timingDraft` holds the half-built rule so the
   * first field doesn't vanish while the second is being chosen; only a
   * complete rule is written into the config that gets saved.
   */
  const setTimingRule = (courseKey, changes) => {
    const key = String(courseKey);
    const next = { afterEvent: 'served', ...(timingDraft[key] || config.courseTiming?.[key] || {}) };
    if ('minutes' in changes) {
      const n = parseInt(changes.minutes, 10);
      next.minutes = changes.minutes === '' || Number.isNaN(n) ? '' : n;
    }
    if ('afterCourse' in changes) {
      const n = parseInt(changes.afterCourse, 10);
      next.afterCourse = changes.afterCourse === '' || Number.isNaN(n) ? '' : n;
    }
    if ('afterEvent' in changes) next.afterEvent = changes.afterEvent;

    setTimingDraft({ ...timingDraft, [key]: next });

    const timing = { ...(config.courseTiming || {}) };
    if (next.minutes === '' || !next.afterCourse) delete timing[key];
    else timing[key] = { minutes: next.minutes, afterCourse: next.afterCourse, afterEvent: next.afterEvent };
    patch({ courseTiming: timing });
  };

  const clearTimingRule = (courseKey) => {
    const key = String(courseKey);
    const timing = { ...(config.courseTiming || {}) };
    delete timing[key];
    const draft = { ...timingDraft };
    delete draft[key];
    setTimingDraft(draft);
    patch({ courseTiming: timing });
  };

  /** What a timing field should show: the half-typed draft, else the saved rule. */
  const timingValue = (courseKey, field) => {
    const key = String(courseKey);
    const src = timingDraft[key] || config.courseTiming?.[key];
    return src?.[field] ?? (field === 'afterEvent' ? 'served' : '');
  };

  const toggleStraightFireType = (key) => {
    const cur = config.straightFireOrderTypes || [];
    patch({
      straightFireOrderTypes: cur.includes(key)
        ? cur.filter(t => t !== key)
        : [...cur, key],
    });
  };

  const disabled = !canEdit;

  return (
    <div className="space-y-4" data-testid="coursing-settings">
      {!canEdit && (
        <div className="flex items-center gap-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-md p-2">
          <Info size={14} /> Only an owner or manager can change coursing.
        </div>
      )}

      {/* Master switch */}
      <Card>
        <CardContent className="p-4">
          <label className="flex items-start gap-3 cursor-pointer">
            <input type="checkbox" className="mt-1" checked={!!config.enabled} disabled={disabled}
              onChange={e => patch({ enabled: e.target.checked })}
              data-testid="coursing-enabled" />
            <span>
              <span className="font-semibold text-sm">Use courses, holding and firing</span>
              <p className="text-xs text-gray-500 mt-0.5">
                Off by default. While it's off the POS behaves exactly as it does today —
                no course grouping, no Fire/Hold buttons, nothing extra to tap. Leave it off
                for a takeaway-only venue.
              </p>
            </span>
          </label>
        </CardContent>
      </Card>

      {config.enabled && (
        <>
          {/* Courses */}
          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-sm">Courses</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              {config.courses.map((c, i) => (
                <div key={c.key} className="flex items-center gap-2" data-testid={`course-row-${c.key}`}>
                  <Badge variant="outline" className="text-[10px] w-8 justify-center">{c.key}</Badge>
                  <Input className="h-8 text-sm flex-1" value={c.label} disabled={disabled}
                    onChange={e => {
                      const courses = [...config.courses];
                      courses[i] = { ...c, label: e.target.value };
                      patch({ courses });
                    }}
                    data-testid={`course-label-${c.key}`} />
                  <label className="flex items-center gap-1 text-[10px] text-gray-500 whitespace-nowrap">
                    <input type="radio" name="defaultCourse" disabled={disabled}
                      checked={Number(config.defaultCourse) === Number(c.key)}
                      onChange={() => patch({ defaultCourse: Number(c.key) })}
                      data-testid={`course-default-${c.key}`} />
                    default
                  </label>
                  <Button variant="ghost" size="sm" className="text-red-500 h-7 w-7 p-0" disabled={disabled}
                    onClick={() => removeCourse(c.key)} data-testid={`course-remove-${c.key}`}>
                    <Trash2 size={12} />
                  </Button>
                </div>
              ))}
              <div className="flex gap-2 pt-2 border-t">
                <Input className="h-8 text-sm flex-1" placeholder="Add a course, e.g. Cheese" value={newCourse}
                  disabled={disabled} onChange={e => setNewCourse(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') addCourse(); }}
                  data-testid="course-new-label" />
                <Button size="sm" variant="outline" className="h-8" disabled={disabled}
                  onClick={addCourse} data-testid="course-add"><Plus size={14} /></Button>
              </div>
              <p className="text-[10px] text-gray-500">
                The one marked <strong>default</strong> catches anything not mapped below.
              </p>
            </CardContent>
          </Card>

          {/* Category -> course */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Which categories go on which course</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-gray-500 mb-3">
                Map a category once and every item in it lands on that course automatically.
                Staff can still move an individual dish on the POS.
              </p>
              {categories.length === 0 ? (
                <p className="text-xs text-gray-400">No categories found.</p>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {categories.map(cat => (
                    <div key={cat} className="flex items-center gap-2" data-testid={`cat-course-${cat}`}>
                      <span className="text-xs flex-1 truncate" title={cat}>{cat}</span>
                      <select
                        className="text-xs border rounded px-2 h-8 bg-white"
                        disabled={disabled}
                        value={config.categoryCourses?.[cat] ?? ''}
                        onChange={e => setCategoryCourse(cat, e.target.value)}
                        data-testid={`cat-course-select-${cat}`}
                      >
                        <option value="">— default —</option>
                        {config.courses.map(c => (
                          <option key={c.key} value={c.key}>{c.label}</option>
                        ))}
                      </select>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Firing behaviour */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-1.5"><Flame size={14} /> Firing</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <label className="flex items-start gap-2 cursor-pointer">
                <input type="checkbox" className="mt-0.5" disabled={disabled}
                  checked={!!config.autoFireFirstCourse}
                  onChange={e => patch({ autoFireFirstCourse: e.target.checked })}
                  data-testid="coursing-autofire" />
                <span className="text-xs">
                  <strong>Fire the first course on send</strong>
                  <span className="block text-gray-500">
                    Later courses are held until a server fires them. Turn this off to hold
                    every course until it's fired by hand.
                  </span>
                </span>
              </label>

              <label className="flex items-start gap-2 cursor-pointer">
                <input type="checkbox" className="mt-0.5" disabled={disabled}
                  checked={!!config.allowStraightFire}
                  onChange={e => patch({ allowStraightFire: e.target.checked })}
                  data-testid="coursing-allow-straight" />
                <span className="text-xs">
                  <strong>Show "Fire All Now" in the cart</strong>
                  <span className="block text-gray-500">
                    A one-tap override for when the table wants everything together.
                  </span>
                </span>
              </label>

              <div>
                <p className="text-xs font-medium mb-1">Always fire everything at once for:</p>
                <div className="flex gap-2 flex-wrap">
                  {ORDER_TYPES.map(t => {
                    const on = (config.straightFireOrderTypes || []).includes(t.key);
                    return (
                      <button key={t.key} type="button" disabled={disabled}
                        onClick={() => toggleStraightFireType(t.key)}
                        className={`text-xs px-2 py-1 rounded border transition ${on ? 'text-white' : 'bg-white text-gray-600'}`}
                        style={on ? { background: theme?.primary || '#f58c14', borderColor: theme?.primary || '#f58c14' } : {}}
                        data-testid={`straight-fire-${t.key}`}>
                        {t.label}
                      </button>
                    );
                  })}
                </div>
                <p className="text-[10px] text-gray-500 mt-1">
                  These order types skip coursing entirely — no course UI, no holding.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Course timing */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-1.5"><Timer size={14} /> Course timing</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <label className="flex items-start gap-2 cursor-pointer">
                <input type="checkbox" className="mt-0.5" disabled={disabled}
                  checked={!!config.autoFireTiming}
                  onChange={e => patch({ autoFireTiming: e.target.checked })}
                  data-testid="coursing-auto-timing" />
                <span className="text-xs">
                  <strong>Fire held courses automatically on a timer</strong>
                  <span className="block text-gray-500">
                    Off by default. A rule that fires food at a table that isn't ready
                    is worse than a server having to tap Fire.
                  </span>
                </span>
              </label>

              {config.autoFireTiming && (
                <div className="space-y-2 pt-1 border-t">
                  {config.courses.map(c => {
                    const rule = config.courseTiming?.[String(c.key)];
                    const earlier = config.courses.filter(o => Number(o.key) < Number(c.key));
                    if (earlier.length === 0) {
                      return (
                        <p key={c.key} className="text-[10px] text-gray-400" data-testid={`timing-na-${c.key}`}>
                          {c.label} — fires on send (nothing comes before it)
                        </p>
                      );
                    }
                    return (
                      <div key={c.key} className="flex items-center gap-1.5 flex-wrap text-xs"
                        data-testid={`timing-row-${c.key}`}>
                        <span className="font-medium w-20 truncate" title={c.label}>{c.label}</span>
                        <input type="number" min="0" max="240" className="w-14 h-7 text-xs border rounded px-1"
                          disabled={disabled} value={timingValue(c.key, 'minutes')}
                          placeholder="—"
                          onChange={e => setTimingRule(c.key, { minutes: e.target.value })}
                          data-testid={`timing-minutes-${c.key}`} />
                        <span className="text-gray-500">min after</span>
                        <select className="h-7 text-xs border rounded px-1 bg-white" disabled={disabled}
                          value={timingValue(c.key, 'afterCourse')}
                          onChange={e => setTimingRule(c.key, { afterCourse: e.target.value })}
                          data-testid={`timing-after-${c.key}`}>
                          <option value="">—</option>
                          {earlier.map(o => <option key={o.key} value={o.key}>{o.label}</option>)}
                        </select>
                        <select className="h-7 text-xs border rounded px-1 bg-white" disabled={disabled}
                          value={timingValue(c.key, 'afterEvent')}
                          onChange={e => setTimingRule(c.key, { afterEvent: e.target.value })}
                          data-testid={`timing-event-${c.key}`}>
                          <option value="served">is served</option>
                          <option value="fired">is fired</option>
                        </select>
                        {rule && (
                          <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-red-500" disabled={disabled}
                            onClick={() => clearTimingRule(c.key)} data-testid={`timing-clear-${c.key}`}>
                            <Trash2 size={11} />
                          </Button>
                        )}
                      </div>
                    );
                  })}
                  <p className="text-[10px] text-gray-500">
                    Only a course that's still <em>held</em> auto-fires. One a server already
                    fired by hand is left alone.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Seats */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-1.5"><Users size={14} /> Seats</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <label className="flex items-start gap-2 cursor-pointer">
                <input type="checkbox" className="mt-0.5" disabled={disabled}
                  checked={!!config.useSeats}
                  onChange={e => patch({ useSeats: e.target.checked })}
                  data-testid="coursing-use-seats" />
                <span className="text-xs">
                  <strong>Order by seat</strong>
                  <span className="block text-gray-500">
                    Adds a seat picker to each cart line and prints the seat on the
                    docket, so runners don't have to ask who had the steak.
                  </span>
                </span>
              </label>
              {config.useSeats && (
                <div className="flex items-center gap-2 pt-1">
                  <span className="text-xs">Seats offered per table</span>
                  <input type="number" min="1" max="40" className="w-16 h-7 text-xs border rounded px-1"
                    disabled={disabled} value={config.seatCount ?? 8}
                    onChange={e => patch({ seatCount: parseInt(e.target.value, 10) || 8 })}
                    data-testid="coursing-seat-count" />
                </div>
              )}
            </CardContent>
          </Card>

          {/* Floor-plan pacing */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-1.5"><LayoutGrid size={14} /> Floor plan pacing</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <label className="flex items-start gap-2 cursor-pointer">
                <input type="checkbox" className="mt-0.5" disabled={disabled}
                  checked={!!config.syncTablePacing}
                  onChange={e => patch({ syncTablePacing: e.target.checked })}
                  data-testid="coursing-sync-pacing" />
                <span className="text-xs">
                  <strong>Advance the table's pacing when a course fires</strong>
                  <span className="block text-gray-500">
                    The floor plan tracks tables through seated → drinks → entrée → main
                    with dwell timers. Without this it drifts: the plan can show a table on
                    "drinks" long after the kitchen fired their mains.
                  </span>
                </span>
              </label>
              {config.syncTablePacing && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1 border-t">
                  {config.courses.map(c => (
                    <div key={c.key} className="flex items-center gap-2" data-testid={`pacing-row-${c.key}`}>
                      <span className="text-xs flex-1 truncate" title={c.label}>{c.label}</span>
                      <select className="text-xs border rounded px-2 h-8 bg-white" disabled={disabled}
                        value={config.tablePacingMap?.[String(c.key)] ?? ''}
                        onChange={e => {
                          const next = { ...(config.tablePacingMap || {}) };
                          if (e.target.value === '') delete next[String(c.key)];
                          else next[String(c.key)] = e.target.value;
                          patch({ tablePacingMap: next });
                        }}
                        data-testid={`pacing-select-${c.key}`}>
                        <option value="">— don't change —</option>
                        {PACING_STAGES.map(p => <option key={p} value={p}>{p}</option>)}
                      </select>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}

      <Button onClick={save} disabled={disabled || saving}
        style={{ backgroundColor: theme?.primary || '#f58c14' }} data-testid="coursing-save">
        <Save size={16} className="mr-1" /> {saving ? 'Saving…' : 'Save Coursing Settings'}
      </Button>
    </div>
  );
}
