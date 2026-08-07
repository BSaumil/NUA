import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { staffMgmtAPI } from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Lock, Mail, AlertCircle, Hash, ShieldCheck } from 'lucide-react';
import Logo from '../components/brand/Logo';

export default function Login() {
  const { login, completeTwoFactor } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState('email'); // email | pin
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [pin, setPin] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  // Set once the password step passes but a code is still owed.
  const [challenge, setChallenge] = useState(null);
  const [code, setCode] = useState('');
  const [trustDevice, setTrustDevice] = useState(true);

  const handleEmailLogin = async (e) => {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      const res = await login(email, password);
      if (res.twoFactor) {
        setChallenge(res.twoFactor);
      } else {
        navigate('/', { replace: true }); // role-based landing (Today / POS / Kitchen)
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid credentials');
    }
    setLoading(false);
  };

  const handleCodeSubmit = async (e) => {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      const res = await completeTwoFactor(challenge.challengeToken, code, trustDevice);
      if (res.verifiedBy === 'recovery') {
        // Say it out loud — a recovery code is a one-shot, and someone who
        // just burned one needs to know how many are left before they're
        // locked out mid-service.
        window.sessionStorage.setItem(
          'nua_recovery_notice',
          `You signed in with a recovery code. ${res.recoveryCodesRemaining} left.`);
      }
      navigate('/', { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || 'Incorrect code');
      setCode('');
    }
    setLoading(false);
  };

  const handlePinLogin = async (e) => {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      const res = await staffMgmtAPI.pinLogin(pin);
      localStorage.setItem('nua_token', res.data.token);
      window.location.assign('/'); // role-based landing (Today / POS / Kitchen)
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid PIN');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-950 to-black" data-testid="login-page">
      <Card className="w-full max-w-sm border-gray-800 bg-gray-900/80 backdrop-blur">
        <CardContent className="p-8">
          {/* Login is a marketing-facing surface, so it gets the full
              wordmark lockup (BRAND-SPEC §3) — on this dark background the
              wordmark is orange (BRAND-SPEC §2), never a gradient. */}
          <div className="flex flex-col items-center mb-6">
            <Logo variant="marketing" background="dark" size={34} />
          </div>

          {/* Second factor — replaces the whole form rather than sitting
              alongside it, so there is no way to be half signed in. */}
          {challenge ? (
            <div data-testid="twofactor-step">
              <div className="flex flex-col items-center mb-5">
                <ShieldCheck size={28} style={{ color: '#f58c14' }} />
                <p className="text-white font-medium mt-2">Two-factor check</p>
                <p className="text-gray-400 text-sm text-center mt-1">
                  {challenge.enrolmentRequired
                    ? 'This venue requires a second factor for your role. Open Settings → Security after signing in on a trusted device.'
                    : 'Enter the 6-digit code from your authenticator app'}
                </p>
              </div>
              {error && (
                <div className="flex items-center gap-2 text-red-400 text-sm bg-red-950/50 p-3 rounded-lg mb-4" data-testid="twofactor-error">
                  <AlertCircle size={16} /> {error}
                </div>
              )}
              {!challenge.enrolmentRequired && (
                <form onSubmit={handleCodeSubmit} className="space-y-4">
                  <Input
                    autoFocus inputMode="numeric" autoComplete="one-time-code"
                    placeholder="000000" value={code}
                    onChange={e => setCode(e.target.value.replace(/[^0-9A-Za-z-]/g, '').slice(0, 11))}
                    className="text-center text-2xl tracking-[0.4em] font-mono h-14 bg-gray-800 border-gray-700 text-white"
                    data-testid="twofactor-code" />
                  <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
                    <input type="checkbox" checked={trustDevice} className="accent-orange-500 w-4 h-4"
                      onChange={e => setTrustDevice(e.target.checked)} data-testid="twofactor-trust" />
                    Remember this terminal for 30 days
                  </label>
                  <Button type="submit" className="w-full h-11 text-white font-medium hover:opacity-90"
                    style={{ backgroundColor: '#f58c14' }} disabled={loading || code.length < 6}
                    data-testid="twofactor-submit">
                    {loading ? 'Checking...' : 'Verify'}
                  </Button>
                  {challenge.recoveryAvailable && (
                    <p className="text-xs text-gray-500 text-center">
                      Lost your phone? Enter one of your recovery codes instead.
                    </p>
                  )}
                </form>
              )}
              <button onClick={() => { setChallenge(null); setCode(''); setError(''); }}
                className="mt-5 w-full text-sm text-gray-500 hover:text-gray-300"
                data-testid="twofactor-back">
                Use a different account
              </button>
            </div>
          ) : (
          <>
          {/* Mode Toggle */}
          <div className="flex gap-1 mb-6 bg-gray-800 rounded-lg p-1">
            <button onClick={() => setMode('email')} data-testid="mode-email"
              className={`flex-1 py-2 text-sm rounded-md font-medium transition-colors ${mode === 'email' ? 'text-white' : 'text-gray-400 hover:text-white'}`}
              style={mode === 'email' ? { backgroundColor: '#f58c14' } : {}}>
              <Mail size={14} className="inline mr-1" /> Email
            </button>
            <button onClick={() => setMode('pin')} data-testid="mode-pin"
              className={`flex-1 py-2 text-sm rounded-md font-medium transition-colors ${mode === 'pin' ? 'text-white' : 'text-gray-400 hover:text-white'}`}
              style={mode === 'pin' ? { backgroundColor: '#f58c14' } : {}}>
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
              <Button type="submit" className="w-full h-11 text-white font-medium hover:opacity-90" style={{ backgroundColor: '#f58c14' }} disabled={loading} data-testid="login-submit">
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
              <Button type="submit" className="w-full h-11 text-white font-medium hover:opacity-90" style={{ backgroundColor: '#f58c14' }} disabled={loading || pin.length < 2} data-testid="pin-submit">
                {loading ? 'Signing in...' : 'Sign In with PIN'}
              </Button>
            </form>
          )}

          <div className="mt-6 pt-4 border-t border-gray-800">
            <p className="text-xs text-gray-500 text-center">
              {mode === 'email' ? 'Owner: owner@nua.com' : 'Ask your manager for your PIN code'}
            </p>
          </div>
          </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
