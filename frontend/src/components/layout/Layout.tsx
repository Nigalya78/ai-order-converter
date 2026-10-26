import React, { useState } from 'react';
import { Sidebar } from './Sidebar';
import type { NavTab } from './Sidebar';
import { Header } from './Header';
import { X } from 'lucide-react';
import { ToastContainer } from '../common/Toast';
import type { ToastMessage } from '../common/Toast';

interface LayoutProps {
  currentTab: NavTab;
  onNavigate: (tab: NavTab) => void;
  orderCount?: number;
  apiConnected?: boolean | null;
  apiUrl: string;
  onRefresh?: () => void;
  isRefreshing?: boolean;
  selectedOrderId?: number | null;
  toasts?: ToastMessage[];
  onDismissToast?: (id: string) => void;
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({
  currentTab,
  onNavigate,
  orderCount,
  apiConnected,
  apiUrl,
  onRefresh,
  isRefreshing,
  selectedOrderId,
  toasts = [],
  onDismissToast = () => {},
  children,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleMobileNav = (tab: NavTab) => {
    onNavigate(tab);
    setMobileMenuOpen(false);
  };

  return (
    <div className="min-h-screen flex bg-slate-50 font-sans">
      {}
      <div className="hidden lg:flex shrink-0">
        <Sidebar
          currentTab={currentTab}
          onNavigate={onNavigate}
          orderCount={orderCount}
          apiConnected={apiConnected}
          apiUrl={apiUrl}
        />
      </div>

      {}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          {}
          <div
            className="fixed inset-0 bg-slate-900/70 backdrop-blur-xs transition-opacity duration-200"
            onClick={() => setMobileMenuOpen(false)}
            aria-hidden="true"
          />

          {}
          <div className="relative flex flex-col w-72 max-w-[85vw] bg-slate-900 z-10 shadow-2xl animate-fadeIn">
            <div className="absolute top-4 right-4 z-20">
              <button
                type="button"
                onClick={() => setMobileMenuOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white bg-slate-800 transition-colors"
                aria-label="Close navigation"
              >
                <X size={18} />
              </button>
            </div>
            <Sidebar
              currentTab={currentTab}
              onNavigate={handleMobileNav}
              orderCount={orderCount}
              apiConnected={apiConnected}
              apiUrl={apiUrl}
            />
          </div>
        </div>
      )}

      {}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen">
        {}
        <Header
          currentTab={currentTab}
          onNavigateToOrders={() => onNavigate('orders')}
          onNewOrderClick={() => onNavigate('message-to-order')}
          onToggleMobileMenu={() => setMobileMenuOpen(true)}
          onRefresh={onRefresh}
          isRefreshing={isRefreshing}
          selectedOrderId={selectedOrderId}
          apiConnected={apiConnected}
        />

        {}
        <main className="flex-1 p-3.5 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto animate-fadeIn">
          {children}
        </main>
      </div>

      {}
      <ToastContainer toasts={toasts} onDismiss={onDismissToast} />
    </div>
  );
};
