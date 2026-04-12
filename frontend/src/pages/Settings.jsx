import React, { useState, useEffect } from 'react';
import { Palette, MapPin, Users as UsersIcon, Building, GraduationCap } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { useTheme } from '../contexts/ThemeContext';
import { locations, users } from '../mockData';
import { useToast } from '../hooks/use-toast';
import { advancedAPI } from '../services/api';

const Settings = () => {
  const { theme, updateTheme, resetTheme } = useTheme();
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState('theme');
  const [trainingMode, setTrainingMode] = useState(false);
  const [trainingLoading, setTrainingLoading] = useState(false);

  useEffect(() => {
    advancedAPI.getTrainingMode().then(r => setTrainingMode(r.data?.enabled || false)).catch(() => {});
  }, []);

  const handleThemeUpdate = (key, value) => {
    updateTheme({ [key]: value });
    toast({
      title: "Theme Updated",
      description: "Your color preferences have been saved",
    });
  };

  const tabs = [
    { id: 'theme', label: 'Theme', icon: Palette },
    { id: 'training', label: 'Training Mode', icon: GraduationCap },
    { id: 'locations', label: 'Locations', icon: MapPin },
    { id: 'users', label: 'Users & Roles', icon: UsersIcon },
    { id: 'business', label: 'Business Info', icon: Building }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold" style={{ color: theme.text }}>Settings</h1>
        <p className="text-gray-500 mt-1">Manage your system preferences and configurations</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        {tabs.map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className="flex items-center gap-2 px-4 py-3 font-medium transition-colors relative"
              style={{
                color: activeTab === tab.id ? theme.primary : theme.text,
                borderBottom: activeTab === tab.id ? `2px solid ${theme.primary}` : 'none'
              }}
            >
              <Icon size={18} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Training Mode */}
      {activeTab === 'training' && (
        <Card>
          <CardHeader><CardTitle>Training Mode</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-gray-500">
              When enabled, POS transactions are simulated — no real charges are processed.
              Ideal for onboarding new staff or testing workflows.
            </p>
            <div className="flex items-center justify-between p-4 rounded-lg border">
              <div>
                <p className="font-semibold">{trainingMode ? 'Training Mode is ON' : 'Training Mode is OFF'}</p>
                <p className="text-sm text-gray-500">{trainingMode ? 'All POS transactions are simulated' : 'POS is processing real transactions'}</p>
              </div>
              <Button
                data-testid="toggle-training-mode"
                disabled={trainingLoading}
                onClick={async () => {
                  setTrainingLoading(true);
                  try {
                    const res = await advancedAPI.setTrainingMode(!trainingMode);
                    setTrainingMode(res.data.enabled);
                    toast({ title: res.data.enabled ? 'Training Mode Enabled' : 'Training Mode Disabled', description: res.data.message });
                  } catch { toast({ title: 'Error', description: 'Failed to toggle training mode', variant: 'destructive' }); }
                  setTrainingLoading(false);
                }}
                style={{ backgroundColor: trainingMode ? '#ef4444' : theme.primary }}
                className="text-white"
              >
                {trainingMode ? 'Disable' : 'Enable'}
              </Button>
            </div>
            {trainingMode && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
                A yellow banner will appear on the POS Terminal reminding staff that transactions are simulated.
              </div>
            )}
          </CardContent>
        </Card>
      )}


      {/* Theme Settings */}
      {activeTab === 'theme' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Color Customization</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <p className="text-sm text-gray-500 mb-4">
                Customize your POS system colors to match your brand. Changes apply instantly across the entire application.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {[
                  { key: 'primary', label: 'Primary Color', description: 'Main brand color' },
                  { key: 'secondary', label: 'Secondary Color', description: 'Supporting accent' },
                  { key: 'accent', label: 'Accent Color', description: 'Highlights and CTAs' },
                  { key: 'sidebar', label: 'Sidebar Background', description: 'Navigation background' }
                ].map(colorOption => (
                  <div key={colorOption.key} className="space-y-2">
                    <label className="font-medium text-sm">{colorOption.label}</label>
                    <p className="text-xs text-gray-500">{colorOption.description}</p>
                    <div className="flex items-center gap-3">
                      <input
                        type="color"
                        value={theme[colorOption.key]}
                        onChange={(e) => handleThemeUpdate(colorOption.key, e.target.value)}
                        className="w-20 h-10 rounded border cursor-pointer"
                      />
                      <Input
                        value={theme[colorOption.key]}
                        onChange={(e) => handleThemeUpdate(colorOption.key, e.target.value)}
                        className="flex-1 font-mono text-sm"
                      />
                    </div>
                  </div>
                ))}
              </div>

              {/* Preview */}
              <div className="mt-6 p-6 rounded-lg" style={{ backgroundColor: theme.sidebar }}>
                <h4 className="font-semibold mb-4" style={{ color: theme.text }}>Theme Preview</h4>
                <div className="flex gap-3">
                  <button
                    className="px-4 py-2 rounded font-medium text-white"
                    style={{ backgroundColor: theme.primary }}
                  >
                    Primary Button
                  </button>
                  <button
                    className="px-4 py-2 rounded font-medium text-white"
                    style={{ backgroundColor: theme.secondary }}
                  >
                    Secondary Button
                  </button>
                  <button
                    className="px-4 py-2 rounded font-medium text-white"
                    style={{ backgroundColor: theme.accent }}
                  >
                    Accent Button
                  </button>
                </div>
              </div>

              <Button variant="outline" onClick={resetTheme}>
                Reset to Default Theme
              </Button>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Locations */}
      {activeTab === 'locations' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-bold" style={{ color: theme.text }}>Store Locations</h2>
            <Button style={{ backgroundColor: theme.primary }}>Add Location</Button>
          </div>

          {locations.map(location => (
            <Card key={location.id}>
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="text-lg font-bold mb-2" style={{ color: theme.text }}>{location.name}</h3>
                    <div className="space-y-1 text-sm text-gray-600">
                      <p>{location.address}</p>
                      <p>{location.phone}</p>
                    </div>
                    <span
                      className="inline-block mt-3 px-3 py-1 rounded-full text-xs font-medium"
                      style={{
                        backgroundColor: location.status === 'active' ? '#dcfce7' : '#fee2e2',
                        color: location.status === 'active' ? '#15803d' : '#991b1b'
                      }}
                    >
                      {location.status.toUpperCase()}
                    </span>
                  </div>
                  <Button variant="outline">Edit</Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Users & Roles */}
      {activeTab === 'users' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-bold" style={{ color: theme.text }}>Team Members</h2>
            <Button style={{ backgroundColor: theme.primary }}>Add User</Button>
          </div>

          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-left p-4 text-sm font-medium text-gray-500">Name</th>
                      <th className="text-left p-4 text-sm font-medium text-gray-500">Email</th>
                      <th className="text-left p-4 text-sm font-medium text-gray-500">Role</th>
                      <th className="text-left p-4 text-sm font-medium text-gray-500">Locations</th>
                      <th className="text-center p-4 text-sm font-medium text-gray-500">Status</th>
                      <th className="text-center p-4 text-sm font-medium text-gray-500">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map(user => (
                      <tr key={user.id} className="border-t hover:bg-gray-50 transition-colors">
                        <td className="p-4">
                          <div className="flex items-center gap-3">
                            <div
                              className="w-10 h-10 rounded-full flex items-center justify-center text-white font-medium"
                              style={{ backgroundColor: theme.primary }}
                            >
                              {user.name.split(' ').map(n => n[0]).join('')}
                            </div>
                            <span className="font-medium">{user.name}</span>
                          </div>
                        </td>
                        <td className="p-4 text-sm text-gray-600">{user.email}</td>
                        <td className="p-4">
                          <span className="px-2 py-1 rounded text-xs font-medium bg-gray-100">
                            {user.role}
                          </span>
                        </td>
                        <td className="p-4 text-sm">
                          {user.locations.map(locId => 
                            locations.find(l => l.id === locId)?.name
                          ).join(', ')}
                        </td>
                        <td className="p-4 text-center">
                          <span
                            className="inline-block px-2 py-1 rounded-full text-xs font-medium"
                            style={{
                              backgroundColor: user.status === 'active' ? '#dcfce7' : '#fee2e2',
                              color: user.status === 'active' ? '#15803d' : '#991b1b'
                            }}
                          >
                            {user.status.toUpperCase()}
                          </span>
                        </td>
                        <td className="p-4 text-center">
                          <Button variant="outline" size="sm">Edit</Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Business Info */}
      {activeTab === 'business' && (
        <Card>
          <CardHeader>
            <CardTitle>Business Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-2 block">Business Name</label>
                <Input placeholder="Your Business Name" defaultValue="NUVA POS Pro" />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">ABN</label>
                <Input placeholder="12 345 678 901" />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Business Address</label>
                <Input placeholder="123 Main St, Sydney NSW 2000" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium mb-2 block">Phone</label>
                  <Input placeholder="+61 2 1234 5678" />
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">Email</label>
                  <Input placeholder="info@business.com" />
                </div>
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Tax Registration Number</label>
                <Input placeholder="Tax ID / GST Registration" />
              </div>
              <Button style={{ backgroundColor: theme.primary }}>Save Changes</Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default Settings;
