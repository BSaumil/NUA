import React, { useEffect, useState, useCallback } from 'react';
import {
  LogIn, LogOut, Clock, CalendarDays, CalendarOff, Plus, Trash2,
  CheckCircle2, XCircle, Hourglass, User, Moon, Sun, LogOut as SignOutIcon,
} from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { staffMgmtAPI, v26API } from '../services/api';
import { toast } from 'sonner';

const DAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

function sumHoursThisWeek(timecards) {
  const now = new Date();
  const day = (now.getDay() + 6) % 7; // Monday = 0
  const monday = new Date(now); monday.setHours(0, 0, 0, 0); monday.setDate(now.getDate() - day);
  return timecards
    .filter(tc => new Date(tc.clockIn) >= monday)
    .reduce((sum, tc) => sum + (tc.hoursWorked || 0), 0);
}

export default function StaffApp() {
  const { theme, darkMode, toggleDarkMode } = useTheme();
  const { user, logout } = useAuth();
  const [clockStatus, setClockStatus] = useState(null);
  const [timecards, setTimecards] = useState([]);
  const [shifts, setShifts] = useState([]);
  const [timeOff, setTimeOff] = useState([]);
  const [availability, setAvailability] = useState(null);
  const [breakMins, setBreakMins] = useState('0');
  const [showTimeOffDialog, setShowTimeOffDialog] = useState(false);
  const [timeOffForm, setTimeOffForm] = useState({ startDate: '', endDate: '', reason: '' });
  const [loading, setLoading] = useState(true);

  useEffect(() => { document.title = 'NUA Crew'; }, []);

  const load = useCallback(async () => {
    try {
      const [status, tc, ros, off, avail] = await Promise.allSettled([
        staffMgmtAPI.myStatus(), staffMgmtAPI.getTimecards(),
        staffMgmtAPI.getRoster(), staffMgmtAPI.listTimeOff(),
        v26API.getAvailability(user.id),
      ]);
      if (status.status === 'fulfilled') setClockStatus(status.value.data);
      if (tc.status === 'fulfilled') setTimecards(tc.value.data);
      if (ros.status === 'fulfilled') setShifts(ros.value.data);
      if (off.status === 'fulfilled') setTimeOff(off.value.data);
      if (avail.status === 'fulfilled') setAvailability(avail.value.data);
    } finally { setLoading(false); }
  }, [user?.id]);

  useEffect(() => { load(); }, [load]);

  const handleClockIn = async () => {
    try { await staffMgmtAPI.clockIn(); toast.success("You're clocked in — have a great shift!"); load(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Failed to clock in'); }
  };
  const handleClockOut = async () => {
    try { await staffMgmtAPI.clockOut({ breakMinutes: parseInt(breakMins) || 0 }); toast.success('Clocked out — see you next shift!'); load(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Failed to clock out'); }
  };
  const handleRequestTimeOff = async () => {
    if (!timeOffForm.startDate || !timeOffForm.endDate || !timeOffForm.reason) {
      toast.error('Fill in the dates and a reason'); return;
    }
    try {
      await staffMgmtAPI.requestTimeOff(timeOffForm);
      toast.success('Time off requested');
      setShowTimeOffDialog(false);
      setTimeOffForm({ startDate: '', endDate: '', reason: '' });
      load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed to submit request'); }
  };
  const handleCancelTimeOff = async (id) => {
    try { await staffMgmtAPI.cancelTimeOff(id); toast.success('Request cancelled'); load(); }
    catch { toast.error('Failed to cancel'); }
  };

  const weeklyHours = sumHoursThisWeek(timecards);
  const upcomingShifts = [...shifts].sort((a, b) => DAY_ORDER.indexOf(a.date) - DAY_ORDER.indexOf(b.date));
  const blackouts = availability?.blackoutDates || [];

  return (
    <div className="min-h-screen pb-10" style={{ background: darkMode ? '#0b0b0f' : '#f6f7fb' }} data-testid="staff-app-page">
      {/* Top bar — deliberately minimal, this is a single-purpose app */}
      <div className="sticky top-0 z-10 backdrop-blur border-b px-4 py-3 flex items-center justify-between"
        style={{ background: darkMode ? 'rgba(11,11,15,0.85)' : 'rgba(255,255,255,0.85)', borderColor: darkMode ? '#1f1f28' : '#e5e7eb' }}>
        <div className="flex items-center gap-2">
          <span className="font-bold" style={{ color: theme.primary }}>NUA</span>
          <span className="text-sm text-gray-400">Crew</span>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={toggleDarkMode} className="text-gray-400 hover:text-gray-600" data-testid="staff-app-theme-toggle">
            {darkMode ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <button onClick={logout} className="text-gray-400 hover:text-red-500" data-testid="staff-app-signout">
            <SignOutIcon size={18} />
          </button>
        </div>
      </div>

      <div className="max-w-md mx-auto px-4 pt-5 space-y-4">
        {/* Who / status */}
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-full flex items-center justify-center font-bold text-white shrink-0" style={{ background: theme.primary }}>
            <User size={20} />
          </div>
          <div>
            <p className="font-semibold" style={{ color: darkMode ? '#eaeaea' : '#111827' }}>{user?.name}</p>
            <p className="text-xs text-gray-400 capitalize">{user?.role}</p>
          </div>
        </div>

        {/* Big clock in/out — the one thing this app must never make you hunt for */}
        <Card data-testid="staff-app-clock-card">
          <CardContent className="p-5 text-center space-y-3">
            {clockStatus?.clockedIn ? (
              <>
                <Badge className="bg-green-100 text-green-700 mx-auto"><Clock size={12} className="mr-1" /> Clocked in since {new Date(clockStatus.currentShift.clockIn).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</Badge>
                <Input type="number" placeholder="Break minutes" value={breakMins} onChange={e => setBreakMins(e.target.value)} className="text-center" data-testid="staff-app-break-input" />
                <Button className="w-full h-12 text-base bg-red-600 hover:bg-red-700 text-white" onClick={handleClockOut} data-testid="staff-app-clockout-btn">
                  <LogOut size={18} className="mr-2" /> Clock Out
                </Button>
              </>
            ) : (
              <Button className="w-full h-14 text-lg" style={{ backgroundColor: theme.primary }} onClick={handleClockIn} data-testid="staff-app-clockin-btn">
                <LogIn size={20} className="mr-2" /> Clock In
              </Button>
            )}
            <p className="text-xs text-gray-400">{weeklyHours.toFixed(1)}h worked this week</p>
          </CardContent>
        </Card>

        {/* My shifts */}
        <div>
          <h2 className="text-sm font-semibold mb-2 flex items-center gap-1.5" style={{ color: darkMode ? '#eaeaea' : '#111827' }}>
            <CalendarDays size={15} /> My Shifts
          </h2>
          <div className="space-y-2">
            {upcomingShifts.map(s => (
              <Card key={s.id} data-testid={`staff-app-shift-${s.id}`}>
                <CardContent className="p-3 flex items-center justify-between">
                  <div>
                    <p className="font-medium text-sm">{s.date}</p>
                    <p className="text-xs text-gray-400">{s.startTime} – {s.endTime}{s.notes ? ` · ${s.notes}` : ''}</p>
                  </div>
                  {s.blackoutOverridden && <Badge className="bg-amber-100 text-amber-700 text-[10px]">Override</Badge>}
                </CardContent>
              </Card>
            ))}
            {!loading && upcomingShifts.length === 0 && (
              <Card className="border-dashed"><CardContent className="p-6 text-center text-sm text-gray-400">No shifts on the roster yet.</CardContent></Card>
            )}
          </div>
        </div>

        {/* Time off */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-semibold flex items-center gap-1.5" style={{ color: darkMode ? '#eaeaea' : '#111827' }}>
              <CalendarOff size={15} /> Time Off
            </h2>
            <Button size="sm" variant="outline" onClick={() => setShowTimeOffDialog(true)} data-testid="staff-app-request-timeoff-btn">
              <Plus size={14} className="mr-1" /> Request
            </Button>
          </div>
          <div className="space-y-2">
            {timeOff.map(t => (
              <Card key={t.id} data-testid={`staff-app-timeoff-${t.id}`}>
                <CardContent className="p-3 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">{t.startDate} → {t.endDate}</p>
                    <p className="text-xs text-gray-400">{t.reason}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className={
                      t.status === 'approved' ? 'bg-green-100 text-green-700' :
                      t.status === 'denied' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
                    }>
                      {t.status === 'approved' ? <CheckCircle2 size={11} className="mr-1" /> : t.status === 'denied' ? <XCircle size={11} className="mr-1" /> : <Hourglass size={11} className="mr-1" />}
                      {t.status}
                    </Badge>
                    {t.status === 'pending' && (
                      <button onClick={() => handleCancelTimeOff(t.id)} className="text-gray-400 hover:text-red-600" data-testid={`staff-app-cancel-timeoff-${t.id}`}>
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
            {!loading && timeOff.length === 0 && (
              <Card className="border-dashed"><CardContent className="p-6 text-center text-sm text-gray-400">No time off requests yet.</CardContent></Card>
            )}
          </div>
        </div>

        {/* Availability / blackout — read-only, set by the owner */}
        {blackouts.length > 0 && (
          <div>
            <h2 className="text-sm font-semibold mb-2" style={{ color: darkMode ? '#eaeaea' : '#111827' }}>My Blackout Dates</h2>
            <div className="space-y-1.5">
              {blackouts.map((b, i) => (
                <div key={i} className="text-xs px-3 py-2 rounded-lg bg-amber-50 text-amber-700 border border-amber-200" data-testid={`staff-app-blackout-${i}`}>
                  {b.from} → {b.to || b.from}{b.reason ? ` · ${b.reason}` : ''}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Request Time Off dialog */}
      <Dialog open={showTimeOffDialog} onOpenChange={setShowTimeOffDialog}>
        <DialogContent className="max-w-sm" data-testid="staff-app-timeoff-dialog">
          <DialogHeader><DialogTitle>Request Time Off</DialogTitle></DialogHeader>
          <div className="space-y-3 py-2">
            <div className="grid grid-cols-2 gap-2">
              <div><label className="text-xs font-medium text-gray-500 mb-1 block">Start</label>
                <Input type="date" value={timeOffForm.startDate} onChange={e => setTimeOffForm({ ...timeOffForm, startDate: e.target.value })} data-testid="staff-app-timeoff-start" />
              </div>
              <div><label className="text-xs font-medium text-gray-500 mb-1 block">End</label>
                <Input type="date" value={timeOffForm.endDate} onChange={e => setTimeOffForm({ ...timeOffForm, endDate: e.target.value })} data-testid="staff-app-timeoff-end" />
              </div>
            </div>
            <textarea className="w-full min-h-[80px] p-2 border rounded-md text-sm resize-none" placeholder="Reason"
              value={timeOffForm.reason} onChange={e => setTimeOffForm({ ...timeOffForm, reason: e.target.value })} data-testid="staff-app-timeoff-reason" />
            <Button className="w-full" style={{ backgroundColor: theme.primary }} onClick={handleRequestTimeOff} data-testid="staff-app-submit-timeoff-btn">Submit Request</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
