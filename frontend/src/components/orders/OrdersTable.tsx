import React, { useState, useMemo } from 'react';
import type { Order, OrderStatus } from '../../api/types';
import { StatusBadge } from '../common/StatusBadge';
import { Search, Eye, ArrowUpDown, MessageSquare, X, Copy, Check } from 'lucide-react';

interface OrdersTableProps {
  orders: Order[];
  onSelectOrder: (orderId: number) => void;
  onOpenStatusModal: (order: Order) => void;
  onOpenModifyModal: (order: Order) => void;
  onNewOrderClick?: () => void;
  isLoading?: boolean;
}

export const OrdersTable: React.FC<OrdersTableProps> = ({
  orders,
  onSelectOrder,
  onOpenStatusModal,
  onOpenModifyModal,
  onNewOrderClick,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | OrderStatus>('all');
  const [sortDirection, setSortDirection] = useState<'desc' | 'asc'>('desc');
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const handleCopyId = (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    navigator.clipboard.writeText(id.toString());
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  const formatItemsSummary = (items: Order['items']) => {
    if (!items || items.length === 0) return 'No items recorded';
    return items
      .map((it) => {
        const size =
          it.variant ||
          (typeof it.quantity === 'number' && it.unit
            ? `${it.quantity}${it.unit}`
            : it.quantity || '');
        return `${it.product}${size ? ` (${size})` : ''}`;
      })
      .join(', ');
  };

  const filteredOrders = useMemo(() => {
    let result = [...orders];

    if (statusFilter !== 'all') {
      result = result.filter((o) => o.status === statusFilter);
    }

    if (searchTerm.trim()) {
      const query = searchTerm.toLowerCase();
      result = result.filter((o) => {
        const idMatch = o.order_id.toString().includes(query);
        const msgMatch = (o.customer_message || '').toLowerCase().includes(query);
        const itemMatch = (o.items || []).some((it) =>
          (it.product || '').toLowerCase().includes(query)
        );
        return idMatch || msgMatch || itemMatch;
      });
    }

    result.sort((a, b) => {
      const diff = b.order_id - a.order_id;
      return sortDirection === 'desc' ? diff : -diff;
    });

    return result;
  }, [orders, statusFilter, searchTerm, sortDirection]);

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      return d.toLocaleDateString('en-IN', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-xs overflow-hidden">
      {}
      <div className="p-4 sm:p-5 border-b border-slate-200/80 flex flex-col md:flex-row md:items-center justify-between gap-3.5 bg-slate-50/50">
        {}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 scrollbar-none">
          {(
            [
              { id: 'all', label: 'All Orders' },
              { id: 'payment_pending', label: 'Payment Pending' },
              { id: 'confirmed', label: 'Confirmed' },
              { id: 'cancelled', label: 'Cancelled' },
            ] as const
          ).map((tab) => {
            const count =
              tab.id === 'all'
                ? orders.length
                : orders.filter((o) => o.status === tab.id).length;
            const isActive = statusFilter === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setStatusFilter(tab.id)}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all duration-150 flex items-center gap-1.5 ${
                  isActive
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'text-slate-600 hover:bg-slate-200/70 hover:text-slate-900'
                }`}
              >
                <span>{tab.label}</span>
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                    isActive ? 'bg-indigo-700 text-white' : 'bg-slate-200 text-slate-700'
                  }`}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {}
        <div className="flex items-center gap-2">
          <div className="relative flex-1 md:w-64">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
            />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by ID, snack, message..."
              className="w-full pl-9 pr-8 py-1.5 text-xs bg-white border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all placeholder:text-slate-400"
            />
            {searchTerm && (
              <button
                type="button"
                onClick={() => setSearchTerm('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-0.5"
                aria-label="Clear search"
              >
                <X size={13} />
              </button>
            )}
          </div>

          <button
            type="button"
            onClick={() => setSortDirection((prev) => (prev === 'desc' ? 'asc' : 'desc'))}
            className="p-1.5 text-slate-600 hover:text-slate-900 border border-slate-300 rounded-xl bg-white hover:bg-slate-50 transition-colors shadow-2xs"
            title={`Sort order: ${sortDirection === 'desc' ? 'Newest first' : 'Oldest first'}`}
          >
            <ArrowUpDown size={14} />
          </button>
        </div>
      </div>

      {/* Mobile Card View (< md) */}
      <div className="block md:hidden divide-y divide-slate-100">
        {filteredOrders.length === 0 ? (
          <div className="py-12 px-4 text-center">
            <div className="flex flex-col items-center justify-center text-slate-400 space-y-2.5">
              <div className="h-12 w-12 rounded-2xl bg-slate-100 flex items-center justify-center text-slate-400">
                <MessageSquare size={24} />
              </div>
              <p className="text-sm font-bold text-slate-700">No matching orders found</p>
              <p className="text-xs text-slate-400 max-w-sm">
                {searchTerm
                  ? `No orders matching "${searchTerm}". Try another keyword or clear the search filter.`
                  : 'No orders have been recorded in this category yet.'}
              </p>
              {onNewOrderClick && (
                <button
                  type="button"
                  onClick={onNewOrderClick}
                  className="mt-2 px-3.5 py-1.5 text-xs font-semibold text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition-colors"
                >
                  Create an order via AI
                </button>
              )}
            </div>
          </div>
        ) : (
          filteredOrders.map((order) => {
            const isPending = order.status === 'payment_pending';
            return (
              <div
                key={order.order_id}
                onClick={() => onSelectOrder(order.order_id)}
                className="p-4 hover:bg-indigo-50/30 transition-colors cursor-pointer space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono font-bold text-slate-900 text-sm">
                      #{order.order_id}
                    </span>
                    <button
                      type="button"
                      onClick={(e) => handleCopyId(e, order.order_id)}
                      className="text-slate-400 hover:text-slate-700 transition-colors p-1"
                      title="Copy Order ID"
                      aria-label={`Copy order ID ${order.order_id}`}
                    >
                      {copiedId === order.order_id ? (
                        <Check size={13} className="text-emerald-600" />
                      ) : (
                        <Copy size={13} />
                      )}
                    </button>
                  </div>
                  <StatusBadge status={order.status} size="sm" />
                </div>

                <div>
                  <p className="text-xs font-medium text-slate-800 line-clamp-2">
                    &ldquo;{order.customer_message}&rdquo;
                  </p>
                  <p className="text-[11px] text-slate-500 mt-1">
                    {formatItemsSummary(order.items)}
                  </p>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs">
                  <div>
                    <span className="text-[10px] text-slate-400 block">{formatDate(order.created_at)}</span>
                    <span className="font-black text-slate-900 text-sm">₹{order.total?.toFixed(0) || '0'}</span>
                  </div>

                  <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                    <button
                      type="button"
                      onClick={() => onSelectOrder(order.order_id)}
                      className="p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                      title="View order details"
                      aria-label="View details"
                    >
                      <Eye size={15} />
                    </button>

                    <button
                      type="button"
                      onClick={() => onOpenStatusModal(order)}
                      className="px-2.5 py-1 text-[11px] font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors shadow-2xs"
                    >
                      Status
                    </button>

                    {isPending && (
                      <button
                        type="button"
                        onClick={() => onOpenModifyModal(order)}
                        className="px-2.5 py-1 text-[11px] font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition-colors shadow-2xs"
                      >
                        Modify
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Desktop / Tablet Table View (>= md) */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs min-w-[700px]">
          <thead>
            <tr className="border-b border-slate-200/80 bg-slate-50/70 text-slate-600 font-bold uppercase tracking-wider text-[10px]">
              <th className="py-3 px-4 w-24">Order ID</th>
              <th className="py-3 px-4">Customer Request</th>
              <th className="py-3 px-4">Line Items</th>
              <th className="py-3 px-4 w-24">Total</th>
              <th className="py-3 px-4 w-36">Status</th>
              <th className="py-3 px-4 w-36">Date</th>
              <th className="py-3 px-4 text-right w-40">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-slate-700">
            {filteredOrders.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-14 text-center">
                  <div className="flex flex-col items-center justify-center text-slate-400 space-y-2.5">
                    <div className="h-12 w-12 rounded-2xl bg-slate-100 flex items-center justify-center text-slate-400">
                      <MessageSquare size={24} />
                    </div>
                    <p className="text-sm font-bold text-slate-700">No matching orders found</p>
                    <p className="text-xs text-slate-400 max-w-sm">
                      {searchTerm
                        ? `No orders matching "${searchTerm}". Try another keyword or clear the search filter.`
                        : 'No orders have been recorded in this category yet.'}
                    </p>
                    {onNewOrderClick && (
                      <button
                        type="button"
                        onClick={onNewOrderClick}
                        className="mt-2 px-3.5 py-1.5 text-xs font-semibold text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition-colors"
                      >
                        Create an order via AI
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ) : (
              filteredOrders.map((order) => {
                const isPending = order.status === 'payment_pending';
                return (
                  <tr
                    key={order.order_id}
                    className="hover:bg-indigo-50/40 transition-colors group cursor-pointer"
                    onClick={() => onSelectOrder(order.order_id)}
                  >
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono font-bold text-slate-900">
                          #{order.order_id}
                        </span>
                        <button
                          type="button"
                          onClick={(e) => handleCopyId(e, order.order_id)}
                          className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-slate-700 transition-opacity p-0.5"
                          title="Copy Order ID"
                        >
                          {copiedId === order.order_id ? (
                            <Check size={11} className="text-emerald-600" />
                          ) : (
                            <Copy size={11} />
                          )}
                        </button>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 max-w-xs">
                      <div
                        className="truncate text-slate-800 font-medium"
                        title={order.customer_message}
                      >
                        {order.customer_message}
                      </div>
                    </td>

                    <td className="py-3.5 px-4 max-w-xs">
                      <div
                        className="truncate text-slate-600"
                        title={formatItemsSummary(order.items)}
                      >
                        {formatItemsSummary(order.items)}
                      </div>
                    </td>

                    <td className="py-3.5 px-4 font-bold text-slate-900">
                      ₹{order.total?.toFixed(0) || '0'}
                    </td>

                    <td className="py-3.5 px-4">
                      <StatusBadge status={order.status} size="sm" />
                    </td>

                    <td className="py-3.5 px-4 text-slate-500 whitespace-nowrap text-[11px]">
                      {formatDate(order.created_at)}
                    </td>

                    <td
                      className="py-3.5 px-4 text-right"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div className="inline-flex items-center gap-1.5 justify-end">
                        <button
                          type="button"
                          onClick={() => onSelectOrder(order.order_id)}
                          className="p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                          title="View order details"
                        >
                          <Eye size={15} />
                        </button>

                        <button
                          type="button"
                          onClick={() => onOpenStatusModal(order)}
                          className="px-2.5 py-1 text-[11px] font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors shadow-2xs"
                          title="Update Status"
                        >
                          Status
                        </button>

                        {isPending && (
                          <button
                            type="button"
                            onClick={() => onOpenModifyModal(order)}
                            className="px-2.5 py-1 text-[11px] font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition-colors shadow-2xs"
                            title="Modify order"
                          >
                            Modify
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {}
      <div className="p-3.5 bg-slate-50 border-t border-slate-200 text-xs text-slate-500 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <span>
          Showing <strong>{filteredOrders.length}</strong> of <strong>{orders.length}</strong> total
          orders
        </span>
        <span className="text-[11px] text-slate-400">Click any order to view full audit trail</span>
      </div>
    </div>
  );
};
