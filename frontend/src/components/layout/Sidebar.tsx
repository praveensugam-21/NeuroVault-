import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/useAuthStore';
import { useVaultStore } from '../../store/useVaultStore';
import {
  LayoutDashboard,
  FolderLock,
  Network,
  MessageSquare,
  UploadCloud,
  Settings,
  LogOut,
  Folder
} from 'lucide-react';


interface SidebarProps {
  darkMode: boolean;
  setDarkMode: (val: boolean) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ darkMode, setDarkMode }) => {
  const location = useLocation();
  const logout = useAuthStore((state) => state.logout);
  const activeCategory = useVaultStore((state) => state.activeCategory);
  const setActiveCategory = useVaultStore((state) => state.setActiveCategory);

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Knowledge Graph', href: '/graph', icon: Network },
    { name: 'Memory Assistant', href: '/chat', icon: MessageSquare },
    { name: 'Upload Center', href: '/upload', icon: UploadCloud },
    { name: 'Settings', href: '/settings', icon: Settings },
  ];

  // Smart Folder list matching Section 6
  const smartFolders = [
    { name: 'Identity Documents', value: 'Identity Documents' },
    { name: 'Academic Records', value: 'Academic Records' },
    { name: 'Professional Documents', value: 'Professional Documents' },
    { name: 'Financial Documents', value: 'Financial Documents' },
    { name: 'Medical Records', value: 'Medical Records' },
    { name: 'Property & Legal', value: 'Property & Legal' },
    { name: 'Vehicle Documents', value: 'Vehicle Documents' },
    { name: 'Personal Notes', value: 'Personal Notes' },
    { name: 'Unclassified', value: 'Unclassified (Review Needed)' },
  ];

  const handleFolderClick = (val: string) => {
    setActiveCategory(activeCategory === val ? null : val);
  };

  return (
    <aside className="w-64 bg-card border-r border-border flex flex-col h-screen overflow-y-auto">
      {/* Brand Identity */}
      <div className="p-6 border-b border-border flex items-center gap-3">
        <FolderLock className="w-6 h-6 text-primary" />
        <span className="font-semibold text-lg tracking-tight select-none">NeuroVault AI</span>
      </div>

      {/* Main Nav */}
      <nav className="p-4 space-y-1 flex-1">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href;
          return (
            <Link
              key={item.name}
              to={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              }`}
            >
              <item.icon className="w-4 h-4" />
              {item.name}
            </Link>
          );
        })}

        <div className="pt-4 pb-2">
          <p className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            Smart folders
          </p>
        </div>

        {/* Smart Folder Tree */}
        <div className="space-y-1">
          {smartFolders.map((folder) => {
            const isSelected = activeCategory === folder.value;
            return (
              <button
                key={folder.name}
                onClick={() => handleFolderClick(folder.value)}
                className={`w-full flex items-center gap-3 px-3 py-1.5 rounded-md text-sm font-medium transition-colors text-left ${
                  isSelected
                    ? 'bg-secondary text-foreground font-semibold border border-border'
                    : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
                }`}
              >
                <Folder className={`w-4 h-4 ${isSelected ? 'text-primary' : 'text-muted-foreground'}`} />
                <span className="truncate">{folder.name}</span>
              </button>
            );
          })}
        </div>
      </nav>

      {/* Profile/Footer */}
      <div className="p-4 border-t border-border space-y-3">
        {/* Theme Toggle */}
        <button
          onClick={() => setDarkMode(!darkMode)}
          className="w-full flex items-center justify-between px-3 py-2 rounded-md text-sm font-medium text-muted-foreground hover:bg-muted transition-colors"
        >
          <span>{darkMode ? 'Light Theme' : 'Dark Theme'}</span>
          <span className="text-xs border border-border px-1.5 py-0.5 rounded bg-muted">
            {darkMode ? 'DARK' : 'LIGHT'}
          </span>
        </button>

        {/* Logout */}
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium text-red-600 hover:bg-red-50 hover:dark:bg-red-950/20 transition-colors text-left"
        >
          <LogOut className="w-4 h-4" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
};
