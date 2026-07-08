import React, { useState, useEffect } from 'react';
import { FileText, Calendar, Send, CheckCircle, AlertCircle, Download, Upload } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { useTheme } from '../contexts/ThemeContext';
import { basGstAPI } from '../services/api';
import { useToast } from '../hooks/use-toast';
import BasWorksheetPanel from '../components/bas/BasWorksheetPanel';

const BASGST = () => {
  const { theme } = useTheme();
  const { toast } = useToast();
  const [showApiConfig, setShowApiConfig] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [basReports, setBasReports] = useState([]);

  useEffect(() => {
    fetchReports();
  }, []);
  
  const fetchReports = async () => {
    try {
      const res = await basGstAPI.getReports();
      setBasReports(res.data);
    } catch (error) {
      console.error('Error fetching BAS reports:', error);
    }
  };

  const handleMockSubmit = async (report) => {
    try {
      await basGstAPI.submit(report.id, false);
      toast({
        title: "BAS Report Submitted (Mock)",
        description: `${report.quarter} report has been submitted successfully to ATO (simulated)`,
      });
      fetchReports();
    } catch (error) {
      console.error('Error submitting report:', error);
    }
  };

  const handleApiSubmit = async (report) => {
    if (!apiKey) {
      toast({
        title: "API Key Required",
        description: "Please configure your ATO API credentials first",
        variant: "destructive"
      });
      return;
    }
    try {
      await basGstAPI.submit(report.id, true);
      toast({
        title: "BAS Report Submitted",
        description: `${report.quarter} report has been submitted to ATO via API`,
      });
      fetchReports();
    } catch (error) {
      console.error('Error submitting report:', error);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold" style={{ color: theme.text }}>BAS & GST Filing</h1>
          <p className="text-gray-500 mt-1">Automated quarterly tax reporting and submissions</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={() => setShowApiConfig(!showApiConfig)}>
            <Upload className="mr-2" size={18} />
            {showApiConfig ? 'Hide' : 'Configure'} API
          </Button>
          <Button style={{ backgroundColor: theme.primary }}>
            <FileText className="mr-2" size={18} />
            Generate New Report
          </Button>
        </div>
      </div>

      {/* ATO Worksheet — G1-G20 / W1-W5 / T1 for the current quarter */}
      <BasWorksheetPanel theme={theme} />


      {/* API Configuration Panel */}
      {showApiConfig && (
        <Card className="border-2" style={{ borderColor: theme.primary }}>
          <CardHeader>
            <CardTitle>ATO API Configuration</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-2 block">ATO API Key</label>
                <Input
                  type="password"
                  placeholder="Enter your ATO API key"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Get your API key from the ATO Business Portal. This enables real BAS submissions.
                </p>
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">ABN</label>
                <Input placeholder="12 345 678 901" />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Entity Name</label>
                <Input placeholder="Your Business Name" />
              </div>
              <Button style={{ backgroundColor: theme.primary }}>
                Save Configuration
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">Current Quarter GST</p>
              <FileText size={20} style={{ color: theme.primary }} />
            </div>
            <p className="text-3xl font-bold" style={{ color: theme.text }}>
              ${basReports.find(r => r.status === 'draft')?.netGst.toFixed(2) || '0.00'}
            </p>
            <p className="text-xs text-gray-500 mt-1">Due: 28 Apr 2025</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">YTD GST Collected</p>
              <CheckCircle size={20} style={{ color: '#10b981' }} />
            </div>
            <p className="text-3xl font-bold" style={{ color: theme.text }}>
              ${basReports.reduce((sum, r) => sum + r.gstCollected, 0).toFixed(2)}
            </p>
            <p className="text-xs text-green-500 mt-1">On track</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">Reports Filed</p>
              <Calendar size={20} style={{ color: theme.accent }} />
            </div>
            <p className="text-3xl font-bold" style={{ color: theme.text }}>
              {basReports.filter(r => r.status === 'submitted').length}
            </p>
            <p className="text-xs text-gray-500 mt-1">This year</p>
          </CardContent>
        </Card>
      </div>

      {/* BAS Reports */}
      <div className="space-y-4">
        <h2 className="text-2xl font-bold" style={{ color: theme.text }}>BAS Reports</h2>

        {basReports.map(report => (
          <Card key={report.id}>
            <CardContent className="p-6">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-4">
                    <h3 className="text-xl font-bold" style={{ color: theme.text }}>{report.quarter}</h3>
                    <span
                      className="px-3 py-1 rounded-full text-xs font-medium flex items-center gap-1"
                      style={{
                        backgroundColor: report.status === 'submitted' ? '#dcfce7' : '#fef3c7',
                        color: report.status === 'submitted' ? '#15803d' : '#92400e'
                      }}
                    >
                      {report.status === 'submitted' ? (
                        <CheckCircle size={12} />
                      ) : (
                        <AlertCircle size={12} />
                      )}
                      {report.status.toUpperCase()}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-5 gap-6">
                    <div>
                      <p className="text-sm text-gray-500 mb-1">Period</p>
                      <p className="font-medium">{report.period}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500 mb-1">Total Sales</p>
                      <p className="font-bold" style={{ color: theme.primary }}>
                        ${report.totalSales.toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500 mb-1">GST Collected</p>
                      <p className="font-bold text-green-600">
                        ${report.gstCollected.toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500 mb-1">GST Paid</p>
                      <p className="font-bold text-red-600">
                        ${report.gstPaid.toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500 mb-1">Net GST</p>
                      <p className="font-bold text-xl" style={{ color: theme.accent }}>
                        ${report.netGst.toLocaleString()}
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 pt-4 border-t flex items-center justify-between">
                    <div className="text-sm">
                      <span className="text-gray-500">Due Date: </span>
                      <span className="font-medium">{new Date(report.dueDate).toLocaleDateString()}</span>
                      {report.submittedDate && (
                        <>
                          <span className="text-gray-500 ml-4">Submitted: </span>
                          <span className="font-medium">{new Date(report.submittedDate).toLocaleDateString()}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex flex-col gap-2 ml-6">
                  <Button variant="outline" size="sm">
                    <Download size={14} className="mr-1" />
                    Download
                  </Button>
                  {report.status === 'draft' && (
                    <>
                      <Button
                        size="sm"
                        style={{ backgroundColor: theme.primary }}
                        onClick={() => handleMockSubmit(report)}
                      >
                        <Send size={14} className="mr-1" />
                        Submit (Mock)
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleApiSubmit(report)}
                        style={{ borderColor: theme.secondary, color: theme.secondary }}
                      >
                        <Send size={14} className="mr-1" />
                        Submit via API
                      </Button>
                    </>
                  )}
                </div>
              </div>

              {/* Detailed Breakdown */}
              <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                <h4 className="font-semibold mb-3" style={{ color: theme.text }}>GST Calculation Breakdown</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <p className="text-gray-500">G1 - Total Sales</p>
                    <p className="font-medium">${report.totalSales.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">1A - GST on Sales</p>
                    <p className="font-medium text-green-600">${report.gstCollected.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">1B - GST on Purchases</p>
                    <p className="font-medium text-red-600">${report.gstPaid.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Net Amount</p>
                    <p className="font-bold" style={{ color: theme.primary }}>
                      ${report.netGst.toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default BASGST;
