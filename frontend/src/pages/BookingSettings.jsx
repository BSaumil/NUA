import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Save, Clock, Users, CalendarDays } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { useTheme } from '../contexts/ThemeContext';
import { reservationFeaturesAPI } from '../services/api';
import { toast } from 'sonner';

export default function BookingSettings() {
  const { theme } = useTheme();
  const [tab, setTab] = useState('rules');
  const [rules, setRules] = useState(null);
  const [schedule, setSchedule] = useState([]);

  useEffect(() => {
    reservationFeaturesAPI.getBookingRules().then(r => setRules(r.data)).catch(() => {});
    reservationFeaturesAPI.getBookingSchedule().then(r => setSchedule(r.data)).catch(() => {});
  }, []);

  const saveRules = async () => {
    try { await reservationFeaturesAPI.saveBookingRules(rules); toast.success('Booking rules saved'); } catch { toast.error('Failed'); }
  };

  const saveSchedule = async () => {
    try { await reservationFeaturesAPI.saveBookingSchedule(schedule); toast.success('Schedule saved'); } catch { toast.error('Failed'); }
  };

  const updateShift = (idx, field, value) => {
    const s = [...schedule]; s[idx] = { ...s[idx], [field]: value }; setSchedule(s);
  };

  const addShift = () => {
    setSchedule([...schedule, { id: '', name: 'New Shift', startTime: '12:00', endTime: '15:00', interval: 30, tables: [], enabled: true }]);
  };

  return (
    <div className="space-y-6" data-testid="booking-settings-page">
      <div><h1 className="text-2xl font-bold" style={{ color: theme.text }}>Booking Settings & Rules</h1><p className="text-sm text-gray-500">Configure booking window, schedule shifts, and rules</p></div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList><TabsTrigger value="rules">Rules</TabsTrigger><TabsTrigger value="schedule">Schedule</TabsTrigger></TabsList>

        {/* RULES */}
        <TabsContent value="rules" className="mt-4">
          {rules && (
            <Card><CardHeader><CardTitle className="text-sm">Booking Rules</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div><label className="text-sm font-medium mb-1 block">Max Online Party Size</label><Input type="number" value={rules.maxOnlinePartySize} onChange={e => setRules({ ...rules, maxOnlinePartySize: parseInt(e.target.value) || 0 })} data-testid="max-party-size" /></div>
                <div><label className="text-sm font-medium mb-1 block">Max Advance Days</label><Input type="number" value={rules.maxAdvanceDays} onChange={e => setRules({ ...rules, maxAdvanceDays: parseInt(e.target.value) || 0 })} /></div>
                <div><label className="text-sm font-medium mb-1 block">Booking Window (minutes)</label>
                  <select className="w-full p-2 border rounded-md text-sm" value={rules.bookingWindowMinutes} onChange={e => setRules({ ...rules, bookingWindowMinutes: parseInt(e.target.value) })} data-testid="booking-window">
                    <option value={30}>Every 30 minutes</option><option value={60}>Every 1 hour</option>
                  </select>
                </div>
                <div><label className="text-sm font-medium mb-1 block">Cancellation Window (hours)</label><Input type="number" value={rules.cancellationHours} onChange={e => setRules({ ...rules, cancellationHours: parseInt(e.target.value) || 0 })} /></div>
              </div>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={rules.autoConfirm} onChange={e => setRules({ ...rules, autoConfirm: e.target.checked })} /> Auto-confirm bookings</label>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={rules.requireDeposit} onChange={e => setRules({ ...rules, requireDeposit: e.target.checked })} /> Require deposit</label>
              {rules.requireDeposit && <Input type="number" step="0.01" placeholder="Deposit amount ($)" value={rules.depositAmount} onChange={e => setRules({ ...rules, depositAmount: parseFloat(e.target.value) || 0 })} />}
              <Button style={{ backgroundColor: theme.primary }} onClick={saveRules} data-testid="save-rules-btn"><Save size={16} className="mr-1" /> Save Rules</Button>
            </CardContent></Card>
          )}
        </TabsContent>

        {/* SCHEDULE */}
        <TabsContent value="schedule" className="mt-4">
          <Card><CardHeader><CardTitle className="text-sm flex items-center justify-between">Booking Shifts<Button size="sm" variant="outline" onClick={addShift} data-testid="add-shift-btn"><CalendarDays size={14} className="mr-1" /> Add Shift</Button></CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {schedule.map((shift, i) => (
              <div key={shift.id || i} className="p-4 border rounded-lg space-y-3" data-testid={`shift-${i}`}>
                <div className="grid grid-cols-4 gap-3">
                  <div><label className="text-xs text-gray-500">Shift Name</label><Input className="h-8 text-sm" value={shift.name} onChange={e => updateShift(i, 'name', e.target.value)} /></div>
                  <div><label className="text-xs text-gray-500">Start</label><Input type="time" className="h-8 text-sm" value={shift.startTime} onChange={e => updateShift(i, 'startTime', e.target.value)} /></div>
                  <div><label className="text-xs text-gray-500">End</label><Input type="time" className="h-8 text-sm" value={shift.endTime} onChange={e => updateShift(i, 'endTime', e.target.value)} /></div>
                  <div><label className="text-xs text-gray-500">Interval</label>
                    <select className="w-full h-8 text-sm border rounded px-2" value={shift.interval} onChange={e => updateShift(i, 'interval', parseInt(e.target.value))}>
                      <option value={30}>30 min</option><option value={60}>1 hour</option>
                    </select>
                  </div>
                </div>
                <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={shift.enabled} onChange={e => updateShift(i, 'enabled', e.target.checked)} /> Enabled</label>
              </div>
            ))}
            <Button style={{ backgroundColor: theme.primary }} onClick={saveSchedule} data-testid="save-schedule-btn"><Save size={16} className="mr-1" /> Save Schedule</Button>
          </CardContent></Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
