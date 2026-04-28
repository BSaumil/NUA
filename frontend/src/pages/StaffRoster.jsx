import React, { useState, useEffect } from 'react';
import {
  Clock, LogIn, LogOut, Calendar, DollarSign, Users, FileText,
  Plus, Trash2, BarChart3, Download
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

export default function StaffRoster() {
  const { theme } = useTheme();
  const { user } = useAuth();
  const isOwner = user?.role === 'owner';
  const [tab, setTab] = useState('timecards');
  const [clockStatus, setClockStatus] = useState(null);
  const [timecards, setTimecards] = useState([]);
  const [roster, setRoster] = useState([]);
  const [staff, setStaff] = useState([]);
  const [payrun, setPayrun] = useState(null);
  const [payHistory, setPayHistory] = useState([]);
  const [staffReports, setStaffReports] = useState(null);
  const [reportPeriod, setReportPeriod] = useState('week');
  const [payPeriod, setPayPeriod] = useState('week');
  const [showAddShift, setShowAddShift] = useState(false);
  const [shiftForm, setShiftForm] = useState({ staffId: '', staffName: '', date: '', startTime: '09:00', endTime: '17:00', notes: '' });
  const [breakMins, setBreakMins] = useState('0');

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
    if (user?.role === 'owner' || user?.role === 'manager') {
      try { const r = await staffMgmtAPI.getStaffReports({ period: reportPeriod }); setStaffReports(r.data); } catch {}
    }
  };

  const handleClockIn = async () => {
    try { await staffMgmtAPI.clockIn(); toast.success('Clocked in!'); fetchAll(); } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };
  const handleClockOut = async () => {
    try { await staffMgmtAPI.clockOut({ breakMinutes: parseInt(breakMins) || 0 }); toast.success('Clocked out!'); fetchAll(); } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  const handleAddShift = async () => {
    const s = staff.find(x => x.id === shiftForm.staffId);
    try {
      await staffMgmtAPI.createRosterShift({ ...shiftForm, staffName: s?.name || '', role: s?.role || '' });
      toast.success('Shift added'); setShowAddShift(false); fetchAll();
    } catch { toast.error('Failed'); }
  };

  const handleDeleteShift = async (id) => {
    try { await staffMgmtAPI.deleteRosterShift(id); toast.success('Shift removed'); fetchAll(); } catch {}
  };

  const handleCalcPayrun = async () => {
    try { const r = await staffMgmtAPI.calculatePayrun({ period: payPeriod }); setPayrun(r.data); } catch { toast.error('Failed'); }
  };

  const handleProcessPayrun = async () => {
    if (!payrun) return;
    try { await staffMgmtAPI.processPayrun(payrun); toast.success('Payrun processed & logged to Accounting'); setPayrun(null); fetchAll(); } catch { toast.error('Failed'); }
  };

  return (
    <div className="space-y-6" data-testid="staff-roster-page">
      <div className="flex items-center justify-between">
        <div><h1 className="text-3xl font-bold" style={{ color: theme.text }}>Staff Management</h1><p className="text-gray-500 mt-1">Timecards, roster, payrun & reports</p></div>
        {/* Clock In/Out */}
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
          <TabsTrigger value="timecards">Timecards</TabsTrigger>
          <TabsTrigger value="roster">Roster</TabsTrigger>
          {isOwner && <TabsTrigger value="payrun">Payrun</TabsTrigger>}
          {(isOwner || user?.role === 'manager') && <TabsTrigger value="reports">Reports</TabsTrigger>}
        </TabsList>

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
                <th className="text-right p-3 font-medium text-gray-500">Cost</th>
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
                    <td className="p-3 text-right font-mono" style={{ color: theme.primary }}>${(tc.hoursWorked * (tc.payRate || 0)).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {timecards.length === 0 && <p className="text-center text-gray-400 py-8">No timecards yet. Clock in to start.</p>}
          </div></CardContent></Card>
        </TabsContent>

        {/* ROSTER */}
        <TabsContent value="roster" className="mt-4">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-semibold">Scheduled Shifts</h3>
            {(isOwner || user?.role === 'manager') && <Button size="sm" style={{ backgroundColor: theme.primary }} onClick={() => setShowAddShift(true)} data-testid="add-shift-btn"><Plus size={14} className="mr-1" /> Add Shift</Button>}
          </div>
          <Card><CardContent className="p-0"><div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="roster-table">
              <thead className="bg-gray-50"><tr>
                <th className="text-left p-3 font-medium text-gray-500">Staff</th>
                <th className="text-left p-3 font-medium text-gray-500">Date</th>
                <th className="text-left p-3 font-medium text-gray-500">Start</th>
                <th className="text-left p-3 font-medium text-gray-500">End</th>
                <th className="text-left p-3 font-medium text-gray-500">Notes</th>
                {(isOwner || user?.role === 'manager') && <th className="text-center p-3 font-medium text-gray-500">Actions</th>}
              </tr></thead>
              <tbody>
                {roster.map(s => (
                  <tr key={s.id} className="border-t hover:bg-gray-50">
                    <td className="p-3 font-medium">{s.staffName}</td>
                    <td className="p-3">{s.date}</td>
                    <td className="p-3">{s.startTime}</td>
                    <td className="p-3">{s.endTime}</td>
                    <td className="p-3 text-gray-500">{s.notes}</td>
                    {(isOwner || user?.role === 'manager') && <td className="p-3 text-center"><Button variant="ghost" size="sm" className="text-red-500" onClick={() => handleDeleteShift(s.id)}><Trash2 size={14} /></Button></td>}
                  </tr>
                ))}
              </tbody>
            </table>
            {roster.length === 0 && <p className="text-center text-gray-400 py-8">No shifts scheduled</p>}
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
                  <Card><CardContent className="p-4 text-center"><p className="text-sm text-gray-500">Tax Withholding</p><p className="text-2xl font-bold text-amber-600">${payrun.totals.tax}</p></CardContent></Card>
                  <Card><CardContent className="p-4 text-center"><p className="text-sm text-gray-500">Net Pay</p><p className="text-2xl font-bold text-emerald-600">${payrun.totals.netPay}</p></CardContent></Card>
                </div>
                <Card><CardContent className="p-0"><table className="w-full text-sm">
                  <thead className="bg-gray-50"><tr>
                    <th className="text-left p-3">Staff</th><th className="text-left p-3">Role</th><th className="text-right p-3">Rate</th><th className="text-right p-3">Hours</th><th className="text-right p-3">Gross</th><th className="text-right p-3">Super</th><th className="text-right p-3">Tax</th><th className="text-right p-3">Net</th>
                  </tr></thead>
                  <tbody>
                    {payrun.staffPayroll.map(s => (
                      <tr key={s.staffId} className="border-t"><td className="p-3 font-medium">{s.name}</td><td className="p-3"><Badge variant="outline" className="capitalize text-xs">{s.role}</Badge></td><td className="p-3 text-right">${s.payRate}/hr</td><td className="p-3 text-right">{s.totalHours}h</td><td className="p-3 text-right font-bold">${s.grossPay}</td><td className="p-3 text-right">${s.super}</td><td className="p-3 text-right">${s.tax}</td><td className="p-3 text-right font-bold text-emerald-600">${s.netPay}</td></tr>
                    ))}
                  </tbody>
                </table></CardContent></Card>
                <Button className="bg-emerald-600 hover:bg-emerald-700 text-white" onClick={handleProcessPayrun} data-testid="process-payrun-btn"><FileText size={16} className="mr-1" /> Process Payrun & Log to Accounting</Button>
              </div>
            )}

            {payHistory.length > 0 && (
              <div className="mt-6">
                <h3 className="font-semibold mb-3">Payrun History</h3>
                <div className="space-y-2">
                  {payHistory.map(p => (
                    <Card key={p.id}><CardContent className="p-4 flex items-center justify-between">
                      <div><span className="font-mono text-sm">{p.id}</span><span className="text-gray-500 text-sm ml-3">{p.period}</span></div>
                      <div className="text-right"><p className="font-bold" style={{ color: theme.primary }}>${p.totals?.grossPay || 0}</p><p className="text-xs text-gray-500">{new Date(p.processedAt).toLocaleDateString()}</p></div>
                    </CardContent></Card>
                  ))}
                </div>
              </div>
            )}
          </TabsContent>
        )}

        {/* REPORTS */}
        {(isOwner || user?.role === 'manager') && (
          <TabsContent value="reports" className="mt-4">
            <div className="flex items-center gap-3 mb-4">
              {['week', 'month', 'quarter', 'year'].map(p => (
                <Button key={p} size="sm" variant={reportPeriod === p ? 'default' : 'outline'}
                  style={reportPeriod === p ? { backgroundColor: theme.primary } : {}}
                  onClick={() => setReportPeriod(p)} data-testid={`report-period-${p}`}>
                  {p.charAt(0).toUpperCase() + p.slice(1)}
                </Button>
              ))}
            </div>
            {staffReports && (
              <div className="space-y-4">
                <div className="grid grid-cols-4 gap-4">
                  <Card><CardContent className="p-4 text-center"><p className="text-sm text-gray-500">Total Staff</p><p className="text-2xl font-bold">{staffReports.summary.totalStaff}</p></CardContent></Card>
                  <Card><CardContent className="p-4 text-center"><p className="text-sm text-gray-500">Total Hours</p><p className="text-2xl font-bold" style={{ color: theme.primary }}>{staffReports.summary.totalHours}h</p></CardContent></Card>
                  <Card><CardContent className="p-4 text-center"><p className="text-sm text-gray-500">Total Wages</p><p className="text-2xl font-bold text-emerald-600">${staffReports.summary.totalWages}</p></CardContent></Card>
                  <Card><CardContent className="p-4 text-center"><p className="text-sm text-gray-500">Payruns Done</p><p className="text-2xl font-bold text-blue-600">{staffReports.summary.totalPayruns}</p></CardContent></Card>
                </div>
                <Card><CardContent className="p-0"><table className="w-full text-sm" data-testid="staff-reports-table">
                  <thead className="bg-gray-50"><tr>
                    <th className="text-left p-3">Staff</th><th className="text-left p-3">Role</th><th className="text-right p-3">Rate</th><th className="text-right p-3">Shifts</th><th className="text-right p-3">Hours</th><th className="text-right p-3">Avg/Shift</th><th className="text-right p-3">Total Wages</th><th className="text-center p-3">Status</th>
                  </tr></thead>
                  <tbody>
                    {staffReports.staffStats.map(s => (
                      <tr key={s.id} className="border-t"><td className="p-3 font-medium">{s.name}</td><td className="p-3"><Badge variant="outline" className="capitalize text-xs">{s.role}</Badge></td><td className="p-3 text-right">${s.payRate}/hr</td><td className="p-3 text-right">{s.totalShifts}</td><td className="p-3 text-right">{s.totalHours}h</td><td className="p-3 text-right">{s.avgHoursPerShift}h</td><td className="p-3 text-right font-bold" style={{ color: theme.primary }}>${s.totalWages}</td><td className="p-3 text-center">{s.currentlyClockedIn ? <Badge className="bg-green-100 text-green-700 text-xs">Active</Badge> : <Badge variant="outline" className="text-xs">Off</Badge>}</td></tr>
                    ))}
                  </tbody>
                </table></CardContent></Card>
              </div>
            )}
          </TabsContent>
        )}
      </Tabs>

      {/* Add Shift Dialog */}
      <Dialog open={showAddShift} onOpenChange={setShowAddShift}>
        <DialogContent className="max-w-sm" data-testid="add-shift-dialog">
          <DialogHeader><DialogTitle>Add Roster Shift</DialogTitle></DialogHeader>
          <div className="space-y-3 py-2">
            <select className="w-full p-2 border rounded-md text-sm" value={shiftForm.staffId} onChange={e => setShiftForm({ ...shiftForm, staffId: e.target.value })} data-testid="shift-staff-select">
              <option value="">Select staff...</option>
              {staff.map(s => <option key={s.id} value={s.id}>{s.name} ({s.role})</option>)}
            </select>
            <Input type="date" value={shiftForm.date} onChange={e => setShiftForm({ ...shiftForm, date: e.target.value })} data-testid="shift-date" />
            <div className="grid grid-cols-2 gap-2">
              <Input type="time" value={shiftForm.startTime} onChange={e => setShiftForm({ ...shiftForm, startTime: e.target.value })} data-testid="shift-start" />
              <Input type="time" value={shiftForm.endTime} onChange={e => setShiftForm({ ...shiftForm, endTime: e.target.value })} data-testid="shift-end" />
            </div>
            <Input placeholder="Notes (optional)" value={shiftForm.notes} onChange={e => setShiftForm({ ...shiftForm, notes: e.target.value })} />
            <Button className="w-full" style={{ backgroundColor: theme.primary }} onClick={handleAddShift} data-testid="save-shift-btn">Add Shift</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
