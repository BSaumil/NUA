import React, { useState, useEffect, useMemo } from 'react';
import {
  ShoppingCart, CalendarDays, ChefHat, Utensils, Package, Users,
  BarChart3, DollarSign, UserCog, Sparkles, ShieldCheck, Building2, Settings as SettingsIcon,
  ChevronDown, ChevronRight, RotateCcw, Save, User as UserIcon, Shield
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { enterpriseAPI } from '../../services/api';
import { toast } from 'sonner';

const ICON_MAP = {
  ShoppingCart, CalendarDays, ChefHat, Utensils, Package, Users,
  BarChart3, DollarSign, UserCog, Sparkles, ShieldCheck, Building2, Settings: SettingsIcon,
};

const ROLE_LABEL = {
  owner: 'Owner', manager: 'Manager', cashier: 'Staff / Cashier', kitchen: 'Kitchen',
};

/**
 * Section-grouped permissions panel.
 *   Mode "role":   Owner sets defaults per role (e.g. Manager gets Rosters but
 *                  not Payruns). Owner is read-only (always full access).
 *   Mode "staff":  Owner overrides one specific staff member's access.
 * Sections are collapsible with per-section select-all / margin count.
 */
export default function PermissionsPanel({ staff = [] }) {
  const [mode, setMode] = useState('role'); // 'role' | 'staff'
  const [catalog, setCatalog] = useState({ sections: [], totalFeatures: 0 });
  const [roleRows, setRoleRows] = useState([]);
  const [activeRole, setActiveRole] = useState('manager');
  const [activeStaffId, setActiveStaffId] = useState('');
  const [staffMeta, setStaffMeta] = useState(null); // { name, role, roleDefaults, usingRoleDefaults }
  const [selected, setSelected] = useState(new Set()); // permission ids
  const [openSections, setOpenSections] = useState(() => new Set()); // section names that are expanded
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);

  // Load catalog + role rows once
  useEffect(() => {
    (async () => {
      try {
        const [cRes, rRes] = await Promise.all([
          enterpriseAPI.getPermissionCatalog(),
          enterpriseAPI.getRolePermissions(),
        ]);
        setCatalog(cRes.data || { sections: [], totalFeatures: 0 });
        setRoleRows(rRes.data?.roles || []);
        // Expand every section by default so nothing is hidden on first visit
        setOpenSections(new Set((cRes.data?.sections || []).map(s => s.section)));
        setLoaded(true);
      } catch {
        toast.error('Failed to load permissions catalog');
      }
    })();
  }, []);

  // When active role or staff changes, hydrate `selected`
  useEffect(() => {
    if (!loaded) return;
    if (mode === 'role') {
      const row = roleRows.find(r => r.role === activeRole);
      if (row) {
        setSelected(new Set(row.permissions.includes('*') ? catalog.sections.flatMap(s => s.features.map(f => f.id)) : row.permissions));
      }
    } else {
      if (!activeStaffId) { setSelected(new Set()); setStaffMeta(null); return; }
      (async () => {
        try {
          const r = await enterpriseAPI.getStaffPermissions(activeStaffId);
          const d = r.data || {};
          setStaffMeta({ name: d.name, role: d.role, roleDefaults: d.roleDefaults || [], usingRoleDefaults: d.usingRoleDefaults });
          const eff = (d.customPermissions?.length ? d.customPermissions : d.roleDefaults) || [];
          setSelected(new Set(eff));
        } catch { toast.error('Could not load this user\'s permissions'); }
      })();
    }
  }, [mode, activeRole, activeStaffId, loaded, roleRows.length]);

  const totalCount = catalog.totalFeatures || 0;
  const selectedCount = selected.size;

  const toggleFeature = (id) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const sectionState = (section) => {
    const ids = section.features.map(f => f.id);
    const on = ids.filter(id => selected.has(id)).length;
    return { on, total: ids.length, all: on === ids.length, none: on === 0 };
  };

  const toggleSection = (section) => {
    const ids = section.features.map(f => f.id);
    const { all } = sectionState(section);
    setSelected(prev => {
      const next = new Set(prev);
      if (all) ids.forEach(id => next.delete(id));
      else ids.forEach(id => next.add(id));
      return next;
    });
  };

  const bulkAll = () => setSelected(new Set(catalog.sections.flatMap(s => s.features.map(f => f.id))));
  const bulkNone = () => setSelected(new Set());

  const isOwnerRole = mode === 'role' && activeRole === 'owner';

  const handleSave = async () => {
    if (isOwnerRole) { toast.error('Owner permissions cannot be modified'); return; }
    setSaving(true);
    try {
      if (mode === 'role') {
        const r = await enterpriseAPI.setRolePermissions(activeRole, Array.from(selected));
        toast.success(r.data?.message || 'Role permissions saved');
        // Refresh role rows so the featureCount badge stays accurate
        const rRes = await enterpriseAPI.getRolePermissions();
        setRoleRows(rRes.data?.roles || []);
      } else {
        await enterpriseAPI.setStaffPermissions(activeStaffId, Array.from(selected));
        toast.success('Staff permissions saved');
        setStaffMeta(m => m ? { ...m, usingRoleDefaults: false } : m);
      }
    } catch { toast.error('Save failed'); }
    finally { setSaving(false); }
  };

  const handleReset = async () => {
    if (isOwnerRole) return;
    setSaving(true);
    try {
      if (mode === 'role') {
        const r = await enterpriseAPI.resetRolePermissions(activeRole);
        toast.success(r.data?.message || 'Reset to defaults');
        const rRes = await enterpriseAPI.getRolePermissions();
        setRoleRows(rRes.data?.roles || []);
        const row = (rRes.data?.roles || []).find(x => x.role === activeRole);
        if (row) setSelected(new Set(row.permissions));
      } else if (activeStaffId) {
        const r = await enterpriseAPI.clearStaffPermissionsOverride(activeStaffId);
        toast.success('Reverted to role defaults');
        const defaults = r.data?.roleDefaults || [];
        setSelected(new Set(defaults));
        setStaffMeta(m => m ? { ...m, usingRoleDefaults: true } : m);
      }
    } catch { toast.error('Reset failed'); }
    finally { setSaving(false); }
  };

  const displayedSubject = useMemo(() => {
    if (mode === 'role') return ROLE_LABEL[activeRole] || activeRole;
    if (!staffMeta) return 'Select a staff member';
    return `${staffMeta.name} · ${staffMeta.role}${staffMeta.usingRoleDefaults ? ' · using role defaults' : ' · custom override'}`;
  }, [mode, activeRole, staffMeta]);

  if (!loaded) {
    return <Card><CardContent className="p-6 text-sm text-gray-500">Loading permissions…</CardContent></Card>;
  }

  return (
    <div className="space-y-4" data-testid="permissions-panel">
      {/* Mode + subject picker */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2"><Shield size={18} /> Feature Access Control</CardTitle>
          <p className="text-sm text-gray-500 mt-1">
            Choose <b>By Role</b> to set what every Manager / Staff / Kitchen user can see, or <b>By Staff Member</b> to override a single person. Owner always has full access.
          </p>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* Mode tabs */}
          <div className="flex gap-2" data-testid="perm-mode-tabs">
            <Button
              variant={mode === 'role' ? 'default' : 'outline'} size="sm"
              onClick={() => setMode('role')} data-testid="mode-role"
              className={mode === 'role' ? 'bg-indigo-600 hover:bg-indigo-700 text-white' : ''}
            ><Shield size={14} className="mr-1" /> By Role</Button>
            <Button
              variant={mode === 'staff' ? 'default' : 'outline'} size="sm"
              onClick={() => setMode('staff')} data-testid="mode-staff"
              className={mode === 'staff' ? 'bg-indigo-600 hover:bg-indigo-700 text-white' : ''}
            ><UserIcon size={14} className="mr-1" /> By Staff Member</Button>
          </div>

          {/* Subject picker */}
          {mode === 'role' ? (
            <div className="flex flex-wrap gap-2" data-testid="role-picker">
              {roleRows.map(r => (
                <button
                  key={r.role}
                  onClick={() => setActiveRole(r.role)}
                  className={`text-left px-3 py-2 rounded-lg border transition ${activeRole === r.role ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200 hover:border-gray-400'}`}
                  data-testid={`role-tile-${r.role}`}
                >
                  <div className="flex items-center gap-2">
                    <span className="font-medium capitalize">{ROLE_LABEL[r.role] || r.role}</span>
                    {r.isOwner && <Badge className="bg-amber-100 text-amber-700 text-[10px]">Owner</Badge>}
                    {r.isOverridden && !r.isOwner && <Badge className="bg-indigo-100 text-indigo-700 text-[10px]">Customised</Badge>}
                  </div>
                  <p className="text-[11px] text-gray-500 mt-0.5">
                    {r.isOwner ? `All ${totalCount} features` : `${r.featureCount} of ${totalCount} features`}
                  </p>
                </button>
              ))}
            </div>
          ) : (
            <select
              className="w-full p-2 border rounded-md text-sm"
              value={activeStaffId}
              onChange={e => setActiveStaffId(e.target.value)}
              data-testid="staff-picker"
            >
              <option value="">Select staff member…</option>
              {staff.filter(s => s.role !== 'owner').map(s => (
                <option key={s.id} value={s.id}>{s.name} ({s.role})</option>
              ))}
            </select>
          )}
        </CardContent>
      </Card>

      {/* Feature toggler */}
      {(mode === 'role' || activeStaffId) && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div>
                <CardTitle className="text-base">{displayedSubject}</CardTitle>
                <p className="text-[11px] text-gray-500 mt-1">
                  {isOwnerRole
                    ? 'Owner has every permission — this list is read-only.'
                    : `${selectedCount} of ${totalCount} features enabled`}
                </p>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={bulkAll} disabled={isOwnerRole} data-testid="perm-all">Select all</Button>
                <Button size="sm" variant="outline" onClick={bulkNone} disabled={isOwnerRole} data-testid="perm-none">Clear</Button>
                <Button size="sm" variant="outline" onClick={handleReset} disabled={isOwnerRole || saving} data-testid="perm-reset">
                  <RotateCcw size={13} className="mr-1" /> Reset
                </Button>
                <Button
                  size="sm"
                  onClick={handleSave}
                  disabled={isOwnerRole || saving}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white"
                  data-testid="perm-save"
                ><Save size={13} className="mr-1" /> {saving ? 'Saving…' : 'Save'}</Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className={`space-y-2 ${isOwnerRole ? 'opacity-70 pointer-events-none' : ''}`} data-testid="perm-sections">
            {catalog.sections.map(section => {
              const st = sectionState(section);
              const Icon = ICON_MAP[section.icon] || Shield;
              const open = openSections.has(section.section);
              const bar = st.all ? 'bg-emerald-500' : st.on > 0 ? 'bg-amber-400' : 'bg-gray-300';
              return (
                <div key={section.section} className="border rounded-lg overflow-hidden" data-testid={`section-${section.section}`}>
                  <div className="flex items-center gap-2 p-3 bg-gray-50">
                    <button
                      onClick={() => setOpenSections(prev => {
                        const next = new Set(prev);
                        if (next.has(section.section)) next.delete(section.section); else next.add(section.section);
                        return next;
                      })}
                      className="text-gray-400 hover:text-gray-700"
                      data-testid={`section-toggle-${section.section}`}
                    >
                      {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    </button>
                    <Icon size={16} className="text-indigo-600" />
                    <span className="font-medium text-sm">{section.section}</span>
                    <span className={`inline-block h-1.5 w-16 rounded ${bar}`} />
                    <span className="text-[11px] text-gray-500">{st.on} / {st.total}</span>
                    <div className="flex-1"></div>
                    <label className="text-[11px] flex items-center gap-1 cursor-pointer" data-testid={`section-all-${section.section}`}>
                      <input
                        type="checkbox"
                        checked={st.all}
                        // Indeterminate visual is native but not required
                        onChange={() => toggleSection(section)}
                      />
                      <span className="text-gray-500">select all</span>
                    </label>
                  </div>
                  {open && (
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-1 p-3 bg-white">
                      {section.features.map(f => (
                        <label
                          key={f.id}
                          className={`flex items-center gap-2 text-sm p-2 rounded border cursor-pointer transition ${selected.has(f.id) ? 'border-emerald-300 bg-emerald-50/30' : 'border-gray-200 hover:bg-gray-50'}`}
                          data-testid={`feat-${f.id}`}
                        >
                          <input
                            type="checkbox"
                            checked={selected.has(f.id)}
                            onChange={() => toggleFeature(f.id)}
                          />
                          <span>{f.label}</span>
                        </label>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
