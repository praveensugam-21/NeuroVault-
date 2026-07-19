import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../store/useAuthStore';
import { Brain, AlertCircle, Loader2, Globe, Eye, EyeOff, Lock } from 'lucide-react';
import { getApiUrl } from '../services/api';
import api from '../services/api';

export const Login: React.FC = () => {
  const { login, loginWithGoogle, register, error, clearError, loading } = useAuthStore();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [googleClientId, setGoogleClientId] = useState<string | null>(null);
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

  // Fetch authentication configuration (like Google Client ID) from backend on mount
  useEffect(() => {
    api.get('/api/auth/config')
      .then(res => {
        if (res.data && res.data.google_client_id) {
          setGoogleClientId(res.data.google_client_id);
        }
      })
      .catch(err => {
        console.error("Failed to load auth config:", err);
      });
  }, []);

  // Dynamically load the Google GIS script and render the button if a client ID is configured
  useEffect(() => {
    if (!googleClientId) return;

    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => {
      if ((window as any).google) {
        (window as any).google.accounts.id.initialize({
          client_id: googleClientId,
          callback: handleGoogleLoginResponse,
        });

        (window as any).google.accounts.id.renderButton(
          document.getElementById('google-signin-btn'),
          {
            theme: 'outline',
            size: 'large',
            text: 'signin_with',
            shape: 'rectangular',
            logo_alignment: 'left',
            width: 320,
          }
        );
      }
    };
    document.body.appendChild(script);

    return () => {
      document.body.removeChild(script);
    };
  }, [googleClientId]);

  const handleGoogleLoginResponse = async (response: any) => {
    if (response && response.credential) {
      clearError();
      await loginWithGoogle(response.credential);
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
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4 font-sans antialiased">
      <div className="w-full max-w-md">
        {/* Main Card: Clean borders, professional typography, organized layout */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl shadow-lg p-8 space-y-6">
          
          {/* Header */}
          <div className="flex flex-col items-center text-center space-y-4">
            <div className="w-12 h-12 bg-slate-800 border border-slate-700 rounded-xl flex items-center justify-center">
              <Brain className="w-6 h-6 text-blue-500" />
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-tight text-white">
                IRIS Document Vault
              </h1>
              <p className="text-xs text-slate-400 mt-1">
                Intelligent Retrieval and Information System
              </p>
            </div>
            <div className="flex items-center gap-1.5 text-[10px] text-slate-400 bg-slate-850 border border-slate-800 px-3 py-1 rounded-md">
              <Lock className="w-3 h-3 text-emerald-500" />
              <span>AES-256 Encrypted · Self-hosted Privacy</span>
            </div>
          </div>

          {/* Toggle local login/register */}
          <div className="flex bg-slate-800/80 border border-slate-700/50 rounded-lg p-1">
            <button
              type="button"
              onClick={() => { setIsRegister(false); clearError(); }}
              className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-colors ${
                !isRegister
                  ? 'bg-slate-700 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => { setIsRegister(true); clearError(); }}
              className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-colors ${
                isRegister
                  ? 'bg-slate-700 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Register
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@domain.com"
                className="w-full h-9 px-3 bg-slate-800 border border-slate-750 rounded-md text-slate-100 placeholder-slate-500 text-xs focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                required
                disabled={loading}
                autoComplete="email"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full h-9 pl-3 pr-10 bg-slate-800 border border-slate-750 rounded-md text-slate-100 placeholder-slate-500 text-xs focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
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
                <p className="text-[10px] text-slate-500 mt-0.5">Password must be at least 8 characters.</p>
              )}
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                <Globe className="w-2.5 h-2.5" />
                Backend URL
              </label>
              <input
                type="url"
                value={serverUrl}
                onChange={(e) => handleServerUrlChange(e.target.value)}
                placeholder="http://localhost:8001"
                className="w-full h-9 px-3 bg-slate-800 border border-slate-750 rounded-md text-slate-100 placeholder-slate-500 text-xs focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
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
              className="w-full h-9 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-md transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-1 focus:ring-blue-500"
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

          {/* Render Google Sign-in if configured on the backend */}
          {googleClientId && !isRegister && (
            <div className="space-y-4">
              <div className="relative flex py-1 items-center text-[10px] text-slate-500 font-bold uppercase tracking-wider">
                <div className="flex-grow border-t border-slate-800"></div>
                <span className="flex-shrink mx-4 text-slate-500">Or Continue With</span>
                <div className="flex-grow border-t border-slate-800"></div>
              </div>

              <div className="flex justify-center w-full">
                <div id="google-signin-btn" className="w-full flex justify-center"></div>
              </div>
            </div>
          )}

          {/* Footer Info */}
          <p className="text-center text-[10px] text-slate-500 border-t border-slate-850 pt-4">
            IRIS is fully self-hosted. All document storage, metadata database, and AI processing remain 100% under your control.
          </p>
        </div>
      </div>
    </div>
  );
};
