import React, { useState } from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs';
import { BookOpenCheck, FileSpreadsheet, Landmark, ReceiptText, ArrowLeftRight, TrendingUp, ChevronRight, PiggyBank, Target } from 'lucide-react';
import Overview from './finance/Overview';
import Reports from './finance/Reports';
import AccountsPayable from './finance/AccountsPayable';
import AccountsReceivable from './finance/AccountsReceivable';
import Deposits from './finance/Deposits';
import Budgets from './finance/Budgets';
import BankRec from './finance/BankRec';
import Journals from './finance/Journals';
import ChartOfAccounts from './finance/ChartOfAccounts';

const FinanceLedger = () => {
  const [tab, setTab] = useState('overview');
  return (
    <div className="space-y-6" data-testid="finance-ledger-page">
      <div>
        <h1 className="text-3xl font-bold">Finance &amp; Accounting</h1>
        <p className="text-slate-500 mt-1">Double-entry ledger · P&amp;L · Balance Sheet · AP/AR · Bank Rec</p>
      </div>
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="flex-wrap">
          <TabsTrigger value="overview" data-testid="fin-tab-overview"><TrendingUp size={14} className="mr-1" /> Overview</TabsTrigger>
          <TabsTrigger value="reports" data-testid="fin-tab-reports"><FileSpreadsheet size={14} className="mr-1" /> Reports</TabsTrigger>
          <TabsTrigger value="ap" data-testid="fin-tab-ap"><ArrowLeftRight size={14} className="mr-1" /> Bills (AP)</TabsTrigger>
          <TabsTrigger value="ar" data-testid="fin-tab-ar"><ReceiptText size={14} className="mr-1" /> Invoices (AR)</TabsTrigger>
          <TabsTrigger value="deposits" data-testid="fin-tab-deposits"><PiggyBank size={14} className="mr-1" /> Deposits</TabsTrigger>
          <TabsTrigger value="budgets" data-testid="fin-tab-budgets"><Target size={14} className="mr-1" /> Budgets</TabsTrigger>
          <TabsTrigger value="bank" data-testid="fin-tab-bank"><Landmark size={14} className="mr-1" /> Bank Rec</TabsTrigger>
          <TabsTrigger value="journals" data-testid="fin-tab-journals"><BookOpenCheck size={14} className="mr-1" /> Journals</TabsTrigger>
          <TabsTrigger value="coa" data-testid="fin-tab-coa"><ChevronRight size={14} className="mr-1" /> Chart of Accounts</TabsTrigger>
        </TabsList>
        <TabsContent value="overview"><Overview /></TabsContent>
        <TabsContent value="reports"><Reports /></TabsContent>
        <TabsContent value="ap"><AccountsPayable /></TabsContent>
        <TabsContent value="ar"><AccountsReceivable /></TabsContent>
        <TabsContent value="deposits"><Deposits /></TabsContent>
        <TabsContent value="budgets"><Budgets /></TabsContent>
        <TabsContent value="bank"><BankRec /></TabsContent>
        <TabsContent value="journals"><Journals /></TabsContent>
        <TabsContent value="coa"><ChartOfAccounts /></TabsContent>
      </Tabs>
    </div>
  );
};

export default FinanceLedger;
