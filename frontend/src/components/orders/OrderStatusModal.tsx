import React, { useState } from 'react';
import { Modal } from '../common/Modal';
import type { Order, OrderStatus } from '../../api/types';
import { StatusBadge } from '../common/StatusBadge';
import { AlertBanner } from '../common/AlertBanner';
import { LoadingSpinner } from '../common/LoadingSpinner';

interface OrderStatusModalProps {
  order: Order | null;
  isOpen: boolean;
  onClose: () => void;
  onStatusUpdated: (updatedOrder: { order_id: number; status: OrderStatus }) => void;
  updateStatusFn: (orderId: number, status: OrderStatus) => Promise<any>;
}

export const OrderStatusModal: React.FC<OrderStatusModalProps> = ({
  order,
  isOpen,
  onClose,
  onStatusUpdated,
  updateStatusFn,
}) => {
  const [selectedStatus, setSelectedStatus] = useState<OrderStatus | ''>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!order) return null;
  const allowedTransitions: Record<OrderStatus, OrderStatus[]> = {
    payment_pending: ['confirmed', 'cancelled'],
    confirmed: ['cancelled'],
    cancelled: [],
  };

  const validNextStatuses = allowedTransitions[order.status] || [];

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedStatus || selectedStatus === order.status) return;

    setIsSubmitting(true);
    setError(null);

    try {
      await updateStatusFn(order.order_id, selectedStatus);
      onStatusUpdated({
        order_id: order.order_id,
        status: selectedStatus,
      });
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to update order status');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Update Order Status #${order.order_id}`}
      description="Change order status following the backend workflow validation rules"
      maxWidth="md"
    >
      <form onSubmit={handleUpdate} className="space-y-4">
        {error && <AlertBanner type="error" message={error} onDismiss={() => setError(null)} />}

        <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 flex items-center justify-between">
          <span className="text-xs font-medium text-slate-600">Current Status:</span>
          <StatusBadge status={order.status} />
        </div>

        {validNextStatuses.length === 0 ? (
          <div className="p-4 bg-slate-100 rounded-lg border border-slate-200 text-center text-sm text-slate-600">
            This order is currently <strong>{order.status}</strong>. As a terminal state in the
            workflow, it cannot be transitioned to another status.
          </div>
        ) : (
          <div className="space-y-2">
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
              Select New Status
            </label>
            <div className="space-y-2">
              {validNextStatuses.map((statusOption) => (
                <label
                  key={statusOption}
                  className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedStatus === statusOption
                      ? 'border-indigo-600 bg-indigo-50/50 ring-1 ring-indigo-600'
                      : 'border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <input
                      type="radio"
                      name="status"
                      value={statusOption}
                      checked={selectedStatus === statusOption}
                      onChange={() => setSelectedStatus(statusOption)}
                      className="text-indigo-600 focus:ring-indigo-500 h-4 w-4"
                    />
                    <span className="text-sm font-medium text-slate-900 capitalize">
                      {statusOption.replace('_', ' ')}
                    </span>
                  </div>
                  <StatusBadge status={statusOption} size="sm" />
                </label>
              ))}
            </div>
          </div>
        )}

        <div className="pt-4 border-t border-slate-100 flex items-center justify-end gap-2.5">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!selectedStatus || isSubmitting || validNextStatuses.length === 0}
            className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg shadow-xs transition-colors flex items-center gap-2"
          >
            {isSubmitting && <LoadingSpinner size="sm" />}
            <span>Confirm Update</span>
          </button>
        </div>
      </form>
    </Modal>
  );
};
