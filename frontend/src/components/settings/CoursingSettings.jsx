import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { Save, Plus, Trash2, Flame, Info } from 'lucide-react';
import { coursingAPI, categoriesAPI } from '../../services/api';
import { toast } from 'sonner';

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
        </>
      )}

      <Button onClick={save} disabled={disabled || saving}
        style={{ backgroundColor: theme?.primary || '#f58c14' }} data-testid="coursing-save">
        <Save size={16} className="mr-1" /> {saving ? 'Saving…' : 'Save Coursing Settings'}
      </Button>
    </div>
  );
}
