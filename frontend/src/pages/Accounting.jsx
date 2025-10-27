import React, { useState } from 'react';
import { Calendar, FileText, Download, Filter, TrendingUp, DollarSign } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { useTheme } from '../contexts/ThemeContext';
import { transactions } from '../mockData';

const Accounting = () => {
  const { theme } = useTheme();
  const [dateRange, setDateRange] = useState('today');
  const [reportType, setReportType] = useState('transactions');

  // Calculate summary stats
  const totalRevenue = transactions.reduce((sum, t) => sum + t.total, 0);
  const totalGST = transactions.reduce((sum, t) => sum + t.gst, 0);
  const avgTransaction = totalRevenue / transactions.length;

  // Group transactions by hour for minute-level tracing
  const transactionsByHour = transactions.reduce((acc, txn) => {
    const hour = new Date(txn.timestamp).getHours();
    if (!acc[hour]) acc[hour] = [];
    acc[hour].push(txn);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold" style={{ color: theme.text }}>Accounting & Reports</h1>
          <p className="text-gray-500 mt-1">Comprehensive financial reporting with minute-level tracing</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline">
            <Filter className="mr-2" size={18} />
            Filter
          </Button>
          <Button style={{ backgroundColor: theme.primary }}>
            <Download className="mr-2" size={18} />
            Export
          </Button>
        </div>
      </div>

      {/* Date Range Selector */}
      <div className="flex gap-2">
        {['today', 'week', 'month', 'quarter', 'year'].map(range => (
          <Button
            key={range}
            variant={dateRange === range ? 'default' : 'outline'}
            onClick={() => setDateRange(range)}
            style={{
              backgroundColor: dateRange === range ? theme.primary : 'transparent',
              color: dateRange === range ? 'white' : theme.text
            }}
          >
            {range.charAt(0).toUpperCase() + range.slice(1)}
          </Button>
        ))}
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">Total Revenue</p>
              <DollarSign size={20} style={{ color: theme.primary }} />
            </div>
            <p className="text-3xl font-bold" style={{ color: theme.text }}>${totalRevenue.toFixed(2)}</p>
            <p className="text-xs text-green-500 mt-1 flex items-center gap-1">
              <TrendingUp size={12} />
              +12.5% vs last period
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">GST Collected</p>
              <FileText size={20} style={{ color: theme.secondary }} />
            </div>
            <p className="text-3xl font-bold" style={{ color: theme.text }}>${totalGST.toFixed(2)}</p>
            <p className="text-xs text-gray-500 mt-1">10% of sales</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">Transactions</p>
              <FileText size={20} style={{ color: theme.accent }} />
            </div>
            <p className="text-3xl font-bold" style={{ color: theme.text }}>{transactions.length}</p>
            <p className="text-xs text-gray-500 mt-1">Completed orders</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">Avg Transaction</p>
              <TrendingUp size={20} style={{ color: '#10b981' }} />
            </div>
            <p className="text-3xl font-bold" style={{ color: theme.text }}>${avgTransaction.toFixed(2)}</p>
            <p className="text-xs text-gray-500 mt-1">Per order</p>
          </CardContent>
        </Card>
      </div>

      {/* Report Type Tabs */}
      <div className="flex gap-2">
        {['transactions', 'hourly', 'p&l', 'expenses'].map(type => (
          <Button
            key={type}
            variant={reportType === type ? 'default' : 'outline'}
            onClick={() => setReportType(type)}
            style={{
              backgroundColor: reportType === type ? theme.primary : 'transparent',
              color: reportType === type ? 'white' : theme.text
            }}
          >
            {type.toUpperCase()}
          </Button>
        ))}
      </div>

      {/* Detailed Transactions */}
      {reportType === 'transactions' && (
        <Card>
          <CardHeader>
            <CardTitle>Transaction Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-3 text-sm font-medium text-gray-500">Transaction ID</th>
                    <th className="text-left p-3 text-sm font-medium text-gray-500">Timestamp</th>
                    <th className="text-left p-3 text-sm font-medium text-gray-500">Location</th>
                    <th className="text-left p-3 text-sm font-medium text-gray-500">Cashier</th>
                    <th className="text-left p-3 text-sm font-medium text-gray-500">Payment</th>
                    <th className="text-right p-3 text-sm font-medium text-gray-500">GST</th>
                    <th className="text-right p-3 text-sm font-medium text-gray-500">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map(txn => (
                    <tr key={txn.id} className="border-b hover:bg-gray-50 transition-colors">
                      <td className="p-3">
                        <span className="font-mono text-sm font-medium" style={{ color: theme.primary }}>
                          {txn.id}
                        </span>
                      </td>
                      <td className="p-3 text-sm">
                        {new Date(txn.timestamp).toLocaleString('en-AU', {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                          second: '2-digit'
                        })}
                      </td>
                      <td className="p-3 text-sm">{txn.location}</td>
                      <td className="p-3 text-sm">{txn.cashier}</td>
                      <td className="p-3">
                        <span className="text-xs bg-gray-100 px-2 py-1 rounded">{txn.paymentMethod}</span>
                      </td>
                      <td className="p-3 text-right text-sm">${txn.gst.toFixed(2)}</td>
                      <td className="p-3 text-right font-bold" style={{ color: theme.primary }}>
                        ${txn.total.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Hourly Breakdown (Minute-Level Tracing) */}
      {reportType === 'hourly' && (
        <Card>
          <CardHeader>
            <CardTitle>Hourly Transaction Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {Object.entries(transactionsByHour).map(([hour, txns]) => (
                <div key={hour} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-bold text-lg" style={{ color: theme.text }}>
                      {hour.toString().padStart(2, '0')}:00 - {hour.toString().padStart(2, '0')}:59
                    </h3>
                    <span className="text-sm text-gray-500">{txns.length} transactions</span>
                  </div>
                  <div className="space-y-2">
                    {txns.map(txn => (
                      <div key={txn.id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                        <div>
                          <span className="font-mono text-xs font-medium" style={{ color: theme.primary }}>
                            {txn.id}
                          </span>
                          <span className="text-xs text-gray-500 ml-3">
                            {new Date(txn.timestamp).toLocaleTimeString('en-AU', {
                              hour: '2-digit',
                              minute: '2-digit',
                              second: '2-digit'
                            })}
                          </span>
                        </div>
                        <span className="font-bold" style={{ color: theme.primary }}>${txn.total.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                  <div className="mt-3 pt-3 border-t flex justify-between">
                    <span className="text-sm font-medium">Hour Total:</span>
                    <span className="font-bold" style={{ color: theme.primary }}>
                      ${txns.reduce((sum, t) => sum + t.total, 0).toFixed(2)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* P&L Report */}
      {reportType === 'p&l' && (
        <Card>
          <CardHeader>
            <CardTitle>Profit & Loss Statement</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="space-y-2">
                <h3 className="font-semibold text-lg" style={{ color: theme.text }}>Revenue</h3>
                <div className="flex justify-between p-2">
                  <span>Total Sales</span>
                  <span className="font-bold" style={{ color: theme.primary }}>${totalRevenue.toFixed(2)}</span>
                </div>
              </div>
              <div className="space-y-2 pt-4 border-t">
                <h3 className="font-semibold text-lg" style={{ color: theme.text }}>Expenses</h3>
                <div className="flex justify-between p-2">
                  <span>Cost of Goods Sold</span>
                  <span className="font-medium text-red-500">$12,450.00</span>
                </div>
                <div className="flex justify-between p-2">
                  <span>Operating Expenses</span>
                  <span className="font-medium text-red-500">$8,200.00</span>
                </div>
                <div className="flex justify-between p-2">
                  <span>Taxes (GST)</span>
                  <span className="font-medium text-red-500">${totalGST.toFixed(2)}</span>
                </div>
              </div>
              <div className="pt-4 border-t">
                <div className="flex justify-between p-2 bg-gray-50 rounded-lg">
                  <span className="font-bold text-lg">Net Profit</span>
                  <span className="font-bold text-xl" style={{ color: theme.primary }}>
                    ${(totalRevenue - 12450 - 8200 - totalGST).toFixed(2)}
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default Accounting;
