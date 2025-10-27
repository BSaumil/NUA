import React, { useState, useEffect } from 'react';
import { DollarSign, ShoppingBag, Users, TrendingUp, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { useTheme } from '../contexts/ThemeContext';
import { transactionsAPI, customersAPI, accountingAPI } from '../services/api';

const Dashboard = () => {
  const { theme } = useTheme();
  const [transactions, setTransactions] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [summary, setSummary] = useState({
    totalRevenue: 0,
    gstCollected: 0,
    transactions: 0,
    avgTransaction: 0
  });

  useEffect(() => {
    fetchData();
  }, []);
  
  const fetchData = async () => {
    try {
      const [txnRes, custRes, summaryRes] = await Promise.all([
        transactionsAPI.getAll(),
        customersAPI.getAll(),
        accountingAPI.getSummary()
      ]);
      setTransactions(txnRes.data);
      setCustomers(custRes.data);
      setSummary(summaryRes.data);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    }
  };

  const stats = [
    {
      title: 'Total Revenue',
      value: `$${summary.totalRevenue.toFixed(2)}`,
      change: '+12.5%',
      trend: 'up',
      icon: DollarSign,
      color: theme.primary
    },
    {
      title: 'Transactions Today',
      value: summary.transactions.toString(),
      change: '+8.2%',
      trend: 'up',
      icon: ShoppingBag,
      color: theme.secondary
    },
    {
      title: 'Active Customers',
      value: customers.length.toString(),
      change: '+5.4%',
      trend: 'up',
      icon: Users,
      color: theme.accent
    },
    {
      title: 'Avg. Transaction',
      value: `$${summary.avgTransaction.toFixed(2)}`,
      change: '-2.1%',
      trend: 'down',
      icon: TrendingUp,
      color: '#10b981'
    }
  ];

  const recentTransactions = transactions.slice(0, 5);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold" style={{ color: theme.text }}>Dashboard</h1>
        <p className="text-gray-500 mt-1">Welcome back! Here's what's happening today.</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => {
          const Icon = stat.icon;
          const TrendIcon = stat.trend === 'up' ? ArrowUpRight : ArrowDownRight;

          return (
            <Card key={stat.title} className="hover:shadow-lg transition-shadow duration-300">
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm text-gray-500 font-medium">{stat.title}</p>
                    <h3 className="text-3xl font-bold mt-2" style={{ color: theme.text }}>
                      {stat.value}
                    </h3>
                    <div className="flex items-center gap-1 mt-2">
                      <TrendIcon
                        size={16}
                        className={stat.trend === 'up' ? 'text-green-500' : 'text-red-500'}
                      />
                      <span
                        className={`text-sm font-medium ${
                          stat.trend === 'up' ? 'text-green-500' : 'text-red-500'
                        }`}
                      >
                        {stat.change}
                      </span>
                      <span className="text-sm text-gray-500">vs last week</span>
                    </div>
                  </div>
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center"
                    style={{ backgroundColor: `${stat.color}20` }}
                  >
                    <Icon size={24} style={{ color: stat.color }} />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Transactions */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Transactions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentTransactions.map((txn) => (
                <div key={txn.id} className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 transition-colors">
                  <div className="flex-1">
                    <p className="font-medium" style={{ color: theme.text }}>{txn.id}</p>
                    <p className="text-sm text-gray-500">
                      {new Date(txn.timestamp).toLocaleString()}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-bold" style={{ color: theme.primary }}>${txn.total.toFixed(2)}</p>
                    <p className="text-xs text-gray-500">{txn.paymentMethod}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Top Customers */}
        <Card>
          <CardHeader>
            <CardTitle>Top Customers</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {customers.slice(0, 5).map((customer) => (
                <div key={customer.id} className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 transition-colors">
                  <div className="flex items-center gap-3">
                    <div
                      className="w-10 h-10 rounded-full flex items-center justify-center text-white font-medium"
                      style={{ backgroundColor: theme.primary }}
                    >
                      {customer.name.split(' ').map(n => n[0]).join('')}
                    </div>
                    <div>
                      <p className="font-medium" style={{ color: theme.text }}>{customer.name}</p>
                      <p className="text-sm text-gray-500">{customer.membershipTier}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-bold" style={{ color: theme.primary }}>${customer.totalSpent.toFixed(2)}</p>
                    <p className="text-xs text-gray-500">{customer.visits} visits</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Dashboard;
