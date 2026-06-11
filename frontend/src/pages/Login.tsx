import React, { useState } from 'react';
import { useAuthStore } from '../store/useAuthStore';
import { FolderLock, AlertCircle } from 'lucide-react';

export const Login: React.FC = () => {
  const { login, register, error, clearError, loading } = useAuthStore();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

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
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-card border border-border p-8 rounded-lg space-y-6 shadow-lg">
        {/* Brand */}
        <div className="flex flex-col items-center text-center space-y-2 select-none">
          <div className="p-3 bg-secondary rounded border border-border">
            <FolderLock className="w-6 h-6 text-primary" />
          </div>
          <h2 className="text-xl font-bold tracking-tight">NeuroVault AI</h2>
          <p className="text-xs text-muted-foreground">Personal Knowledge Reasoning Layer</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1">
            <label className="text-[10px] font-semibold text-muted-foreground uppercase">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@company.com"
              className="w-full bg-background border border-border rounded px-3 py-2 text-xs focus:outline-none focus:border-primary"
              required
            />
          </div>

          <div className="space-y-1">
            <label className="text-[10px] font-semibold text-muted-foreground uppercase">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full bg-background border border-border rounded px-3 py-2 text-xs focus:outline-none focus:border-primary"
              required
            />
          </div>

          {error && (
            <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900 text-red-800 dark:text-red-400 p-3 rounded text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-primary text-primary-foreground hover:bg-primary/95 py-2.5 rounded text-xs font-semibold disabled:opacity-50 transition-colors"
          >
            {loading ? 'Authenticating...' : isRegister ? 'Create Account' : 'Sign In'}
          </button>
        </form>

        {/* Toggle Mode */}
        <div className="text-center">
          <button
            type="button"
            onClick={() => {
              setIsRegister(!isRegister);
              clearError();
            }}
            className="text-[11px] text-muted-foreground hover:underline"
          >
            {isRegister ? 'Already have an account? Sign In' : "Don't have an account? Sign Up"}
          </button>
        </div>
      </div>
    </div>
  );
};
