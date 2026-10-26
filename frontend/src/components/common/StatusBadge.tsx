import React from 'react';
import { Clock, CheckCircle2, XCircle } from 'lucide-react';
import type { OrderStatus } from '../../api/types';

interface StatusBadgeProps {
  status: OrderStatus;
  size?: 'sm' | 'md' | 'lg';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 gap-1',
    md: 'text-xs px-2.5 py-1 gap-1.5 font-medium',
    lg: 'text-sm px-3 py-1.5 gap-2 font-medium',
  };

  const iconSizes = {
    sm: 12,
    md: 14,
    lg: 16,
  };

  switch (status) {
    case 'payment_pending':
      return (
        <span
          className={`inline-flex items-center rounded-full border border-amber-200 bg-amber-50 text-amber-800 ${sizeClasses[size]}`}
          title="Payment is pending customer confirmation"
        >
          <Clock size={iconSizes[size]} className="text-amber-600 animate-pulse" />
          <span>Payment Pending</span>
        </span>
      );

    case 'confirmed':
      return (
        <span
          className={`inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 text-emerald-800 ${sizeClasses[size]}`}
          title="Order has been confirmed"
        >
          <CheckCircle2 size={iconSizes[size]} className="text-emerald-600" />
          <span>Confirmed</span>
        </span>
      );

    case 'cancelled':
      return (
        <span
          className={`inline-flex items-center rounded-full border border-rose-200 bg-rose-50 text-rose-800 ${sizeClasses[size]}`}
          title="Order is cancelled"
        >
          <XCircle size={iconSizes[size]} className="text-rose-600" />
          <span>Cancelled</span>
        </span>
      );

    default:
      return (
        <span
          className={`inline-flex items-center rounded-full border border-slate-200 bg-slate-100 text-slate-700 ${sizeClasses[size]}`}
        >
          <span>{status}</span>
        </span>
      );
  }
};
