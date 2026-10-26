import React from 'react';
import {
  LayoutDashboard,
  ShoppingBag,
  Sparkles,
  BookOpen,
  MessageSquareText,
  Database,
  ExternalLink,
} from 'lucide-react';

export type NavTab = 'dashboard' | 'chat' | 'orders' | 'message-to-order' | 'catalog';

interface SidebarProps {
  currentTab: NavTab;
  onNavigate: (tab: NavTab) => void;
  orderCount?: number;
  apiConnected?: boolean | null;
  apiUrl: string;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onNavigate,
  orderCount,
  apiConnected,
  apiUrl,
}) => {
  const navItems = [
    {
      id: 'dashboard' as NavTab,
      label: 'Overview',
      icon: LayoutDashboard,
      badge: null,
    },
    {
      id: 'chat' as NavTab,
      label: 'AI Chat to Order',
      icon: MessageSquareText,
      highlight: true,
      badge: 'Interactive',
    },
    {
      id: 'orders' as NavTab,
      label: 'Orders',
      icon: ShoppingBag,
      badge: orderCount !== undefined ? orderCount : null,
    },
    {
      id: 'message-to-order' as NavTab,
      label: 'AI Message Converter',
      icon: Sparkles,
      badge: 'Raw Text',
    },
    {
      id: 'catalog' as NavTab,
      label: 'Product Catalogue',
      icon: BookOpen,
      badge: '4 items',
    },
  ];

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0 min-h-screen border-r border-slate-800 select-none">
      {}
      <div className="h-16 px-6 flex items-center gap-3 border-b border-slate-800/80 bg-slate-950/40">
        <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-violet-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/25 ring-1 ring-white/20">
          <Sparkles size={18} />
        </div>
        <div>
          <span className="font-extrabold text-white text-sm tracking-tight block leading-tight">
            OrderConverter
          </span>
          <span className="text-[10px] font-semibold text-indigo-400 tracking-wider uppercase">
            AI Assistant · South Indian Snacks
          </span>
        </div>
      </div>

      {}
      <div className="px-3 py-5 flex-1 space-y-1">
        <div className="px-3 pb-2 text-[10px] font-bold tracking-wider text-slate-500 uppercase">
          Navigation Menu
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all duration-150 ${
                isActive
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20 translate-x-0.5'
                  : 'text-slate-300 hover:bg-slate-800/80 hover:text-white'
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon
                  size={17}
                  className={
                    isActive
                      ? 'text-white'
                      : item.highlight
                      ? 'text-indigo-400'
                      : 'text-slate-400'
                  }
                />
                <span>{item.label}</span>
              </div>
            </button>
          );
        })}
      </div>
    </aside>
  );
};
