import React, { useState, useEffect } from 'react';
import {
  Clock, LogIn, LogOut, Calendar, DollarSign, Users, FileText,
  Plus, Trash2, BarChart3, Printer
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { staffMgmtAPI } from '../services/api';
import { toast } from 'sonner';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;
const authHeader = () => ({ Authorization: `Bearer ${localStorage.getItem('nuva_token')}` });
const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const POSITIONS = ['Barista', 'Bar', 'Floor', 'Kitchen', 'Register', 'Manager', 'Host', 'Dishwasher'];

export default function StaffRoster() {
  const { theme } = useTheme();
  const { user } = useAuth();
  const isOwner = user?.role === 'owner';
  const isManager = user?.role === 'manager';
  const canManage = isOwner || isManager;
  const [tab, setTab] = useState('roster');
  const [clockStatus, setClockStatus] = useState(null);
  const [timecards, setTimecards] = useState([]);
  const [roster, setRoster] = useState([]);
  const [staff, setStaff] = useState([]);
  const [payrun, setPayrun] = useState(null);
  const [payHistory, setPayHistory] = useState([]);
  const [staffReports, setStaffReports] = useState(null);
  const [reportPeriod, setReportPeriod] = useState('week');
  const [payPeriod, setPayPeriod] = useState('week');
  const [breakMins, setBreakMins] = useState('0');
  // Week roster form
  const [showWeekRoster, setShowWeekRoster] = useState(false);
  const [weekForm, setWeekForm] = useState({ staffId: '', position: 'Floor', weekStart: '', shifts: {} });

  useEffect(() => { fetchAll(); }, []);
  useEffect(() => { fetchReports(); }, [reportPeriod]);

  const fetchAll = async () => {
    try {
      const [status, tc, ros, st] = await Promise.all([
        staffMgmtAPI.myStatus(), staffMgmtAPI.getTimecards(),
        staffMgmtAPI.getRoster(), axios.get(`${API}/api/auth/staff`, { headers: authHeader() }),
      ]);
      setClockStatus(status.data);
      setTimecards(tc.data);
      setRoster(ros.data);
      setStaff(st.data.filter(s => s.role !== 'owner'));
    } catch {}
    if (isOwner) {
      try { const h = await staffMgmtAPI.getPayrunHistory(); setPayHistory(h.data); } catch {}
    }
  };

  const fetchReports = async () => {
    if (canManage) {
      try { const r = await staffMgmtAPI.getStaffReports({ period: reportPeriod }); setStaffReports(r.data); } catch {}
    }
  };

  const handleClockIn = async () => { try { await staffMgmtAPI.clockIn(); toast.success('Clocked in!'); fetchAll(); } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); } };
  const handleClockOut = async () => { try { await staffMgmtAPI.clockOut({ breakMinutes: parseInt(breakMins) || 0 }); toast.success('Clocked out!'); fetchAll(); } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); } };
  const handleDeleteShift = async (id) => { try { await staffMgmtAPI.deleteRosterShift(id); toast.success('Shift removed'); fetchAll(); } catch {} };

  // Week Roster — add shifts for entire week at once
  const handleAddWeekRoster = async () => {
    const staffMember = staff.find(s => s.id === weekForm.staffId);
    if (!staffMember) { toast.error('Select a staff member'); return; }
    const activeDays = Object.entries(weekForm.shifts).filter(([_, v]) => v.enabled);
    if (activeDays.length === 0) { toast.error('Select at least one day'); return; }

    let created = 0;
    for (const [day, shift] of activeDays) {
      try {
        await staffMgmtAPI.createRosterShift({
          staffId: weekForm.staffId, staffName: staffMember.name,
          date: day, weekStart: weekForm.weekStart,
          startTime: shift.startTime, endTime: shift.endTime,
          role: weekForm.position, notes: weekForm.position,
        });
        created++;
      } catch {}
    }
    toast.success(`${created} shifts added for ${staffMember.name}`);
    setShowWeekRoster(false);
    setWeekForm({ staffId: '', position: 'Floor', weekStart: '', shifts: {} });
    fetchAll();
  };

  // Calculate weekly budget from roster
  const getWeeklyBudget = () => {
    let totalHours = 0;
    let totalCost = 0;
    const dayCosts = {};
    roster.forEach(s => {
      const staffMember = staff.find(st => st.id === s.staffId) || {};
      const start = s.startTime?.split(':').map(Number) || [0, 0];
      const end = s.endTime?.split(':').map(Number) || [0, 0];
      const hours = Math.max((end[0] + end[1] / 60) - (start[0] + start[1] / 60), 0);
      const cost = hours * (staffMember.payRate || 0);
      totalHours += hours;
      totalCost += cost;
      const day = s.date || 'Unknown';
      dayCosts[day] = (dayCosts[day] || 0) + cost;
    });
    return { totalHours: totalHours.toFixed(1), totalCost: totalCost.toFixed(2), dayCosts };
  };

  // PRINT ROSTER — No wages, no tips
  const printRoster = () => {
    const w = window.open('', '_blank', 'width=800,height=600');
    const grouped = {};
    roster.forEach(s => {
      const day = s.date || 'Unassigned';
      if (!grouped[day]) grouped[day] = [];
      grouped[day].push(s);
    });
    w.document.write(`<html><head><title>Staff Roster</title><style>
      body{font-family:sans-serif;max-width:700px;margin:20px auto;font-size:13px}
      h1{text-align:center;font-size:20px;margin-bottom:5px}
      h2{font-size:14px;margin:15px 0 5px;padding:5px;background:#f3f4f6;border-radius:4px}
      table{width:100%;border-collapse:collapse;margin-bottom:15px}
      th,td{text-align:left;padding:6px 10px;border-bottom:1px solid #e5e7eb}
      th{background:#f9fafb;font-weight:600;font-size:11px;text-transform:uppercase;color:#6b7280}
      .pos{background:#e0f2fe;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:500}
      @media print{body{margin:0}}
    </style></head><body>
    <h1>NUVA POS — Staff Roster</h1>
    <p style="text-align:center;color:#6b7280;font-size:11px">Printed: ${new Date().toLocaleDateString()}</p>`);

    Object.entries(grouped).sort().forEach(([day, shifts]) => {
      w.document.write(`<h2>${day}</h2><table><thead><tr><th>Staff</th><th>Position</th><th>Start</th><th>End</th></tr></thead><tbody>`);
      shifts.forEach(s => {
        w.document.write(`<tr><td><strong>${s.staffName}</strong></td><td><span class="pos">${s.notes || s.role || '-'}</span></td><td>${s.startTime}</td><td>${s.endTime}</td></tr>`);
      });
      w.document.write('</tbody></table>');
    });

    w.document.write('</body></html>');
    w.document.close();
    w.print();
  };

  const handleCalcPayrun = async () => { try { const r = await staffMgmtAPI.calculatePayrun({ period: payPeriod }); setPayrun(r.data); } catch { toast.error('Failed'); } };
  const handleProcessPayrun = async () => { if (!payrun) return; try { await staffMgmtAPI.processPayrun(payrun); toast.success('Payrun processed'); setPayrun(null); fetchAll(); } catch { toast.error('Failed'); } };

  const budget = getWeeklyBudget();

  return (
    <div className="space-y-6" data-testid="staff-roster-page">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold" style={{ color: theme.text }}>Staff Management</h1><p className="text-sm text-gray-500">Timecards, weekly roster, payrun & reports</p></div>
        <div className="flex items-center gap-3">
          {clockStatus?.clockedIn ? (
            <div className="flex items-center gap-2">
              <Badge className="bg-green-100 text-green-700">Clocked In</Badge>
              <Input type="number" placeholder="Break mins" className="w-24 h-9" value={breakMins} onChange={e => setBreakMins(e.target.value)} data-testid="break-mins" />
              <Button onClick={handleClockOut} className="bg-red-600 hover:bg-red-700 text-white" data-testid="clock-out-btn"><LogOut size={16} className="mr-1" /> Clock Out</Button>
            </div>
          ) : (
            <Button onClick={handleClockIn} style={{ backgroundColor: theme.primary }} data-testid="clock-in-btn"><LogIn size={16} className="mr-1" /> Clock In</Button>
          )}
        </div>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="roster">Roster</TabsTrigger>
          <TabsTrigger value="timecards">Timecards</TabsTrigger>
          {isOwner && <TabsTrigger value="payrun">Payrun</TabsTrigger>}
          {canManage && <TabsTrigger value="reports">Reports</TabsTrigger>}
        </TabsList>

        {/* ROSTER */}
        <TabsContent value="roster" className="mt-4 space-y-4">
          {/* Budget Summary (owner/manager only) */}
          {canManage && roster.length > 0 && (
            <div className="grid grid-cols-3 gap-4">
              <Card><CardContent className="p-4 text-center"><p className="text-sm text-gray-500">Total Shifts</p><p className="text-2xl font-bold" style={{ color: theme.primary }}>{roster.length}</p></CardContent></Card>
              <Card><CardContent className="p-4 text-center"><p className="text-sm text-gray-500">Total Hours</p><p className="text-2xl font-bold text-blue-600">{budget.totalHours}h</p></CardContent></Card>
              <Card><CardContent className="p-4 text-center"><p className="text-sm text-gray-500">Weekly Budget</p><p className="text-2xl font-bold text-emerald-600">${budget.totalCost}</p></CardContent></Card>
            </div>
          )}

          <div className="flex justify-between items-center">
            <h3 className="font-semibold">Scheduled Shifts</h3>
            <div className="flex gap-2">
              {roster.length > 0 && <Button size="sm" variant="outline" onClick={printRoster} data-testid="print-roster-btn"><Printer size={14} className="mr-1" /> Print Roster</Button>}
              {canManage && <Button size="sm" style={{ backgroundColor: theme.primary }} onClick={() => setShowWeekRoster(true)} data-testid="add-week-roster-btn"><Plus size={14} className="mr-1" /> Add Week Roster</Button>}
            </div>
          </div>

          <Card><CardContent className="p-0"><div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="roster-table">
              <thead className="bg-gray-50"><tr>
                <th className="text-left p-3 font-medium text-gray-500">Staff</th>
                <th className="text-left p-3 font-medium text-gray-500">Position</th>
                <th className="text-left p-3 font-medium text-gray-500">Day/Date</th>
                <th className="text-left p-3 font-medium text-gray-500">Start</th>
                <th className="text-left p-3 font-medium text-gray-500">End</th>
                <th className="text-right p-3 font-medium text-gray-500">Hours</th>
                {canManage && <th className="text-right p-3 font-medium text-gray-500">Cost</th>}
                {canManage && <th className="text-center p-3 font-medium text-gray-500">Actions</th>}
              </tr></thead>
              <tbody>
                {roster.map(s => {
                  const staffMember = staff.find(st => st.id === s.staffId) || {};
                  const start = s.startTime?.split(':').map(Number) || [0, 0];
                  const end = s.endTime?.split(':').map(Number) || [0, 0];
                  const hours = Math.max((end[0] + end[1] / 60) - (start[0] + start[1] / 60), 0);
                  const cost = hours * (staffMember.payRate || 0);
                  return (
                    <tr key={s.id} className="border-t hover:bg-gray-50" data-testid={`roster-row-${s.id}`}>
                      <td className="p-3 font-medium">{s.staffName}</td>
                      <td className="p-3"><Badge variant="outline" className="text-xs">{s.notes || s.role || '-'}</Badge></td>
                      <td className="p-3 text-sm">{s.date}</td>
                      <td className="p-3">{s.startTime}</td>
                      <td className="p-3">{s.endTime}</td>
                      <td className="p-3 text-right font-medium">{hours.toFixed(1)}h</td>
                      {canManage && <td className="p-3 text-right font-mono text-emerald-600">${cost.toFixed(2)}</td>}
                      {canManage && <td className="p-3 text-center"><Button variant="ghost" size="sm" className="text-red-500" onClick={() => handleDeleteShift(s.id)}><Trash2 size={14} /></Button></td>}
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {roster.length === 0 && <p className="text-center text-gray-400 py-8">No shifts scheduled. Click "Add Week Roster" to get started.</p>}
          </div></CardContent></Card>
        </TabsContent>

        {/* TIMECARDS */}
        <TabsContent value="timecards" className="mt-4">
          <Card><CardContent className="p-0"><div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="timecards-table">
              <thead className="bg-gray-50"><tr>
                <th className="text-left p-3 font-medium text-gray-500">Staff</th>
                <th className="text-left p-3 font-medium text-gray-500">Role</th>
                <th className="text-left p-3 font-medium text-gray-500">Clock In</th>
                <th className="text-left p-3 font-medium text-gray-500">Clock Out</th>
                <th className="text-right p-3 font-medium text-gray-500">Break</th>
                <th className="text-right p-3 font-medium text-gray-500">Hours</th>
                {canManage && <th className="text-right p-3 font-medium text-gray-500">Cost</th>}
              </tr></thead>
              <tbody>
                {timecards.map(tc => (
                  <tr key={tc.id} className="border-t hover:bg-gray-50">
                    <td className="p-3 font-medium">{tc.staffName}</td>
                    <td className="p-3"><Badge variant="outline" className="capitalize text-xs">{tc.role}</Badge></td>
                    <td className="p-3 text-xs">{new Date(tc.clockIn).toLocaleString()}</td>
                    <td className="p-3 text-xs">{tc.clockOut ? new Date(tc.clockOut).toLocaleString() : <Badge className="bg-green-100 text-green-700 text-xs">Active</Badge>}</td>
                    <td className="p-3 text-right">{tc.breakMinutes}m</td>
                    <td className="p-3 text-right font-bold">{tc.hoursWorked}h</td>
                    {canManage && <td className="p-3 text-right font-mono" style={{ color: theme.primary }}>${(tc.hoursWorked * (tc.payRate || 0)).toFixed(2)}</td>}
                  </tr>
                ))}
              </tbody>
            </table>
            {timecards.length === 0 && <p className="text-center text-gray-400 py-8">No timecards yet. Clock in to start.</p>}
          </div></CardContent></Card>
        </TabsContent>

        {/* PAYRUN */}
        {isOwner && (
          <TabsContent value="payrun" className="mt-4">
            <div className="flex items-center gap-3 mb-4">
              <select className="p-2 border rounded-md text-sm" value={payPeriod} onChange={e => setPayPeriod(e.target.value)} data-testid="payrun-period">
                <option value="week">This Week</option><option value="fortnight">Fortnight</option><option value="month">This Month</option><option value="quarter">This Quarter</option><option value="year">This Year</option>
              </select>
              <Button style={{ backgroundColor: theme.primary }} onClick={handleCalcPayrun} data-testid="calc-payrun-btn"><DollarSign size={16} className="mr-1" /> Calculate Payrun</Button>
            </div>
            {payrun && (
              <div className="space-y-4">
                <div className="grid grid-cols-4 gap-4">
                  <Card><CardContent className="p-4 text-center"><p className="text-sm text-gray-500">Gross Pay</p><p className="text-2xl font-bold" style={{ color: theme.primary }}>${payrun.totals.grossPay}</p></CardContent></Card>
                  <Card><CardContent className="p-4 text-center"><p className="text-sm text-gray-500">Super (11.5%)</p><p className="text-2xl font-bold text-blue-600">${payrun.totals.super}</p></CardContent></Card>
                  <Card><CardContent className="p-4 text-center"><p className="text-sm text-gray-500">Tax</p><p className="text-2xl font-bold text-amber-600">${payrun.totals.tax}</p></CardContent></Card>
                  <Card><CardContent className="p-4 text-center"><p className="text-sm text-gray-500">Net Pay</p><p className="text-2xl font-bold text-emerald-600">${payrun.totals.netPay}</p></CardContent></Card>
                </div>
                <Card><CardContent className="p-0"><table className="w-full text-sm"><thead className="bg-gray-50"><tr><th className="text-left p-3">Staff</th><th className="text-left p-3">Role</th><th className="text-right p-3">Rate</th><th className="text-right p-3">Hours</th><th className="text-right p-3">Gross</th><th className="text-right p-3">Super</th><th className="text-right p-3">Tax</th><th className="text-right p-3">Net</th></tr></thead><tbody>
                  {payrun.staffPayroll.map(s => (<tr key={s.staffId} className="border-t"><td className="p-3 font-medium">{s.name}</td><td className="p-3"><Badge variant="outline" className="capitalize text-xs">{s.role}</Badge></td><td className="p-3 text-right">${s.payRate}/hr</td><td className="p-3 text-right">{s.totalHours}h</td><td className="p-3 text-right font-bold">${s.grossPay}</td><td className="p-3 text-right">${s.super}</td><td className="p-3 text-right">${s.tax}</td><td className="p-3 text-right font-bold text-emerald-600">${s.netPay}</td></tr>))}
                </tbody></table></CardContent></Card>
                <Button className="bg-emerald-600 hover:bg-emerald-700 text-white" onClick={handleProcessPayrun} data-testid="process-payrun-btn"><FileText size={16} className="mr-1" /> Process Payrun</Button>
              </div>
            )}
            {payHistory.length > 0 && (<div className="mt-6"><h3 className="font-semibold mb-3">Payrun History</h3><div className="space-y-2">{payHistory.map(p => (<Card key={p.id}><CardContent className="p-4 flex items-center justify-between"><div><span className="font-mono text-sm">{p.id}</span><span className="text-gray-500 text-sm ml-3">{p.period}</span></div><div className="text-right"><p className="font-bold" style={{ color: theme.primary }}>${p.totals?.grossPay || 0}</p><p className="text-xs text-gray-500">{new Date(p.processedAt).toLocaleDateString()}</p></div></CardContent></Card>))}</div></div>)}
          </TabsContent>
        )}

        {/* REPORTS */}
        {canManage && (
          <TabsContent value="reports" className="mt-4">
            <div className="flex items-center gap-3 mb-4">
              {['week', 'month', 'quarter', 'year'].map(p => (
                <Button key={p} size="sm" variant={reportPeriod === p ? 'default' : 'outline'} style={reportPeriod === p ? { backgroundColor: theme.primary } : {}} onClick={() => setReportPeriod(p)} data-testid={`report-period-${p}`}>{p.charAt(0).toUpperCase() + p.slice(1)}</Button>
              ))}
            </div>
            {staffReports && (
              <div className="space-y-4">
                <div className="grid grid-cols-4 gap-4">
                  <Card><CardContent className="p-4 text-center"><p className="text-sm text-gray-500">Total Staff</p><p className="text-2xl font-bold">{staffReports.summary.totalStaff}</p></CardContent></Card>
                  <Card><CardContent className="p-4 text-center"><p className="text-sm text-gray-500">Total Hours</p><p className="text-2xl font-bold" style={{ color: theme.primary }}>{staffReports.summary.totalHours}h</p></CardContent></Card>
                  <Card><CardContent className="p-4 text-center"><p className="text-sm text-gray-500">Total Wages</p><p className="text-2xl font-bold text-emerald-600">${staffReports.summary.totalWages}</p></CardContent></Card>
                  <Card><CardContent className="p-4 text-center"><p className="text-sm text-gray-500">Payruns</p><p className="text-2xl font-bold text-blue-600">{staffReports.summary.totalPayruns}</p></CardContent></Card>
                </div>
                <Card><CardContent className="p-0"><table className="w-full text-sm" data-testid="staff-reports-table"><thead className="bg-gray-50"><tr><th className="text-left p-3">Staff</th><th className="text-left p-3">Role</th><th className="text-right p-3">Rate</th><th className="text-right p-3">Shifts</th><th className="text-right p-3">Hours</th><th className="text-right p-3">Avg/Shift</th><th className="text-right p-3">Total Wages</th><th className="text-center p-3">Status</th></tr></thead><tbody>
                  {staffReports.staffStats.map(s => (<tr key={s.id} className="border-t"><td className="p-3 font-medium">{s.name}</td><td className="p-3"><Badge variant="outline" className="capitalize text-xs">{s.role}</Badge></td><td className="p-3 text-right">${s.payRate}/hr</td><td className="p-3 text-right">{s.totalShifts}</td><td className="p-3 text-right">{s.totalHours}h</td><td className="p-3 text-right">{s.avgHoursPerShift}h</td><td className="p-3 text-right font-bold" style={{ color: theme.primary }}>${s.totalWages}</td><td className="p-3 text-center">{s.currentlyClockedIn ? <Badge className="bg-green-100 text-green-700 text-xs">Active</Badge> : <Badge variant="outline" className="text-xs">Off</Badge>}</td></tr>))}
                </tbody></table></CardContent></Card>
              </div>
            )}
          </TabsContent>
        )}
      </Tabs>

      {/* Add Week Roster Dialog */}
      <Dialog open={showWeekRoster} onOpenChange={setShowWeekRoster}>
        <DialogContent className="max-w-lg" data-testid="week-roster-dialog">
          <DialogHeader><DialogTitle>Add Week Roster</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2 max-h-[70vh] overflow-y-auto">
            <select className="w-full p-2 border rounded-md text-sm" value={weekForm.staffId} onChange={e => setWeekForm({ ...weekForm, staffId: e.target.value })} data-testid="week-staff-select">
              <option value="">Select staff member...</option>
              {staff.map(s => <option key={s.id} value={s.id}>{s.name} ({s.role})</option>)}
            </select>
            <select className="w-full p-2 border rounded-md text-sm" value={weekForm.position} onChange={e => setWeekForm({ ...weekForm, position: e.target.value })} data-testid="week-position-select">
              {POSITIONS.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
            <div><label className="text-xs font-medium text-gray-500 mb-1 block">Week Starting (for reference)</label>
              <Input type="date" value={weekForm.weekStart} onChange={e => setWeekForm({ ...weekForm, weekStart: e.target.value })} data-testid="week-start-date" />
            </div>

            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-700">Select days and times:</p>
              {DAYS.map(day => {
                const shift = weekForm.shifts[day] || { enabled: false, startTime: '09:00', endTime: '17:00' };
                return (
                  <div key={day} className="flex items-center gap-3 p-2 rounded-lg border" data-testid={`week-day-${day.toLowerCase()}`}>
                    <label className="flex items-center gap-2 w-28 cursor-pointer">
                      <input type="checkbox" checked={shift.enabled} onChange={e => setWeekForm({ ...weekForm, shifts: { ...weekForm.shifts, [day]: { ...shift, enabled: e.target.checked } } })} />
                      <span className="text-sm font-medium">{day.slice(0, 3)}</span>
                    </label>
                    {shift.enabled && (
                      <div className="flex items-center gap-2 flex-1">
                        <Input type="time" className="h-8 text-sm flex-1" value={shift.startTime} onChange={e => setWeekForm({ ...weekForm, shifts: { ...weekForm.shifts, [day]: { ...shift, startTime: e.target.value } } })} />
                        <span className="text-gray-400 text-xs">to</span>
                        <Input type="time" className="h-8 text-sm flex-1" value={shift.endTime} onChange={e => setWeekForm({ ...weekForm, shifts: { ...weekForm.shifts, [day]: { ...shift, endTime: e.target.value } } })} />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Preview cost */}
            {weekForm.staffId && (() => {
              const staffMember = staff.find(s => s.id === weekForm.staffId);
              const rate = staffMember?.payRate || 0;
              const totalHrs = Object.values(weekForm.shifts).filter(s => s.enabled).reduce((sum, s) => {
                const st = s.startTime?.split(':').map(Number) || [0, 0];
                const en = s.endTime?.split(':').map(Number) || [0, 0];
                return sum + Math.max((en[0] + en[1] / 60) - (st[0] + st[1] / 60), 0);
              }, 0);
              return totalHrs > 0 ? (
                <div className="p-3 bg-gray-50 rounded-lg text-sm">
                  <div className="flex justify-between"><span>Total Hours:</span><span className="font-bold">{totalHrs.toFixed(1)}h</span></div>
                  <div className="flex justify-between"><span>Rate:</span><span>${rate}/hr</span></div>
                  <div className="flex justify-between text-emerald-700 font-bold"><span>Estimated Cost:</span><span>${(totalHrs * rate).toFixed(2)}</span></div>
                </div>
              ) : null;
            })()}

            <Button className="w-full" style={{ backgroundColor: theme.primary }} onClick={handleAddWeekRoster} data-testid="save-week-roster-btn">Add Week Roster</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
