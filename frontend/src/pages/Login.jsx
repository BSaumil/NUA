import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Lock, Mail, AlertCircle } from 'lucide-react';

export default function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Invalid credentials');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-950 to-black" data-testid="login-page">
      <Card className="w-full max-w-sm border-gray-800 bg-gray-900/80 backdrop-blur">
        <CardContent className="p-8">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-white tracking-tight">Ananta</h1>
            <p className="text-gray-400 text-sm mt-1">Staff Portal</p>
          </div>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="flex items-center gap-2 text-red-400 text-sm bg-red-950/50 p-3 rounded-lg" data-testid="login-error">
                <AlertCircle size={16} /> {error}
              </div>
            )}
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
            <Button type="submit" className="w-full h-11 bg-emerald-600 hover:bg-emerald-700 text-white font-medium"
              disabled={loading} data-testid="login-submit">
              {loading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>
          <div className="mt-6 pt-4 border-t border-gray-800">
            <p className="text-xs text-gray-500 text-center">Demo: owner@ananta.com / AnantaOwner2026!</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
