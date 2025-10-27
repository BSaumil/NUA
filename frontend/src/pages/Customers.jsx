import React, { useState, useEffect } from 'react';
import { Search, Plus, Mail, Phone, Award, TrendingUp } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { useTheme } from '../contexts/ThemeContext';
import { customersAPI } from '../services/api';

const membershipColors = {
  Platinum: '#e5e7eb',
  Gold: '#fbbf24',
  Silver: '#9ca3af',
  Bronze: '#cd7f32'
};

const Customers = () => {
  const { theme } = useTheme();
  const [searchTerm, setSearchTerm] = useState('');
  const [customers, setCustomers] = useState([]);

  useEffect(() => {
    fetchCustomers();
  }, []);
  
  const fetchCustomers = async () => {
    try {
      const res = await customersAPI.getAll();
      setCustomers(res.data);
    } catch (error) {
      console.error('Error fetching customers:', error);
    }
  };

  const filteredCustomers = customers.filter(c =>
    c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold" style={{ color: theme.text }}>Customer Directory</h1>
          <p className="text-gray-500 mt-1">Manage customers and membership programs</p>
        </div>
        <Button style={{ backgroundColor: theme.primary }}>
          <Plus className="mr-2" size={18} />
          Add Customer
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {[
          { label: 'Total Customers', value: customers.length.toString(), color: theme.primary },
          { label: 'Platinum Members', value: customers.filter(c => c.membershipTier === 'Platinum').length.toString(), color: '#e5e7eb' },
          { label: 'Gold Members', value: customers.filter(c => c.membershipTier === 'Gold').length.toString(), color: '#fbbf24' },
          { label: 'New This Month', value: '67', color: theme.accent }
        ].map((stat, idx) => (
          <Card key={idx}>
            <CardContent className="p-6">
              <p className="text-sm text-gray-500 mb-1">{stat.label}</p>
              <p className="text-3xl font-bold" style={{ color: stat.color }}>{stat.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
        <Input
          placeholder="Search customers by name or email..."
          className="pl-10"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      {/* Customer Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredCustomers.map(customer => (
          <Card key={customer.id} className="hover:shadow-lg transition-shadow duration-300">
            <CardContent className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div
                    className="w-14 h-14 rounded-full flex items-center justify-center text-white font-bold text-lg"
                    style={{ backgroundColor: theme.primary }}
                  >
                    {customer.name.split(' ').map(n => n[0]).join('')}
                  </div>
                  <div>
                    <h3 className="font-bold text-lg" style={{ color: theme.text }}>{customer.name}</h3>
                    <div className="flex items-center gap-1 mt-1">
                      <Award size={14} style={{ color: membershipColors[customer.membershipTier] }} />
                      <span
                        className="text-xs font-medium px-2 py-1 rounded"
                        style={{
                          backgroundColor: `${membershipColors[customer.membershipTier]}30`,
                          color: theme.text
                        }}
                      >
                        {customer.membershipTier}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <Mail size={14} />
                  <span>{customer.email}</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <Phone size={14} />
                  <span>{customer.phone}</span>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t">
                <div>
                  <p className="text-xs text-gray-500">Total Spent</p>
                  <p className="font-bold" style={{ color: theme.primary }}>${customer.totalSpent}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Visits</p>
                  <p className="font-bold">{customer.visits}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Points</p>
                  <p className="font-bold" style={{ color: theme.accent }}>{customer.points}</p>
                </div>
              </div>

              <div className="mt-4">
                <p className="text-xs text-gray-500">Member Since</p>
                <p className="text-sm font-medium">{new Date(customer.joinDate).toLocaleDateString()}</p>
              </div>

              <Button variant="outline" className="w-full mt-4">
                View Details
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default Customers;
