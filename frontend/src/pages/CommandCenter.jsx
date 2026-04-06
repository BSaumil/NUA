import React, { useState, useEffect } from 'react';
import {
  Brain, TrendingUp, TrendingDown, DollarSign, Users, AlertTriangle,
  Zap, BarChart3, PieChart, Target, Lightbulb, Activity, ShoppingBag
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { useTheme } from '../contexts/ThemeContext';
import { analyticsAPI } from '../services/api';

const INSIGHT_ICONS = {
  warning: AlertTriangle,
  alert: Zap,
  info: Lightbulb,
};

export default function CommandCenter() {
  const { theme } = useTheme();
  const [data, setData] = useState(null);

  useEffect(() => {
    analyticsAPI.getCommandCenter().then(r => setData(r.data)).catch(console.error);
  }, []);

  if (!data) return <div className="flex items-center justify-center h-64 text-gray-400">Loading analytics...</div>;

  const { revenue, costs, profit, topSellers, lowPerformers, insights, customers } = data;

  return (
    <div className="space-y-6" data-testid="command-center-page">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: `linear-gradient(135deg, #6366F1, #EC4899)` }}>
          <Brain size={24} className="text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold" style={{ color: theme.text }}>AI Command Center</h1>
          <p className="text-sm text-gray-500">Real-time insights, margins & performance intelligence</p>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-6 gap-3">
        {[
          { label: 'Total Revenue', val: `$${revenue.total.toFixed(0)}`, icon: DollarSign, color: '#10B981' },
          { label: 'Avg Ticket', val: `$${revenue.avgTicket.toFixed(2)}`, icon: ShoppingBag, color: theme.primary },
          { label: 'Food Cost %', val: `${costs.foodCostPct.toFixed(1)}%`, icon: PieChart, color: costs.foodCostPct > 35 ? '#EF4444' : '#3B82F6' },
          { label: 'Labor Cost %', val: `${costs.laborPct.toFixed(1)}%`, icon: Users, color: costs.laborPct > 30 ? '#EF4444' : '#3B82F6' },
          { label: 'Gross Profit', val: `$${profit.gross.toFixed(0)}`, icon: TrendingUp, color: profit.gross > 0 ? '#10B981' : '#EF4444' },
          { label: 'Net Profit', val: `$${profit.net.toFixed(0)}`, icon: Target, color: profit.net > 0 ? '#10B981' : '#EF4444' },
        ].map((m, i) => (
          <Card key={i} className="border-0 shadow-sm">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <m.icon size={16} style={{ color: m.color }} />
                <span className="text-[10px] text-gray-500">{m.label}</span>
              </div>
              <p className="text-xl font-bold" style={{ color: m.color }}>{m.val}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* AI Insights */}
      {insights.length > 0 && (
        <Card className="border-0 shadow-sm" style={{ background: 'linear-gradient(135deg, #F5F3FF, #FDF2F8)' }}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Lightbulb size={16} className="text-purple-500" /> AI Insights & Recommendations
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {insights.map((insight, i) => {
              const Icon = INSIGHT_ICONS[insight.type] || Lightbulb;
              const colors = { warning: '#F59E0B', alert: '#EF4444', info: '#3B82F6' };
              return (
                <div key={i} className="flex items-start gap-3 p-3 bg-white/70 rounded-lg" data-testid={`insight-${i}`}>
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ background: `${colors[insight.type]}15` }}>
                    <Icon size={16} style={{ color: colors[insight.type] }} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold" style={{ color: theme.text }}>{insight.title}</p>
                      <Badge className="text-[10px]" style={{ background: `${colors[insight.type]}15`, color: colors[insight.type] }}>
                        {insight.priority}
                      </Badge>
                    </div>
                    <p className="text-xs text-gray-600 mt-0.5">{insight.message}</p>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-2 gap-4">
        {/* Top Sellers */}
        <Card className="border-0 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <TrendingUp size={16} className="text-green-500" /> Top Performing Items
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {topSellers.map((item, i) => (
                <div key={i} className="flex items-center gap-3 py-1.5">
                  <span className="w-5 text-xs text-gray-400 font-mono text-right">{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{item.name}</p>
                    <div className="flex items-center gap-2 text-[10px] text-gray-500">
                      <span>{item.quantity} sold</span>
                      <span>${item.revenue.toFixed(0)} rev</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold" style={{ color: item.margin >= 50 ? '#10B981' : item.margin >= 30 ? '#F59E0B' : '#EF4444' }}>
                      {item.margin.toFixed(0)}%
                    </p>
                    <p className="text-[10px] text-gray-400">margin</p>
                  </div>
                  <div className="w-16 h-1.5 bg-gray-200 rounded-full">
                    <div className="h-full rounded-full" style={{
                      width: `${Math.min(100, item.margin)}%`,
                      background: item.margin >= 50 ? '#10B981' : item.margin >= 30 ? '#F59E0B' : '#EF4444'
                    }} />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Low Performers */}
        <Card className="border-0 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <TrendingDown size={16} className="text-red-500" /> Low Margin Items (Review)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {lowPerformers.map((item, i) => (
                <div key={i} className="flex items-center gap-3 py-1.5 px-2 rounded-lg bg-red-50/50">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{item.name}</p>
                    <div className="flex items-center gap-2 text-[10px] text-gray-500">
                      <span>Price: ${item.price}</span>
                      <span>Cost: ${item.cost}</span>
                      <span>{item.quantity} sold</span>
                    </div>
                  </div>
                  <Badge className="bg-red-100 text-red-700 text-xs">{item.margin.toFixed(0)}%</Badge>
                </div>
              ))}
              {lowPerformers.length === 0 && <p className="text-xs text-gray-400 text-center py-4">No data yet</p>}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Customer & Service Stats */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="border-0 shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-1"><Users size={16} className="text-blue-500" /><span className="text-xs text-gray-500">Total Guests</span></div>
            <p className="text-3xl font-bold" style={{ color: theme.text }}>{customers.total}</p>
            <p className="text-xs text-gray-500 mt-1">{customers.vips} VIP guests</p>
          </CardContent>
        </Card>
        <Card className="border-0 shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-1"><Activity size={16} className="text-green-500" /><span className="text-xs text-gray-500">Today's Service</span></div>
            <p className="text-3xl font-bold" style={{ color: theme.text }}>{data.todayReservations}</p>
            <p className="text-xs text-gray-500 mt-1">{data.todayCovers} expected covers</p>
          </CardContent>
        </Card>
        <Card className="border-0 shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-1"><BarChart3 size={16} className="text-purple-500" /><span className="text-xs text-gray-500">Avg Guest Rating</span></div>
            <p className="text-3xl font-bold" style={{ color: theme.text }}>{customers.avgRating}/5</p>
            <p className="text-xs text-gray-500 mt-1">Based on guest feedback</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
