import React, { useState, useEffect } from 'react';
import { Palette, MapPin, Users as UsersIcon, Building, GraduationCap, Plus, Edit, Trash2, Save } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Badge } from '../components/ui/badge';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { locationsAPI, advancedAPI } from '../services/api';
import { toast } from 'sonner';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;
const authHeader = () => ({ Authorization: `Bearer ${localStorage.getItem('nuva_token')}` });

const Settings = () => {
  const { theme, updateTheme, resetTheme } = useTheme();
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('theme');
  const [trainingMode, setTrainingMode] = useState(false);
  const [trainingLoading, setTrainingLoading] = useState(false);
  // Locations
  const [locations, setLocations] = useState([]);
  const [showLocDialog, setShowLocDialog] = useState(false);
  const [editingLoc, setEditingLoc] = useState(null);
  const [locForm, setLocForm] = useState({ name: '', address: '', phone: '' });
  // Staff
  const [staff, setStaff] = useState([]);
  const [showStaffDialog, setShowStaffDialog] = useState(false);
  const [editingStaff, setEditingStaff] = useState(null);
  const [staffForm, setStaffForm] = useState({ name: '', email: '', password: '', role: 'cashier', payRate: '' });
  // Business
  const [bizForm, setBizForm] = useState({ name: 'NUVA POS', abn: '', address: '', phone: '', email: '', taxId: '' });

  useEffect(() => {
    advancedAPI.getTrainingMode().then(r => setTrainingMode(r.data?.enabled || false)).catch(() => {});
    fetchLocations();
    fetchStaff();
    fetchBusiness();
  }, []);

  const fetchLocations = async () => {
    try { const r = await locationsAPI.getAll(); setLocations(r.data); } catch {}
  };
  const fetchStaff = async () => {
    try { const r = await axios.get(`${API}/api/auth/staff`, { headers: authHeader() }); setStaff(r.data); } catch {}
  };
  const fetchBusiness = async () => {
    try {
      const r = await axios.get(`${API}/api/business/settings`, { headers: authHeader() });
      if (r.data) setBizForm(prev => ({ ...prev, ...r.data }));
    } catch {}
  };

  // Location CRUD
  const openAddLoc = () => { setEditingLoc(null); setLocForm({ name: '', address: '', phone: '' }); setShowLocDialog(true); };
  const openEditLoc = (loc) => { setEditingLoc(loc); setLocForm({ name: loc.name, address: loc.address, phone: loc.phone }); setShowLocDialog(true); };
  const saveLoc = async () => {
    try {
      if (editingLoc) { await locationsAPI.update(editingLoc.id, locForm); toast.success('Location updated'); }
      else { await locationsAPI.create(locForm); toast.success('Location created'); }
      setShowLocDialog(false); fetchLocations();
    } catch (e) { toast.error('Failed to save location'); }
  };
  const deleteLoc = async (id) => {
    if (!window.confirm('Delete this location?')) return;
    try { await locationsAPI.delete(id); toast.success('Location deleted'); fetchLocations(); } catch { toast.error('Failed to delete'); }
  };

  // Staff CRUD
  const openAddStaff = () => { setEditingStaff(null); setStaffForm({ name: '', email: '', password: '', role: 'cashier', payRate: '' }); setShowStaffDialog(true); };
  const openEditStaff = (s) => { setEditingStaff(s); setStaffForm({ name: s.name, email: s.email, password: '', role: s.role, payRate: s.payRate || '' }); setShowStaffDialog(true); };
  const saveStaff = async () => {
    try {
      if (editingStaff) {
        const data = { name: staffForm.name, role: staffForm.role, payRate: parseFloat(staffForm.payRate) || 0 };
        await axios.put(`${API}/api/auth/staff/${editingStaff.id}`, data, { headers: authHeader() });
        toast.success('Staff updated');
      } else {
        await axios.post(`${API}/api/auth/register`, { ...staffForm, payRate: parseFloat(staffForm.payRate) || 0 }, { headers: authHeader() });
        toast.success('Staff member created');
      }
      setShowStaffDialog(false); fetchStaff();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed to save staff'); }
  };
  const deleteStaff = async (id) => {
    if (!window.confirm('Delete this staff member?')) return;
    try { await axios.delete(`${API}/api/auth/staff/${id}`, { headers: authHeader() }); toast.success('Staff deleted'); fetchStaff(); } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  // Business save
  const saveBusiness = async () => {
    try {
      await axios.post(`${API}/api/business/settings`, bizForm, { headers: authHeader() });
      toast.success('Business settings saved');
    } catch { toast.error('Failed to save'); }
  };

  const tabs = [
    { id: 'theme', label: 'Theme', icon: Palette },
    { id: 'training', label: 'Training Mode', icon: GraduationCap },
    { id: 'locations', label: 'Locations', icon: MapPin },
    { id: 'users', label: 'Staff', icon: UsersIcon },
    { id: 'business', label: 'Business Info', icon: Building }
  ];

  return (
    <div className="space-y-6" data-testid="settings-page">
      <div><h1 className="text-3xl font-bold" style={{ color: theme.text }}>Settings</h1><p className="text-gray-500 mt-1">Manage your system preferences and configurations</p></div>

      <div className="flex gap-2 border-b">
        {tabs.map(tab => {
          const Icon = tab.icon;
          return (<button key={tab.id} onClick={() => setActiveTab(tab.id)} className="flex items-center gap-2 px-4 py-3 font-medium transition-colors" data-testid={`settings-tab-${tab.id}`}
            style={{ color: activeTab === tab.id ? theme.primary : theme.text, borderBottom: activeTab === tab.id ? `2px solid ${theme.primary}` : 'none' }}>
            <Icon size={18} />{tab.label}
          </button>);
        })}
      </div>

      {/* Training Mode */}
      {activeTab === 'training' && (
        <Card><CardHeader><CardTitle>Training Mode</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-gray-500">When enabled, POS transactions are simulated — no real charges are processed.</p>
          <div className="flex items-center justify-between p-4 rounded-lg border">
            <div>
              <p className="font-semibold">{trainingMode ? 'Training Mode is ON' : 'Training Mode is OFF'}</p>
              <p className="text-sm text-gray-500">{trainingMode ? 'All POS transactions are simulated' : 'POS is processing real transactions'}</p>
            </div>
            <Button data-testid="toggle-training-mode" disabled={trainingLoading} onClick={async () => {
              setTrainingLoading(true);
              try { const r = await advancedAPI.setTrainingMode(!trainingMode); setTrainingMode(r.data.enabled); toast.success(r.data.message); } catch { toast.error('Failed'); }
              setTrainingLoading(false);
            }} style={{ backgroundColor: trainingMode ? '#ef4444' : theme.primary }} className="text-white">
              {trainingMode ? 'Disable' : 'Enable'}
            </Button>
          </div>
        </CardContent></Card>
      )}

      {/* Theme */}
      {activeTab === 'theme' && (
        <Card><CardHeader><CardTitle>Color Customization</CardTitle></CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[{ key: 'primary', label: 'Primary Color' }, { key: 'secondary', label: 'Secondary Color' }, { key: 'accent', label: 'Accent Color' }, { key: 'sidebar', label: 'Sidebar Background' }].map(c => (
              <div key={c.key} className="space-y-2">
                <label className="font-medium text-sm">{c.label}</label>
                <div className="flex items-center gap-3">
                  <input type="color" value={theme[c.key]} onChange={e => updateTheme({ [c.key]: e.target.value })} className="w-20 h-10 rounded border cursor-pointer" />
                  <Input value={theme[c.key]} onChange={e => updateTheme({ [c.key]: e.target.value })} className="flex-1 font-mono text-sm" />
                </div>
              </div>
            ))}
          </div>
          <Button variant="outline" onClick={resetTheme}>Reset to Default</Button>
        </CardContent></Card>
      )}

      {/* Locations */}
      {activeTab === 'locations' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-bold">Store Locations</h2>
            <Button style={{ backgroundColor: theme.primary }} onClick={openAddLoc} data-testid="add-location-btn"><Plus size={16} className="mr-1" /> Add Location</Button>
          </div>
          {locations.map(loc => (
            <Card key={loc.id} data-testid={`location-card-${loc.id}`}><CardContent className="p-6">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-lg font-bold" style={{ color: theme.text }}>{loc.name}</h3>
                  <p className="text-sm text-gray-600">{loc.address}</p>
                  <p className="text-sm text-gray-600">{loc.phone}</p>
                  <Badge className={`mt-2 ${loc.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>{(loc.status || 'active').toUpperCase()}</Badge>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => openEditLoc(loc)} data-testid={`edit-loc-${loc.id}`}><Edit size={14} /></Button>
                  <Button variant="outline" size="sm" className="text-red-500" onClick={() => deleteLoc(loc.id)} data-testid={`delete-loc-${loc.id}`}><Trash2 size={14} /></Button>
                </div>
              </div>
            </CardContent></Card>
          ))}
          {locations.length === 0 && <Card className="border-dashed"><CardContent className="p-12 text-center"><MapPin size={40} className="mx-auto mb-3 text-gray-300" /><p className="text-gray-500">No locations yet. Add your first location.</p></CardContent></Card>}
        </div>
      )}

      {/* Staff */}
      {activeTab === 'users' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-bold">Team Members</h2>
            {user?.role === 'owner' && <Button style={{ backgroundColor: theme.primary }} onClick={openAddStaff} data-testid="add-staff-btn"><Plus size={16} className="mr-1" /> Add Staff</Button>}
          </div>
          <Card><CardContent className="p-0"><div className="overflow-x-auto"><table className="w-full" data-testid="staff-table">
            <thead className="bg-gray-50"><tr>
              <th className="text-left p-4 text-sm font-medium text-gray-500">Name</th>
              <th className="text-left p-4 text-sm font-medium text-gray-500">Email</th>
              <th className="text-left p-4 text-sm font-medium text-gray-500">Role</th>
              <th className="text-center p-4 text-sm font-medium text-gray-500">Status</th>
              {user?.role === 'owner' && <th className="text-right p-4 text-sm font-medium text-gray-500">Pay Rate</th>}
              {user?.role === 'owner' && <th className="text-center p-4 text-sm font-medium text-gray-500">Actions</th>}
            </tr></thead>
            <tbody>
              {staff.map(s => (
                <tr key={s.id} className="border-t hover:bg-gray-50" data-testid={`staff-row-${s.id}`}>
                  <td className="p-4 font-medium">{s.name}</td>
                  <td className="p-4 text-sm text-gray-600">{s.email}</td>
                  <td className="p-4"><Badge variant="outline" className="capitalize">{s.role}</Badge></td>
                  <td className="p-4 text-center">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${s.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                      {(s.status || 'active').toUpperCase()}
                    </span>
                  </td>
                  {user?.role === 'owner' && <td className="p-4 text-right font-mono">${s.payRate || 0}/hr</td>}
                  {user?.role === 'owner' && <td className="p-4 text-center">
                    <div className="flex justify-center gap-2">
                      <Button variant="outline" size="sm" onClick={() => openEditStaff(s)} data-testid={`edit-staff-${s.id}`}><Edit size={14} /></Button>
                      <Button variant="outline" size="sm" className="text-red-500" onClick={() => deleteStaff(s.id)} data-testid={`delete-staff-${s.id}`}><Trash2 size={14} /></Button>
                    </div>
                  </td>}
                </tr>
              ))}
            </tbody>
          </table></div></CardContent></Card>
        </div>
      )}

      {/* Business Info */}
      {activeTab === 'business' && (
        <Card><CardHeader><CardTitle>Business Information</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div><label className="text-sm font-medium mb-1 block">Business Name</label><Input value={bizForm.name} onChange={e => setBizForm({ ...bizForm, name: e.target.value })} data-testid="biz-name" /></div>
          <div><label className="text-sm font-medium mb-1 block">ABN</label><Input placeholder="12 345 678 901" value={bizForm.abn} onChange={e => setBizForm({ ...bizForm, abn: e.target.value })} /></div>
          <div><label className="text-sm font-medium mb-1 block">Business Address</label><Input value={bizForm.address} onChange={e => setBizForm({ ...bizForm, address: e.target.value })} /></div>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="text-sm font-medium mb-1 block">Phone</label><Input value={bizForm.phone} onChange={e => setBizForm({ ...bizForm, phone: e.target.value })} /></div>
            <div><label className="text-sm font-medium mb-1 block">Email</label><Input value={bizForm.email} onChange={e => setBizForm({ ...bizForm, email: e.target.value })} /></div>
          </div>
          <div><label className="text-sm font-medium mb-1 block">Tax Registration</label><Input value={bizForm.taxId} onChange={e => setBizForm({ ...bizForm, taxId: e.target.value })} /></div>
          <Button style={{ backgroundColor: theme.primary }} onClick={saveBusiness} data-testid="save-biz-btn"><Save size={16} className="mr-1" /> Save Changes</Button>
        </CardContent></Card>
      )}

      {/* Location Dialog */}
      <Dialog open={showLocDialog} onOpenChange={setShowLocDialog}>
        <DialogContent className="max-w-sm" data-testid="location-dialog">
          <DialogHeader><DialogTitle>{editingLoc ? 'Edit Location' : 'Add Location'}</DialogTitle></DialogHeader>
          <div className="space-y-3 py-2">
            <Input placeholder="Location name" value={locForm.name} onChange={e => setLocForm({ ...locForm, name: e.target.value })} data-testid="loc-name-input" />
            <Input placeholder="Address" value={locForm.address} onChange={e => setLocForm({ ...locForm, address: e.target.value })} data-testid="loc-address-input" />
            <Input placeholder="Phone" value={locForm.phone} onChange={e => setLocForm({ ...locForm, phone: e.target.value })} data-testid="loc-phone-input" />
            <Button className="w-full" style={{ backgroundColor: theme.primary }} onClick={saveLoc} data-testid="save-loc-btn">{editingLoc ? 'Update' : 'Create'} Location</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Staff Dialog */}
      <Dialog open={showStaffDialog} onOpenChange={setShowStaffDialog}>
        <DialogContent className="max-w-sm" data-testid="staff-dialog">
          <DialogHeader><DialogTitle>{editingStaff ? 'Edit Staff' : 'Add Staff Member'}</DialogTitle></DialogHeader>
          <div className="space-y-3 py-2">
            <Input placeholder="Full name" value={staffForm.name} onChange={e => setStaffForm({ ...staffForm, name: e.target.value })} data-testid="staff-name-input" />
            {!editingStaff && <Input placeholder="Email" value={staffForm.email} onChange={e => setStaffForm({ ...staffForm, email: e.target.value })} data-testid="staff-email-input" />}
            {!editingStaff && <Input type="password" placeholder="Password" value={staffForm.password} onChange={e => setStaffForm({ ...staffForm, password: e.target.value })} data-testid="staff-password-input" />}
            <select className="w-full p-2 border rounded-md text-sm" value={staffForm.role} onChange={e => setStaffForm({ ...staffForm, role: e.target.value })} data-testid="staff-role-select">
              <option value="cashier">Cashier</option><option value="kitchen">Kitchen</option><option value="manager">Manager</option><option value="owner">Owner</option>
            </select>
            <Input type="number" step="0.01" placeholder="Pay rate ($/hr)" value={staffForm.payRate} onChange={e => setStaffForm({ ...staffForm, payRate: e.target.value })} data-testid="staff-payrate-input" />
            <Button className="w-full" style={{ backgroundColor: theme.primary }} onClick={saveStaff} data-testid="save-staff-btn">{editingStaff ? 'Update' : 'Create'} Staff</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Settings;
