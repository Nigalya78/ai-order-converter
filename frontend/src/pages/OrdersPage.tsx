import React from 'react';
import type { Order } from '../api/types';
import { OrdersTable } from '../components/orders/OrdersTable';
import { Sparkles } from 'lucide-react';

interface OrdersPageProps {
  orders: Order[];
  isLoading: boolean;
  onSelectOrder: (orderId: number) => void;
  onOpenStatusModal: (order: Order) => void;
  onOpenModifyModal: (order: Order) => void;
  onNavigateToAI: () => void;
}

export const OrdersPage: React.FC<OrdersPageProps> = ({
  orders,
  isLoading,
  onSelectOrder,
  onOpenStatusModal,
  onOpenModifyModal,
  onNavigateToAI,
}) => {
  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Orders Registry</h2>
          <p className="text-xs text-slate-500 mt-1">
            Browse, filter, and track customer snack orders generated via WhatsApp or chat messages
          </p>
        </div>

        <button
          type="button"
          onClick={onNavigateToAI}
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 rounded-xl shadow-xs transition-all hover:scale-[1.01] self-start sm:self-auto"
        >
          <Sparkles size={14} />
          <span>New Order via AI</span>
        </button>
      </div>

      {}
      <OrdersTable
        orders={orders}
        isLoading={isLoading}
        onSelectOrder={onSelectOrder}
        onOpenStatusModal={onOpenStatusModal}
        onOpenModifyModal={onOpenModifyModal}
        onNewOrderClick={onNavigateToAI}
      />
    </div>
  );
};
