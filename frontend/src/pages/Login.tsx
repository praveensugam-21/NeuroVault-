import React, { useState } from 'react';
import { useAuthStore } from '../store/useAuthStore';
import { Brain, AlertCircle, Loader2, Globe, Eye, EyeOff, Lock } from 'lucide-react';
import { getApiUrl } from '../services/api';

export const Login: React.FC = () => {
  const { login, register, error, clearError, loading } = useAuthStore();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [serverUrl, setServerUrl] = useState(() => {
    return localStorage.getItem('custom_api_url') || getApiUrl();
  });

  const handleServerUrlChange = (value: string) => {
    setServerUrl(value);
    if (value.trim()) {
      localStorage.setItem('custom_api_url', value.trim());
    } else {
      localStorage.removeItem('custom_api_url');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    if (!email || !password) return;
    if (isRegister) {
      const success = await register(email, password);
      if (success) {
        await login(email, password);
      }
    } else {
      await login(email, password);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center p-4">
      {/* Background pattern */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-600/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-indigo-600/5 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-sm">
        {/* Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl shadow-2xl shadow-black/40 p-8 space-y-6">

          {/* Brand Header */}
          <div className="flex flex-col items-center text-center space-y-3 select-none">
            <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white">
                IRIS
              </h1>
              <p className="text-xs text-slate-400 mt-0.5 font-medium">
                Intelligent Retrieval and Information System
              </p>
            </div>
            <div className="flex items-center gap-1.5 text-[10px] text-slate-500 bg-slate-800/50 border border-slate-700/50 px-3 py-1 rounded-full">
              <Lock className="w-2.5 h-2.5" />
              <span>End-to-end encrypted · Self-hosted</span>
            </div>
          </div>

          {/* Mode Toggle */}
          <div className="flex bg-slate-800/60 border border-slate-700/50 rounded-lg p-0.5">
            <button
              type="button"
              onClick={() => { setIsRegister(false); clearError(); }}
              className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-all ${
                !isRegister
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => { setIsRegister(true); clearError(); }}
              className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-all ${
                isRegister
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Create Account
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@domain.com"
                className="nv-input bg-slate-800 border-slate-700 text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:ring-blue-500/15"
                required
                disabled={loading}
                autoComplete="email"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="nv-input bg-slate-800 border-slate-700 text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:ring-blue-500/15 pr-10"
                  required
                  disabled={loading}
                  autoComplete={isRegister ? 'new-password' : 'current-password'}
                  minLength={isRegister ? 8 : undefined}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                </button>
              </div>
              {isRegister && (
                <p className="text-[10px] text-slate-500">Minimum 8 characters required.</p>
              )}
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                <Globe className="w-2.5 h-2.5" />
                Backend URL
              </label>
              <input
                type="url"
                value={serverUrl}
                onChange={(e) => handleServerUrlChange(e.target.value)}
                placeholder="http://localhost:8001"
                className="nv-input bg-slate-800 border-slate-700 text-slate-100 placeholder-slate-500 focus:border-blue-500 text-xs"
                disabled={loading}
                required
              />
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-3 rounded-lg text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full h-10 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-sm font-semibold rounded-lg transition-all duration-200 flex items-center justify-center gap-2 shadow-lg shadow-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500/40"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Authenticating...</span>
                </>
              ) : isRegister ? (
                'Create Account'
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          {/* Footer */}
          <p className="text-center text-[10px] text-slate-600">
            IRIS — Your documents, your data, your privacy.
          </p>
        </div>
      </div>
    </div>
  );
};
