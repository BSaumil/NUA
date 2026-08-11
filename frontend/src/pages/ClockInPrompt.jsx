import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Clock, LogIn, LogOut, ArrowRight } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { staffMgmtAPI } from '../services/api';
import { toast } from 'sonner';

// The first screen after signing in: clock in for the shift, or clock out
// if this login is someone finishing up. Never a hard gate — "Skip" always
// gets straight into the app, since an owner checking something quickly
// shouldn't have to clock in and out to do it.
export default function ClockInPrompt() {
  const { theme, darkMode } = useTheme();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [breakMins, setBreakMins] = useState('0');

  useEffect(() => {
    staffMgmtAPI.myStatus().then(r => setStatus(r.data)).catch(() => setStatus({ clockedIn: false })).finally(() => setLoading(false));
  }, []);

  const goToApp = () => navigate('/', { replace: true });

  const handleClockIn = async () => {
    setBusy(true);
    try { await staffMgmtAPI.clockIn(); toast.success("Clocked in — have a great shift!"); goToApp(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Failed to clock in'); setBusy(false); }
  };

  const handleClockOut = async () => {
    setBusy(true);
    try { await staffMgmtAPI.clockOut({ breakMinutes: parseInt(breakMins, 10) || 0 }); toast.success('Clocked out — see you next shift!'); goToApp(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Failed to clock out'); setBusy(false); }
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center"><div className="animate-pulse text-gray-400">Loading...</div></div>;
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: darkMode ? '#0b0b0f' : '#f6f7fb' }} data-testid="clock-in-prompt-page">
      <Card className="w-full max-w-sm border-0 shadow-lg">
        <CardContent className="p-8 text-center">
          <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4"
            style={{ background: `${theme.primary}15`, color: theme.primary }}>
            <Clock size={26} />
          </div>

          {status?.clockedIn ? (
            <>
              <h1 className="text-lg font-bold mb-1" style={{ color: darkMode ? '#eaeaea' : '#111827' }}>
                Welcome back, {user?.name?.split(' ')[0]}
              </h1>
              <p className="text-sm text-gray-400 mb-6">
                You've been clocked in since {new Date(status.currentShift?.clockIn).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}.
              </p>
              <div className="mb-4">
                <label className="text-xs text-gray-400 block mb-1">Break minutes (if clocking out)</label>
                <input type="number" min="0" value={breakMins} onChange={e => setBreakMins(e.target.value)}
                  className="w-full text-center rounded-lg border px-3 py-2 text-sm"
                  style={{ background: darkMode ? '#15151d' : '#fff', borderColor: darkMode ? '#242430' : '#e5e7eb', color: darkMode ? '#eaeaea' : '#111827' }}
                  data-testid="clock-in-prompt-break-minutes" />
              </div>
              <Button onClick={handleClockOut} disabled={busy} className="w-full h-11 mb-2 text-white font-medium"
                style={{ backgroundColor: '#ef4444' }} data-testid="clock-in-prompt-clock-out">
                <LogOut size={16} className="mr-2" /> {busy ? 'Working...' : 'Clock Out'}
              </Button>
              <button onClick={goToApp} className="text-sm text-gray-400 hover:text-gray-600 flex items-center justify-center gap-1 w-full py-2" data-testid="clock-in-prompt-continue">
                Stay clocked in — continue <ArrowRight size={14} />
              </button>
            </>
          ) : (
            <>
              <h1 className="text-lg font-bold mb-1" style={{ color: darkMode ? '#eaeaea' : '#111827' }}>
                Welcome, {user?.name?.split(' ')[0]}
              </h1>
              <p className="text-sm text-gray-400 mb-6">Ready to start your shift?</p>
              <Button onClick={handleClockIn} disabled={busy} className="w-full h-11 mb-2 text-white font-medium"
                style={{ backgroundColor: theme.primary }} data-testid="clock-in-prompt-clock-in">
                <LogIn size={16} className="mr-2" /> {busy ? 'Working...' : 'Clock In'}
              </Button>
              <button onClick={goToApp} className="text-sm text-gray-400 hover:text-gray-600 flex items-center justify-center gap-1 w-full py-2" data-testid="clock-in-prompt-skip">
                Skip for now <ArrowRight size={14} />
              </button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
