import React, { useState } from 'react';
import { useAuthStore } from '../store/useAuthStore';
import { FolderLock, AlertCircle, Loader2, Globe } from 'lucide-react';
import { getApiUrl } from '../services/api';

export const Login: React.FC = () => {
  const { login, register, error, clearError, loading } = useAuthStore();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
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
        // Automatically log in after registration
        await login(email, password);
      }
    } else {
      await login(email, password);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] dark:bg-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 p-8 rounded shadow-[0_1px_3px_rgba(0,0,0,0.05)] space-y-6">
        
        {/* Brand Header */}
        <div className="flex flex-col items-center text-center space-y-2 select-none">
          <div className="p-2 bg-[#F3F4F6] dark:bg-slate-800 rounded border border-[#E5E7EB] dark:border-slate-800">
            <FolderLock className="w-5 h-5 text-[#2563EB]" />
          </div>
          <h2 className="text-lg font-semibold tracking-tight text-[#111827] dark:text-slate-100">
            NeuroVault
          </h2>
          <p className="text-xs text-[#6B7280] dark:text-slate-400">
            Secure Personal Document Vault
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1">
            <label className="text-[10px] font-bold text-[#6B7280] dark:text-slate-400 uppercase tracking-wider">
              Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@company.com"
              className="nv-input"
              required
              disabled={loading}
            />
          </div>

          <div className="space-y-1">
            <label className="text-[10px] font-bold text-[#6B7280] dark:text-slate-400 uppercase tracking-wider">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="nv-input"
              required
              disabled={loading}
            />
          </div>

          <div className="space-y-1">
            <label className="text-[10px] font-bold text-[#6B7280] dark:text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <Globe className="w-3 h-3 text-[#6B7280] dark:text-slate-400" />
              Server URL
            </label>
            <input
              type="url"
              value={serverUrl}
              onChange={(e) => handleServerUrlChange(e.target.value)}
              placeholder="http://localhost:8001"
              className="nv-input text-xs"
              disabled={loading}
              required
            />
          </div>

          {error && (
            <div className="bg-[#DC2626]/5 border border-[#DC2626]/20 text-[#DC2626] p-3 rounded text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span className="font-medium">{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full nv-btn-primary h-10 font-semibold"
          >
            {loading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Authenticating...</span>
              </>
            ) : isRegister ? (
              'Create Account'
            ) : (
              'Sign In'
            )}
          </button>
        </form>

        {/* Toggle Mode */}
        <div className="text-center pt-2 border-t border-[#E5E7EB] dark:border-slate-800">
          <button
            type="button"
            onClick={() => {
              setIsRegister(!isRegister);
              clearError();
            }}
            className="text-xs text-[#6B7280] dark:text-slate-400 hover:text-[#2563EB] transition-colors"
          >
            {isRegister ? 'Already have an account? Sign In' : "Don't have an account? Sign Up"}
          </button>
        </div>
      </div>
    </div>
  );
};
