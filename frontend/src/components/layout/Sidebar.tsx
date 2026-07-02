import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
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
  Folder,
  ChevronLeft,
  ChevronRight,
  Sun,
  Moon
} from 'lucide-react';

interface SidebarProps {
  darkMode: boolean;
  setDarkMode: (val: boolean) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ darkMode, setDarkMode }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const activeCategory = useVaultStore((state) => state.activeCategory);
  const setActiveCategory = useVaultStore((state) => state.setActiveCategory);
  const [isCollapsed, setIsCollapsed] = useState(false);

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Knowledge Graph', href: '/graph', icon: Network },
    { name: 'Memory Assistant', href: '/chat', icon: MessageSquare },
    { name: 'Upload Center', href: '/upload', icon: UploadCloud },
    { name: 'Settings', href: '/settings', icon: Settings },
  ];

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
    navigate('/vault');
  };

  return (
    <aside 
      className={`${
        isCollapsed ? 'w-14' : 'w-60'
      } bg-white dark:bg-slate-900 border-r border-[#E5E7EB] dark:border-slate-800 flex flex-col h-screen transition-all duration-200 ease-in-out shrink-0 select-none`}
    >
      {/* Brand Identity & Collapse Toggle */}
      <div className="h-14 px-4 border-b border-[#E5E7EB] dark:border-slate-800 flex items-center justify-between overflow-hidden">
        {!isCollapsed && (
          <div className="flex items-center gap-2 font-semibold text-sm tracking-tight text-[#111827] dark:text-slate-100">
            <FolderLock className="w-5 h-5 text-[#2563EB]" />
            <span>NeuroVault AI</span>
          </div>
        )}
        {isCollapsed && (
          <FolderLock className="w-5 h-5 text-[#2563EB] mx-auto" />
        )}
        <button 
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1 hover:bg-[#F3F4F6] dark:hover:bg-slate-800 rounded text-[#6B7280] dark:text-slate-400 focus:outline-none transition-colors"
          title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
        >
          {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Main Nav */}
      <nav className="p-2 space-y-1 flex-1 overflow-y-auto overflow-x-hidden">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href;
          return (
            <Link
              key={item.name}
              to={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded text-xs font-medium transition-all relative ${
                isActive
                  ? 'bg-[#F3F4F6] dark:bg-slate-800 text-[#2563EB] dark:text-[#2563EB] font-semibold'
                  : 'text-[#6B7280] dark:text-slate-400 hover:bg-[#F3F4F6]/50 dark:hover:bg-slate-800/40 hover:text-[#111827] dark:hover:text-slate-100'
              }`}
              title={isCollapsed ? item.name : undefined}
            >
              {isActive && (
                <div className="absolute left-0 top-1.5 bottom-1.5 w-1 bg-[#2563EB] rounded-r" />
              )}
              <item.icon className="w-4 h-4 shrink-0" />
              {!isCollapsed && <span>{item.name}</span>}
            </Link>
          );
        })}

        {/* Separator / Section Header */}
        <div className="py-2">
          {isCollapsed ? (
            <div className="border-b border-[#E5E7EB] dark:border-slate-800 my-1 mx-1" />
          ) : (
            <p className="px-3 text-[10px] font-bold text-[#6B7280] dark:text-slate-500 uppercase tracking-wider">
              Smart folders
            </p>
          )}
        </div>

        {/* Smart Folder Tree */}
        <div className="space-y-1">
          {smartFolders.map((folder) => {
            const isSelected = activeCategory === folder.value;
            return (
              <button
                key={folder.name}
                onClick={() => handleFolderClick(folder.value)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded text-xs font-medium transition-all text-left relative ${
                  isSelected
                    ? 'bg-[#F3F4F6] dark:bg-slate-800 text-[#111827] dark:text-slate-100 font-semibold'
                    : 'text-[#6B7280] dark:text-slate-400 hover:bg-[#F3F4F6]/30 dark:hover:bg-slate-800/30 hover:text-[#111827] dark:hover:text-slate-100'
                }`}
                title={isCollapsed ? folder.name : undefined}
              >
                {isSelected && (
                  <div className="absolute left-0 top-1.5 bottom-1.5 w-1 bg-[#2563EB] rounded-r" />
                )}
                <Folder className={`w-4 h-4 shrink-0 ${isSelected ? 'text-[#2563EB]' : 'text-[#6B7280] dark:text-slate-400'}`} />
                {!isCollapsed && <span className="truncate">{folder.name}</span>}
              </button>
            );
          })}
        </div>
      </nav>

      {/* Footer Settings & Logout */}
      <div className="p-2 border-t border-[#E5E7EB] dark:border-slate-800 space-y-1 shrink-0 bg-white dark:bg-slate-900">
        {/* Theme Toggle */}
        <button
          onClick={() => setDarkMode(!darkMode)}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded text-xs font-medium text-[#6B7280] dark:text-slate-400 hover:bg-[#F3F4F6] dark:hover:bg-slate-800 transition-colors"
          title={isCollapsed ? (darkMode ? 'Light Mode' : 'Dark Mode') : undefined}
        >
          {darkMode ? (
            <Sun className="w-4 h-4 text-[#F59E0B] shrink-0" />
          ) : (
            <Moon className="w-4 h-4 text-[#2563EB] shrink-0" />
          )}
          {!isCollapsed && (
            <div className="flex items-center justify-between w-full">
              <span>{darkMode ? 'Light Theme' : 'Dark Theme'}</span>
              <span className="text-[9px] border border-[#E5E7EB] dark:border-slate-700 px-1 py-0.2 rounded bg-[#F8FAFC] dark:bg-slate-950 font-bold">
                {darkMode ? 'DARK' : 'LIGHT'}
              </span>
            </div>
          )}
        </button>

        {/* Logout */}
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded text-xs font-medium text-[#DC2626] hover:bg-[#DC2626]/5 transition-colors text-left"
          title={isCollapsed ? "Sign Out" : undefined}
        >
          <LogOut className="w-4 h-4 shrink-0" />
          {!isCollapsed && <span>Sign Out</span>}
        </button>
      </div>
    </aside>
  );
};
