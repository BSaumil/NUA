import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { staffMgmtAPI } from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Lock, Mail, AlertCircle, Hash } from 'lucide-react';

export default function Login() {
  const { login } = useAuth();
  const [mode, setMode] = useState('email'); // email | pin
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [pin, setPin] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleEmailLogin = async (e) => {
    e.preventDefault();
    setError(''); setLoading(true);
    try { await login(email, password); } catch (err) {
      setError(err.response?.data?.detail || 'Invalid credentials');
    }
    setLoading(false);
  };

  const handlePinLogin = async (e) => {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      const res = await staffMgmtAPI.pinLogin(pin);
      localStorage.setItem('nuva_token', res.data.token);
      window.location.reload();
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid PIN');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-950 to-black" data-testid="login-page">
      <Card className="w-full max-w-sm border-gray-800 bg-gray-900/80 backdrop-blur">
        <CardContent className="p-8">
          <div className="text-center mb-6">
            <h1 className="text-3xl font-bold text-white tracking-tight">NUA</h1>
            <p className="text-gray-400 text-sm mt-1">Staff Portal</p>
          </div>

          {/* Mode Toggle */}
          <div className="flex gap-1 mb-6 bg-gray-800 rounded-lg p-1">
            <button onClick={() => setMode('email')} data-testid="mode-email"
              className={`flex-1 py-2 text-sm rounded-md font-medium transition-colors ${mode === 'email' ? 'bg-emerald-600 text-white' : 'text-gray-400 hover:text-white'}`}>
              <Mail size={14} className="inline mr-1" /> Email
            </button>
            <button onClick={() => setMode('pin')} data-testid="mode-pin"
              className={`flex-1 py-2 text-sm rounded-md font-medium transition-colors ${mode === 'pin' ? 'bg-emerald-600 text-white' : 'text-gray-400 hover:text-white'}`}>
              <Hash size={14} className="inline mr-1" /> PIN Code
            </button>
          </div>

          {error && (
            <div className="flex items-center gap-2 text-red-400 text-sm bg-red-950/50 p-3 rounded-lg mb-4" data-testid="login-error">
              <AlertCircle size={16} /> {error}
            </div>
          )}

          {mode === 'email' ? (
            <form onSubmit={handleEmailLogin} className="space-y-4">
              <div className="relative">
                <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                <Input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)}
                  className="pl-10 bg-gray-800 border-gray-700 text-white" required data-testid="login-email" />
              </div>
              <div className="relative">
                <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                <Input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)}
                  className="pl-10 bg-gray-800 border-gray-700 text-white" required data-testid="login-password" />
              </div>
              <Button type="submit" className="w-full h-11 bg-emerald-600 hover:bg-emerald-700 text-white font-medium" disabled={loading} data-testid="login-submit">
                {loading ? 'Signing in...' : 'Sign In'}
              </Button>
            </form>
          ) : (
            <form onSubmit={handlePinLogin} className="space-y-4">
              <div className="text-center mb-2">
                <p className="text-gray-400 text-sm">Enter your staff PIN code</p>
              </div>
              <div className="flex justify-center">
                <Input type="password" inputMode="numeric" maxLength={4} placeholder="----" value={pin}
                  onChange={e => { const v = e.target.value.replace(/\D/g, '').slice(0, 4); setPin(v); }}
                  className="text-center text-3xl tracking-[0.5em] font-mono w-48 h-16 bg-gray-800 border-gray-700 text-white"
                  data-testid="login-pin" />
              </div>
              <Button type="submit" className="w-full h-11 bg-emerald-600 hover:bg-emerald-700 text-white font-medium" disabled={loading || pin.length < 2} data-testid="pin-submit">
                {loading ? 'Signing in...' : 'Sign In with PIN'}
              </Button>
            </form>
          )}

          <div className="mt-6 pt-4 border-t border-gray-800">
            <p className="text-xs text-gray-500 text-center">
              {mode === 'email' ? 'Owner: owner@nuva.com' : 'Ask your manager for your PIN code'}
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
