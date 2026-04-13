import React, { useState, useEffect } from 'react';
import { TrendingUp, Calendar, Users, DollarSign, BarChart3, Clock, Lightbulb, ArrowUpRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { useTheme } from '../contexts/ThemeContext';
import { forecastAPI } from '../services/api';

const BUSY_COLORS = { high: '#EF4444', medium: '#F59E0B', low: '#10B981' };

export default function Forecasting() {
  const { theme } = useTheme();
  const [tab, setTab] = useState('demand');
  const [demand, setDemand] = useState(null);
  const [tableTurns, setTableTurns] = useState(null);
  const [roster, setRoster] = useState(null);

  useEffect(() => {
    forecastAPI.getDemand().then(r => setDemand(r.data)).catch(() => {});
    forecastAPI.getTableTurns().then(r => setTableTurns(r.data)).catch(() => {});
    forecastAPI.getSmartRoster().then(r => setRoster(r.data)).catch(() => {});
  }, []);

  return (
    <div className="space-y-6" data-testid="forecasting-page">
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #3B82F6, #06B6D4)' }}>
          <TrendingUp size={24} className="text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold" style={{ color: theme.text }}>Forecasting & Optimization</h1>
          <p className="text-sm text-gray-500">Demand prediction, table turns & smart rostering</p>
        </div>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="demand" data-testid="tab-demand">7-Day Forecast</TabsTrigger>
          <TabsTrigger value="turns" data-testid="tab-turns">Table Turn-Time</TabsTrigger>
          <TabsTrigger value="roster" data-testid="tab-roster">Smart Rostering</TabsTrigger>
        </TabsList>

        {/* ===== DEMAND FORECAST ===== */}
        <TabsContent value="demand" className="mt-4">
          {!demand ? <p className="text-gray-400 text-center py-8">Loading forecast...</p> : (
            <div className="space-y-4">
              <div className="grid grid-cols-7 gap-3">
                {(demand.forecast || []).map((day, i) => {
                  const busyLevel = day.busyLevel || 'low';
                  const bColor = BUSY_COLORS[busyLevel];
                  const isToday = i === 0;
                  const covers = day.totalEstimatedCovers || day.predictedCovers || 0;
                  const staff = day.suggestedStaff || day.staffRecommendation || 0;
                  const revenue = day.predictedRevenue || (covers * 35);
                  const confidence = day.confidence || 72;
                  const dayName = day.dayOfWeek || day.dayName || '';
                  return (
                    <Card key={i} className={`border-0 shadow-sm ${isToday ? 'ring-2' : ''}`}
                      style={isToday ? { '--tw-ring-color': theme.primary } : {}} data-testid={`forecast-day-${i}`}>
                      <CardContent className="p-4 text-center">
                        <p className="text-xs text-gray-500">{isToday ? 'Today' : dayName.slice(0, 3)}</p>
                        <p className="text-xs font-mono text-gray-400">{(day.date || '').slice(5)}</p>
                        <div className="my-3">
                          <p className="text-xl font-bold" style={{ color: theme.primary }}>${Math.round(revenue)}</p>
                          <p className="text-[10px] text-gray-500">predicted</p>
                        </div>
                        <div className="space-y-1.5">
                          <div className="flex items-center justify-between text-[10px]">
                            <span className="text-gray-500">Covers</span>
                            <span className="font-bold">{covers}</span>
                          </div>
                          <div className="flex items-center justify-between text-[10px]">
                            <span className="text-gray-500">Staff</span>
                            <span className="font-bold">{staff}</span>
                          </div>
                          <Badge className="text-[10px] w-full justify-center" style={{ background: `${bColor}15`, color: bColor }}>
                            {busyLevel}
                          </Badge>
                        </div>
                        <div className="mt-2">
                          <div className="text-[10px] text-gray-400">{confidence}% conf</div>
                          <div className="w-full h-1 bg-gray-200 rounded-full mt-0.5">
                            <div className="h-full rounded-full" style={{ width: `${confidence}%`, background: theme.primary }} />
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </div>
          )}
        </TabsContent>

        {/* ===== TABLE TURNS ===== */}
        <TabsContent value="turns" className="mt-4">
          {!tableTurns ? <p className="text-gray-400 text-center py-8">Loading...</p> : (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <Card className="border-0 shadow-sm"><CardContent className="p-4">
                  <p className="text-xs text-gray-500">Avg Turn Time</p>
                  <p className="text-3xl font-bold" style={{ color: theme.primary }}>{tableTurns.avgTurnTime || 0}m</p>
                </CardContent></Card>
                <Card className="border-0 shadow-sm"><CardContent className="p-4">
                  <p className="text-xs text-gray-500">Revenue Opportunity</p>
                  <p className="text-3xl font-bold text-emerald-600">${tableTurns.optimization?.revenueOpportunity || 0}</p>
                </CardContent></Card>
                <Card className="border-0 shadow-sm"><CardContent className="p-4">
                  <p className="text-xs text-gray-500">Extra Covers Potential</p>
                  <p className="text-3xl font-bold" style={{ color: theme.text }}>{tableTurns.optimization?.potentialExtraCovers || 0}</p>
                </CardContent></Card>
              </div>
              {(tableTurns.byPartySize || []).length > 0 && (
                <Card className="border-0 shadow-sm">
                  <CardHeader className="pb-2"><CardTitle className="text-sm">Turn Time by Party Size</CardTitle></CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {tableTurns.byPartySize.map((a, i) => (
                        <div key={i} className="flex items-center gap-4 p-3 rounded-lg bg-gray-50">
                          <Badge variant="outline" className="font-mono">{a.partySize || a.size}</Badge>
                          <div className="flex-1">
                            <span className="text-sm">Avg: <strong>{a.avgTurnTime || a.avgTime || 0}min</strong></span>
                            <div className="w-full h-2 bg-gray-200 rounded-full mt-1">
                              <div className="h-full rounded-full" style={{ width: `${((a.avgTurnTime || a.avgTime || 0) / 180) * 100}%`, background: theme.primary }} />
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
              <Card className="border-0 shadow-sm">
                <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2"><Lightbulb size={14} className="text-amber-500" /> Optimization Insights</CardTitle></CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-600">Optimal turn time: <strong>{tableTurns.optimization?.optimalTurnTime || 0}m</strong></p>
                  <p className="text-sm text-gray-600 mt-1">Potential extra covers per day: <strong>{tableTurns.optimization?.potentialExtraCovers || 0}</strong></p>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        {/* ===== SMART ROSTER ===== */}
        <TabsContent value="roster" className="mt-4">
          {!roster ? <p className="text-gray-400 text-center py-8">Loading...</p> : (
            <Card className="border-0 shadow-sm">
              <CardHeader className="pb-2"><CardTitle className="text-sm">AI Roster Suggestions (Next 7 Days)</CardTitle></CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm" data-testid="roster-table">
                    <thead>
                      <tr className="border-b bg-gray-50/80">
                        <th className="text-left px-4 py-3 font-medium text-gray-500">Day</th>
                        <th className="text-center px-4 py-3 font-medium text-gray-500">Covers</th>
                        <th className="text-center px-4 py-3 font-medium text-gray-500">Servers</th>
                        <th className="text-center px-4 py-3 font-medium text-gray-500">Kitchen</th>
                        <th className="text-center px-4 py-3 font-medium text-gray-500">Bar</th>
                        <th className="text-center px-4 py-3 font-medium text-gray-500">Total Staff</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(roster.roster || roster.rosterSuggestions || []).map((day, i) => {
                        const roles = day.roles || day.staffNeeded || {};
                        const totalStaff = day.totalStaffNeeded || roles.total || (
                          (roles.servers || roles.front_of_house || 0) +
                          (roles.kitchen || 0) +
                          (roles.bartenders || roles.bar || 0) +
                          (roles.host || 0)
                        );
                        return (
                          <tr key={i} className="border-b hover:bg-gray-50/50">
                            <td className="px-4 py-3">
                              <p className="font-medium">{day.dayOfWeek || day.dayName}</p>
                              <p className="text-[10px] text-gray-400">{day.date}</p>
                            </td>
                            <td className="px-4 py-3 text-center font-medium">{day.expectedCovers || day.predictedCovers || 0}</td>
                            <td className="px-4 py-3 text-center">{roles.servers || roles.front_of_house || 0}</td>
                            <td className="px-4 py-3 text-center">{roles.kitchen || 0}</td>
                            <td className="px-4 py-3 text-center">{roles.bartenders || roles.bar || 0}</td>
                            <td className="px-4 py-3 text-center font-bold" style={{ color: theme.primary }}>{totalStaff}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
