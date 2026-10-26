import React, { useState, useEffect } from 'react';
import type { Order, OrderStatus } from '../api/types';
import api from '../api/client';
import { OrderDetail } from '../components/orders/OrderDetail';
import { OrderStatusModal } from '../components/orders/OrderStatusModal';
import { OrderModifyModal } from '../components/orders/OrderModifyModal';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { AlertBanner } from '../components/common/AlertBanner';
import { ArrowLeft } from 'lucide-react';

interface OrderDetailPageProps {
  orderId: number;
  onBack: () => void;
  onOrderUpdated: () => void;
  onShowToast?: (title: string, message?: string, type?: 'success' | 'error' | 'info') => void;
}

export const OrderDetailPage: React.FC<OrderDetailPageProps> = ({
  orderId,
  onBack,
  onOrderUpdated,
  onShowToast,
}) => {
  const [order, setOrder] = useState<Order | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isStatusModalOpen, setIsStatusModalOpen] = useState(false);
  const [isModifyModalOpen, setIsModifyModalOpen] = useState(false);

  const fetchOrder = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getOrderById(orderId);
      setOrder(data);
    } catch (err: any) {
      setError(err.message || `Failed to fetch order #${orderId}`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchOrder();
  }, [orderId]);

  const handleStatusUpdated = ({ status }: { order_id: number; status: OrderStatus }) => {
    if (order) {
      setOrder({ ...order, status });
    }
    if (onShowToast) {
      onShowToast('Status Updated', `Order #${orderId} marked as ${status.replace('_', ' ')}`, 'success');
    }
    onOrderUpdated();
    fetchOrder();
  };

  const handleOrderModified = () => {
    if (onShowToast) {
      onShowToast('Order Modified', `Order #${orderId} line items updated`, 'success');
    }
    onOrderUpdated();
    fetchOrder();
  };

  if (isLoading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center">
        <LoadingSpinner size="lg" label={`Loading order #${orderId} details...`} />
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="space-y-4 max-w-xl mx-auto py-12">
        <AlertBanner
          type="error"
          title="Order Not Found"
          message={error || `Could not find an order with ID #${orderId}.`}
        />
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 px-3.5 py-1.5 rounded-xl hover:bg-slate-50 transition-colors"
        >
          <ArrowLeft size={14} />
          <span>Return to Orders List</span>
        </button>
      </div>
    );
  }

  return (
    <>
      <OrderDetail
        order={order}
        onBack={onBack}
        onOpenStatusModal={() => setIsStatusModalOpen(true)}
        onOpenModifyModal={() => setIsModifyModalOpen(true)}
        onShowToast={onShowToast}
      />

      {}
      <OrderStatusModal
        order={order}
        isOpen={isStatusModalOpen}
        onClose={() => setIsStatusModalOpen(false)}
        onStatusUpdated={handleStatusUpdated}
        updateStatusFn={api.updateOrderStatus.bind(api)}
      />

      {}
      <OrderModifyModal
        order={order}
        isOpen={isModifyModalOpen}
        onClose={() => setIsModifyModalOpen(false)}
        onOrderModified={handleOrderModified}
      />
    </>
  );
};
