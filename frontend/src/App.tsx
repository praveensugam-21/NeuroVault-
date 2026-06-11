import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/useAuthStore';
import { useVaultStore } from './store/useVaultStore';
import { Sidebar } from './components/layout/Sidebar';
import { Dashboard } from './pages/Dashboard';
import { Vault } from './pages/Vault';
import { KnowledgeGraph } from './pages/KnowledgeGraph';
import { Chat } from './pages/Chat';
import { Upload } from './pages/Upload';
import { Settings } from './pages/Settings';
import { Login } from './pages/Login';

const App: React.FC = () => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const activeCategory = useVaultStore((state) => state.activeCategory);

  // Initialize theme mode from system preferences or state
  const [darkMode, setDarkMode] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('theme');
      if (stored) return stored === 'dark';
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    return true;
  });

  // Keep HTML document classes synchronized with dark mode selection
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [darkMode]);

  if (!isAuthenticated) {
    return <Login />;
  }

  return (
    <BrowserRouter>
      <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
        {/* Navigation Sidebar */}
        <Sidebar darkMode={darkMode} setDarkMode={setDarkMode} />

        {/* Core Content Area */}
        <main className="flex-1 h-full overflow-hidden relative">
          <Routes>
            <Route path="/dashboard" element={<Dashboard />} />
            
            {/* If a category is selected in the sidebar, let Vault handle filtering */}
            <Route path="/vault" element={<Vault />} />
            
            <Route path="/graph" element={<KnowledgeGraph />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/settings" element={<Settings />} />
            
            {/* Catch-all redirects */}
            <Route 
              path="*" 
              element={
                activeCategory 
                  ? <Navigate to="/vault" replace /> 
                  : <Navigate to="/dashboard" replace />
              } 
            />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
};

export default App;
