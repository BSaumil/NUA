import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Award, Gift, Calendar, Share2, Star, Copy, Facebook, Twitter, MessageCircle
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;
const TIER_COLORS = { Bronze: 'text-amber-700 bg-amber-50', Silver: 'text-gray-600 bg-gray-100', Gold: 'text-yellow-700 bg-yellow-50', Platinum: 'text-purple-700 bg-purple-50' };

export default function MemberPortal() {
  const [searchParams] = useSearchParams();
  const [view, setView] = useState('signup'); // signup | login | dashboard
  const [member, setMember] = useState(null);
  const [token, setToken] = useState('');
  const [form, setForm] = useState({ name: '', email: '', phone: '', password: '' });
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [shareLinks, setShareLinks] = useState(null);
  const ref = searchParams.get('ref');

  const handleSignup = async (e) => {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      const res = await axios.post(`${API}/api/members/signup`, form);
      setMember(res.data.member);
      setToken(res.data.token);
      setView('dashboard');
      toast.success('Welcome to NUA! 50 bonus points + 15% off voucher');
    } catch (err) {
      setError(typeof err.response?.data?.detail === 'string' ? err.response.data.detail : 'Signup failed');
    }
    setLoading(false);
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      const res = await axios.post(`${API}/api/members/login`, loginForm);
      setMember(res.data.member);
      setToken(res.data.token);
      setView('dashboard');
    } catch (err) {
      setError(typeof err.response?.data?.detail === 'string' ? err.response.data.detail : 'Invalid credentials');
    }
    setLoading(false);
  };

  const loadShareLinks = async () => {
    if (!member) return;
    try {
      const res = await axios.get(`${API}/api/members/share-link/${member.id}`);
      setShareLinks(res.data);
    } catch {}
  };

  const copyCode = () => {
    if (member?.referralCode) {
      navigator.clipboard.writeText(member.referralCode);
      toast.success('Referral code copied!');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-emerald-950 text-white" data-testid="member-portal">
      {/* Header */}
      <header className="p-4 text-center border-b border-gray-800">
        <h1 className="text-2xl font-bold tracking-tight">NUA Members</h1>
      </header>

      <div className="max-w-md mx-auto px-4 py-8">
        {/* Signup/Login */}
        {view !== 'dashboard' && (
          <>
            <div className="flex gap-2 mb-6 justify-center">
              <button onClick={() => setView('signup')} className={`px-5 py-2 rounded-full text-sm font-medium ${view === 'signup' ? 'bg-emerald-600 text-white' : 'bg-gray-800 text-gray-400'}`}
                data-testid="signup-tab">Sign Up</button>
              <button onClick={() => setView('login')} className={`px-5 py-2 rounded-full text-sm font-medium ${view === 'login' ? 'bg-emerald-600 text-white' : 'bg-gray-800 text-gray-400'}`}
                data-testid="login-tab">Login</button>
            </div>

            {view === 'signup' && (
              <Card className="bg-gray-900/80 border-gray-800">
                <CardContent className="p-6">
                  <div className="text-center mb-4">
                    <Award size={32} className="mx-auto text-emerald-400 mb-2" />
                    <h2 className="text-lg font-bold">Join & Get Rewarded</h2>
                    <p className="text-xs text-gray-400">50 bonus points + 15% off your first meal</p>
                  </div>
                  {error && <p className="text-red-400 text-sm mb-3 text-center">{error}</p>}
                  <form onSubmit={handleSignup} className="space-y-3">
                    <Input placeholder="Full Name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                      className="bg-gray-800 border-gray-700 text-white" required data-testid="member-name" />
                    <Input placeholder="Email" type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })}
                      className="bg-gray-800 border-gray-700 text-white" required data-testid="member-email" />
                    <Input placeholder="Phone" value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })}
                      className="bg-gray-800 border-gray-700 text-white" required data-testid="member-phone" />
                    <Input placeholder="Password" type="password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })}
                      className="bg-gray-800 border-gray-700 text-white" required data-testid="member-password" />
                    {ref && <p className="text-xs text-emerald-400">Referred by: {ref}</p>}
                    <Button type="submit" className="w-full bg-emerald-600 hover:bg-emerald-700" disabled={loading}
                      data-testid="member-signup-btn">{loading ? 'Joining...' : 'Join Now'}</Button>
                  </form>
                </CardContent>
              </Card>
            )}

            {view === 'login' && (
              <Card className="bg-gray-900/80 border-gray-800">
                <CardContent className="p-6">
                  {error && <p className="text-red-400 text-sm mb-3 text-center">{error}</p>}
                  <form onSubmit={handleLogin} className="space-y-3">
                    <Input placeholder="Email" type="email" value={loginForm.email} onChange={e => setLoginForm({ ...loginForm, email: e.target.value })}
                      className="bg-gray-800 border-gray-700 text-white" required data-testid="member-login-email" />
                    <Input placeholder="Password" type="password" value={loginForm.password} onChange={e => setLoginForm({ ...loginForm, password: e.target.value })}
                      className="bg-gray-800 border-gray-700 text-white" required data-testid="member-login-password" />
                    <Button type="submit" className="w-full bg-emerald-600 hover:bg-emerald-700" disabled={loading}
                      data-testid="member-login-btn">{loading ? 'Signing in...' : 'Sign In'}</Button>
                  </form>
                </CardContent>
              </Card>
            )}
          </>
        )}

        {/* Dashboard */}
        {view === 'dashboard' && member && (
          <div className="space-y-4" data-testid="member-dashboard">
            {/* Profile Card */}
            <Card className="bg-gradient-to-r from-emerald-900/50 to-gray-900 border-emerald-800">
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h2 className="text-xl font-bold">{member.name}</h2>
                    <p className="text-sm text-gray-400">{member.email}</p>
                  </div>
                  <Badge className={TIER_COLORS[member.tier] || TIER_COLORS.Bronze}>{member.tier}</Badge>
                </div>
                <div className="flex gap-6 mt-4">
                  <div><p className="text-2xl font-bold text-emerald-400">{member.points}</p><p className="text-xs text-gray-400">Points</p></div>
                  <div><p className="text-2xl font-bold">{member.visits}</p><p className="text-xs text-gray-400">Visits</p></div>
                  <div><p className="text-2xl font-bold">${member.totalSpent.toFixed(0)}</p><p className="text-xs text-gray-400">Total Spent</p></div>
                </div>
              </CardContent>
            </Card>

            {/* Vouchers */}
            <Card className="bg-gray-900/80 border-gray-800">
              <CardContent className="p-5">
                <h3 className="font-semibold mb-3 flex items-center gap-2"><Gift size={18} className="text-emerald-400" /> Your Vouchers</h3>
                {member.vouchers?.length > 0 ? (
                  <div className="space-y-2">
                    {member.vouchers.map(v => (
                      <div key={v.id} className="flex items-center justify-between p-3 bg-gray-800 rounded-lg">
                        <div>
                          <p className="font-medium text-sm">{v.name}</p>
                          <p className="text-xs text-gray-400">Code: {v.code}</p>
                        </div>
                        <Badge className="bg-emerald-600 text-white">
                          {v.type === 'percentage' ? `${v.value}% OFF` : `$${v.value} OFF`}
                        </Badge>
                      </div>
                    ))}
                  </div>
                ) : <p className="text-sm text-gray-500">No vouchers yet</p>}
              </CardContent>
            </Card>

            {/* Referral / Share */}
            <Card className="bg-gray-900/80 border-gray-800">
              <CardContent className="p-5">
                <h3 className="font-semibold mb-3 flex items-center gap-2"><Share2 size={18} className="text-emerald-400" /> Refer & Earn</h3>
                <div className="flex items-center gap-2 bg-gray-800 p-3 rounded-lg mb-3">
                  <span className="font-mono text-sm flex-1">{member.referralCode}</span>
                  <button onClick={copyCode} className="text-gray-400 hover:text-white"><Copy size={16} /></button>
                </div>
                <p className="text-xs text-gray-400 mb-3">Share your code — both you and your friend get bonus points!</p>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" className="flex-1 text-xs border-gray-700"
                    onClick={() => { loadShareLinks(); window.open(`https://wa.me/?text=Join me at NUA! Use code ${member.referralCode}`, '_blank'); }}>
                    <MessageCircle size={14} className="mr-1" /> WhatsApp
                  </Button>
                  <Button size="sm" variant="outline" className="flex-1 text-xs border-gray-700"
                    onClick={() => window.open(`https://www.facebook.com/sharer/sharer.php?u=nua.com/join?ref=${member.referralCode}`, '_blank')}>
                    <Facebook size={14} className="mr-1" /> Facebook
                  </Button>
                  <Button size="sm" variant="outline" className="flex-1 text-xs border-gray-700"
                    onClick={() => window.open(`https://twitter.com/intent/tweet?text=Join me at NUA! Code: ${member.referralCode}`, '_blank')}>
                    <Twitter size={14} className="mr-1" /> Twitter
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Button variant="outline" className="w-full border-gray-700 text-gray-400"
              onClick={() => { setMember(null); setView('signup'); }}>
              Sign Out
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
