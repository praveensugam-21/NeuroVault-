import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/useAuthStore';
import { useVaultStore } from '../../store/useVaultStore';
import {
  LayoutDashboard,
  Network,
  MessageSquare,
  UploadCloud,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Sun,
  Moon,
  Brain,
  // Category icons
  IdCard,
  GraduationCap,
  Briefcase,
  Landmark,
  HeartPulse,
  Home,
  Car,
  StickyNote,
  HelpCircle,
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
    { name: 'Identity Documents', value: 'Identity Documents', icon: IdCard },
    { name: 'Academic Records', value: 'Academic Records', icon: GraduationCap },
    { name: 'Professional Documents', value: 'Professional Documents', icon: Briefcase },
    { name: 'Financial Documents', value: 'Financial Documents', icon: Landmark },
    { name: 'Medical Records', value: 'Medical Records', icon: HeartPulse },
    { name: 'Property & Legal', value: 'Property & Legal', icon: Home },
    { name: 'Vehicle Documents', value: 'Vehicle Documents', icon: Car },
    { name: 'Personal Notes', value: 'Personal Notes', icon: StickyNote },
    { name: 'Unclassified', value: 'Unclassified', icon: HelpCircle },
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
      {/* Brand & Collapse Toggle */}
      <div className="h-14 px-3 border-b border-[#E5E7EB] dark:border-slate-800 flex items-center justify-between overflow-hidden">
        {!isCollapsed && (
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center flex-shrink-0">
              <Brain className="w-4 h-4 text-white" />
            </div>
            <div className="leading-tight">
              <span className="font-bold text-sm text-[#111827] dark:text-slate-100 tracking-tight">IRIS</span>
              <p className="text-[9px] text-[#6B7280] dark:text-slate-500 leading-none">Document Intelligence</p>
            </div>
          </div>
        )}
        {isCollapsed && (
          <div className="w-7 h-7 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center mx-auto">
            <Brain className="w-4 h-4 text-white" />
          </div>
        )}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1 hover:bg-[#F3F4F6] dark:hover:bg-slate-800 rounded text-[#6B7280] dark:text-slate-400 focus:outline-none transition-colors ml-1 flex-shrink-0"
          title={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Main Navigation */}
      <nav className="p-2 space-y-0.5 flex-1 overflow-y-auto overflow-x-hidden">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href;
          return (
            <Link
              key={item.name}
              to={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all relative ${
                isActive
                  ? 'bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 font-semibold'
                  : 'text-[#6B7280] dark:text-slate-400 hover:bg-[#F3F4F6]/70 dark:hover:bg-slate-800/50 hover:text-[#111827] dark:hover:text-slate-100'
              }`}
              title={isCollapsed ? item.name : undefined}
            >
              {isActive && (
                <div className="absolute left-0 top-1.5 bottom-1.5 w-0.5 bg-blue-600 dark:bg-blue-400 rounded-r" />
              )}
              <item.icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-blue-600 dark:text-blue-400' : ''}`} />
              {!isCollapsed && <span>{item.name}</span>}
            </Link>
          );
        })}

        {/* Smart Folders Section */}
        <div className="pt-3 pb-1">
          {!isCollapsed && (
            <p className="px-3 text-[10px] font-bold text-[#6B7280] dark:text-slate-500 uppercase tracking-widest mb-1">
              Smart Folders
            </p>
          )}
          {isCollapsed && <div className="border-b border-[#E5E7EB] dark:border-slate-800 my-1 mx-1" />}
        </div>

        <div className="space-y-0.5">
          {smartFolders.map((folder) => {
            const isSelected = activeCategory === folder.value;
            const FolderIcon = folder.icon;
            return (
              <button
                key={folder.name}
                onClick={() => handleFolderClick(folder.value)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all text-left relative ${
                  isSelected
                    ? 'bg-[#F3F4F6] dark:bg-slate-800 text-[#111827] dark:text-slate-100 font-semibold'
                    : 'text-[#6B7280] dark:text-slate-400 hover:bg-[#F3F4F6]/50 dark:hover:bg-slate-800/30 hover:text-[#111827] dark:hover:text-slate-200'
                }`}
                title={isCollapsed ? folder.name : undefined}
              >
                {isSelected && (
                  <div className="absolute left-0 top-1.5 bottom-1.5 w-0.5 bg-blue-600 dark:bg-blue-400 rounded-r" />
                )}
                <FolderIcon
                  className={`w-4 h-4 shrink-0 ${
                    isSelected ? 'text-blue-600 dark:text-blue-400' : 'text-[#6B7280] dark:text-slate-400'
                  }`}
                />
                {!isCollapsed && <span className="truncate">{folder.name}</span>}
              </button>
            );
          })}
        </div>
      </nav>

      {/* Footer */}
      <div className="p-2 border-t border-[#E5E7EB] dark:border-slate-800 space-y-0.5 shrink-0">
        <button
          onClick={() => setDarkMode(!darkMode)}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium text-[#6B7280] dark:text-slate-400 hover:bg-[#F3F4F6] dark:hover:bg-slate-800 transition-colors"
          title={isCollapsed ? (darkMode ? 'Light Mode' : 'Dark Mode') : undefined}
        >
          {darkMode ? (
            <Sun className="w-4 h-4 text-amber-500 shrink-0" />
          ) : (
            <Moon className="w-4 h-4 text-blue-500 shrink-0" />
          )}
          {!isCollapsed && (
            <div className="flex items-center justify-between w-full">
              <span>{darkMode ? 'Light Theme' : 'Dark Theme'}</span>
              <span className="text-[9px] border border-[#E5E7EB] dark:border-slate-700 px-1.5 py-0.5 rounded bg-[#F8FAFC] dark:bg-slate-950 font-bold">
                {darkMode ? 'DARK' : 'LIGHT'}
              </span>
            </div>
          )}
        </button>

        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium text-red-500 hover:bg-red-50 dark:hover:bg-red-500/5 transition-colors text-left"
          title={isCollapsed ? 'Sign Out' : undefined}
        >
          <LogOut className="w-4 h-4 shrink-0" />
          {!isCollapsed && <span>Sign Out</span>}
        </button>
      </div>
    </aside>
  );
};
