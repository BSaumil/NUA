import React, { useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { authAPI } from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Lock, AlertCircle, CheckCircle2 } from 'lucide-react';
import Logo from '../components/brand/Logo';

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (password.length < 8) { setError('Password must be at least 8 characters'); return; }
    if (password !== confirm) { setError('Passwords do not match'); return; }
    setLoading(true);
    try {
      await authAPI.resetPassword(token, password);
      setDone(true);
      setTimeout(() => navigate('/', { replace: true }), 2500);
    } catch (err) {
      setError(err.response?.data?.detail || 'This reset link is invalid or has expired');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-950 to-black" data-testid="reset-password-page">
      <Card className="w-full max-w-sm border-gray-800 bg-gray-900/80 backdrop-blur">
        <CardContent className="p-8">
          <div className="flex flex-col items-center mb-6">
            <Logo variant="marketing" background="dark" size={34} />
          </div>

          {!token ? (
            <div className="text-center" data-testid="reset-no-token">
              <AlertCircle size={28} className="mx-auto mb-3 text-red-400" />
              <p className="text-white font-medium mb-1">Invalid reset link</p>
              <p className="text-gray-400 text-sm mb-5">This link is missing its token. Request a new one from the sign-in page.</p>
              <Link to="/" className="text-sm hover:opacity-90" style={{ color: '#f58c14' }} data-testid="reset-back-to-login">
                Back to sign in
              </Link>
            </div>
          ) : done ? (
            <div className="text-center" data-testid="reset-success">
              <CheckCircle2 size={28} className="mx-auto mb-3 text-emerald-400" />
              <p className="text-white font-medium mb-1">Password updated</p>
              <p className="text-gray-400 text-sm">Taking you to sign in...</p>
            </div>
          ) : (
            <>
              <div className="flex flex-col items-center mb-5">
                <Lock size={28} style={{ color: '#f58c14' }} />
                <p className="text-white font-medium mt-2">Set a new password</p>
                <p className="text-gray-400 text-sm text-center mt-1">Choose a new password for your account.</p>
              </div>
              {error && (
                <div className="flex items-center gap-2 text-red-400 text-sm bg-red-950/50 p-3 rounded-lg mb-4" data-testid="reset-error">
                  <AlertCircle size={16} /> {error}
                </div>
              )}
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="relative">
                  <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                  <Input type="password" placeholder="New password" value={password} onChange={e => setPassword(e.target.value)}
                    className="pl-10 bg-gray-800 border-gray-700 text-white" required data-testid="reset-password-input" />
                </div>
                <div className="relative">
                  <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                  <Input type="password" placeholder="Confirm password" value={confirm} onChange={e => setConfirm(e.target.value)}
                    className="pl-10 bg-gray-800 border-gray-700 text-white" required data-testid="reset-confirm-input" />
                </div>
                <Button type="submit" className="w-full h-11 text-white font-medium hover:opacity-90"
                  style={{ backgroundColor: '#f58c14' }} disabled={loading} data-testid="reset-submit">
                  {loading ? 'Saving...' : 'Set new password'}
                </Button>
              </form>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
