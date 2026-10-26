import React, { useState, useEffect, useCallback } from 'react';
import { Layout } from './components/layout/Layout';
import type { NavTab } from './components/layout/Sidebar';
import { DashboardPage } from './pages/DashboardPage';
import { OrdersPage } from './pages/OrdersPage';
import { OrderDetailPage } from './pages/OrderDetailPage';
import { MessageToOrderPage } from './pages/MessageToOrderPage';
import { ChatToOrderPage } from './pages/ChatToOrderPage';
import { CatalogPage } from './pages/CatalogPage';
import { OrderStatusModal } from './components/orders/OrderStatusModal';
import { OrderModifyModal } from './components/orders/OrderModifyModal';
import type { Order, OrderStatus } from './api/types';
import type { ToastMessage, ToastType } from './components/common/Toast';
import api from './api/client';
import { AlertBanner } from './components/common/AlertBanner';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<NavTab>('dashboard');
  const [selectedOrderId, setSelectedOrderId] = useState<number | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoadingOrders, setIsLoadingOrders] = useState(false);
  const [apiConnected, setApiConnected] = useState<boolean | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const showToast = useCallback((title: string, message?: string, type: ToastType = 'info') => {
    const id = Date.now().toString() + Math.random().toString(36).substring(2, 5);
    setToasts((prev) => [...prev, { id, title, message, type }]);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);
  const [statusModalOrder, setStatusModalOrder] = useState<Order | null>(null);
  const [modifyModalOrder, setModifyModalOrder] = useState<Order | null>(null);
  const [prefilledMessage, setPrefilledMessage] = useState<string>('');
  const fetchOrders = useCallback(async () => {
    setIsLoadingOrders(true);
    setFetchError(null);
    try {
      const response = await api.getOrders();
      setOrders(response.orders || []);
      setApiConnected(true);
    } catch (err: any) {
      setApiConnected(false);
      setFetchError(err.message || 'Failed to connect to backend server');
    } finally {
      setIsLoadingOrders(false);
    }
  }, []);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  const handleNavigate = (tab: NavTab) => {
    setCurrentTab(tab);
    if (tab !== 'orders') {
      setSelectedOrderId(null);
    }
  };

  const handleSelectOrder = (orderId: number) => {
    setSelectedOrderId(orderId);
    setCurrentTab('orders');
  };

  const handleOrderCreated = (orderId: number) => {
    fetchOrders();
    setSelectedOrderId(orderId);
    setCurrentTab('orders');
    showToast('Order Placed!', `Order #${orderId} saved to database in payment_pending status`, 'success');
  };

  const handleStatusUpdated = ({
    order_id,
    status,
  }: {
    order_id: number;
    status: OrderStatus;
  }) => {
    setOrders((prev) =>
      prev.map((ord) => (ord.order_id === order_id ? { ...ord, status } : ord))
    );
    showToast('Status Updated', `Order #${order_id} is now ${status.replace('_', ' ')}`, 'success');
    fetchOrders();
  };

  const handleOrderModified = () => {
    showToast('Order Modified', 'Order items successfully updated', 'success');
    fetchOrders();
  };

  return (
    <Layout
      currentTab={currentTab}
      onNavigate={handleNavigate}
      orderCount={orders.length}
      apiConnected={apiConnected}
      apiUrl={api.getBaseUrl()}
      onRefresh={() => {
        fetchOrders();
        showToast('Refreshed', 'Orders reloaded from database', 'info');
      }}
      isRefreshing={isLoadingOrders}
      selectedOrderId={selectedOrderId}
      toasts={toasts}
      onDismissToast={dismissToast}
    >
      {}
      {fetchError && (
        <div className="mb-6">
          <AlertBanner
            type="error"
            title="Backend Connection Error"
            message={
              <div>
                <p>{fetchError}</p>
                <p className="mt-1 text-xs opacity-90">
                  Ensure FastAPI backend is running via{' '}
                  <code className="bg-rose-100 px-1 py-0.5 rounded font-mono">
                    uvicorn app.main:app --reload
                  </code>{' '}
                  at{' '}
                  <code className="bg-rose-100 px-1 py-0.5 rounded font-mono">
                    {api.getBaseUrl()}
                  </code>
                </p>
              </div>
            }
            onDismiss={() => setFetchError(null)}
          />
        </div>
      )}

      {}
      {currentTab === 'dashboard' && (
        <DashboardPage
          orders={orders}
          isLoading={isLoadingOrders}
          onNavigateToOrders={() => setCurrentTab('orders')}
          onNavigateToAI={() => setCurrentTab('chat')}
          onSelectOrder={handleSelectOrder}
          onOpenStatusModal={(order: Order) => setStatusModalOrder(order)}
        />
      )}

      {currentTab === 'chat' && (
        <ChatToOrderPage
          onNavigateToOrder={handleSelectOrder}
          onShowToast={showToast}
        />
      )}

      {currentTab === 'orders' &&
        (selectedOrderId !== null ? (
          <OrderDetailPage
            orderId={selectedOrderId}
            onBack={() => setSelectedOrderId(null)}
            onOrderUpdated={fetchOrders}
            onShowToast={showToast}
          />
        ) : (
          <OrdersPage
            orders={orders}
            isLoading={isLoadingOrders}
            onSelectOrder={handleSelectOrder}
            onOpenStatusModal={(order) => setStatusModalOrder(order)}
            onOpenModifyModal={(order) => setModifyModalOrder(order)}
            onNavigateToAI={() => setCurrentTab('message-to-order')}
          />
        ))}

      {currentTab === 'message-to-order' && (
        <MessageToOrderPage
          onOrderCreated={handleOrderCreated}
          initialMessage={prefilledMessage}
        />
      )}

      {currentTab === 'catalog' && (
        <CatalogPage
          onSelectSampleMessage={(sampleText) => {
            setPrefilledMessage(sampleText);
            setCurrentTab('message-to-order');
          }}
        />
      )}

      {}
      <OrderStatusModal
        order={statusModalOrder}
        isOpen={statusModalOrder !== null}
        onClose={() => setStatusModalOrder(null)}
        onStatusUpdated={handleStatusUpdated}
        updateStatusFn={api.updateOrderStatus.bind(api)}
      />

      <OrderModifyModal
        order={modifyModalOrder}
        isOpen={modifyModalOrder !== null}
        onClose={() => setModifyModalOrder(null)}
        onOrderModified={handleOrderModified}
      />
    </Layout>
  );
};

export default App;
