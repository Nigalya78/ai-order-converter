import React, { useState, useEffect } from 'react';
import type { Order, OrderStatsResponse } from '../api/types';
import { StatCard } from '../components/dashboard/StatCard';
import { StatusBadge } from '../components/common/StatusBadge';
import api from '../api/client';
import {
  ShoppingBag,
  Clock,
  CheckCircle2,
  Sparkles,
  ArrowRight,
  ExternalLink,
  Award,
  TrendingUp,
} from 'lucide-react';

interface DashboardPageProps {
  orders: Order[];
  isLoading: boolean;
  onNavigateToOrders: () => void;
  onNavigateToAI: () => void;
  onSelectOrder: (orderId: number) => void;
  onOpenStatusModal?: (order: Order) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  orders,
  onNavigateToOrders,
  onNavigateToAI,
  onSelectOrder,
}) => {
  const [stats, setStats] = useState<OrderStatsResponse | null>(null);

  useEffect(() => {
    api
      .getOrderStats()
      .then((data) => setStats(data))
      .catch(() => {
      });
  }, [orders]);
  const totalOrders = stats?.total_orders ?? orders.length;
  const pendingOrders =
    stats?.pending_orders ?? orders.filter((o) => o.status === 'payment_pending').length;
  const confirmedOrders =
    stats?.confirmed_orders ?? orders.filter((o) => o.status === 'confirmed').length;
  const cancelledOrders =
    stats?.cancelled_orders ?? orders.filter((o) => o.status === 'cancelled').length;

  const totalRevenue =
    stats?.total_revenue ??
    orders.filter((o) => o.status !== 'cancelled').reduce((sum, o) => sum + (o.total || 0), 0);

  const avgOrderValue =
    stats?.avg_order_value ??
    (totalOrders > 0 ? Math.round(totalRevenue / (totalOrders - cancelledOrders || 1)) : 0);

  const topProducts = stats?.top_products ?? [];

  const recentOrders = orders.slice(0, 5);

  const pendingPercentage = totalOrders > 0 ? (pendingOrders / totalOrders) * 100 : 0;
  const confirmedPercentage = totalOrders > 0 ? (confirmedOrders / totalOrders) * 100 : 0;
  const cancelledPercentage = totalOrders > 0 ? (cancelledOrders / totalOrders) * 100 : 0;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 rounded-2xl p-6 sm:p-7 text-white shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6 border border-slate-800">
        <div className="space-y-1.5 max-w-2xl">
          <div className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-400/30 mb-1">
            <Sparkles size={12} />
            <span>AI-Powered Conversion System</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
            Customer Message-to-Order Pipeline
          </h2>
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
            FastAPI and Ollama Llama 3.1 normalize informal chat messages, extract line items,
            and store orders directly in Neon PostgreSQL with zero manual data entry.
          </p>
        </div>

        <button
          type="button"
          onClick={onNavigateToAI}
          className="inline-flex items-center justify-center gap-2 px-5 py-3 text-xs sm:text-sm font-semibold text-slate-950 bg-white hover:bg-slate-100 active:bg-slate-200 rounded-xl shadow-md transition-all shrink-0 hover:scale-[1.02]"
        >
          <Sparkles size={16} className="text-indigo-600" />
          <span>Launch AI Converter</span>
        </button>
      </div>

      {}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Orders"
          value={totalOrders}
          subtitle="Orders logged in PostgreSQL"
          icon={ShoppingBag}
          variant="indigo"
          onClick={onNavigateToOrders}
        />
        <StatCard
          label="Payment Pending"
          value={pendingOrders}
          subtitle="Awaiting customer transfer"
          icon={Clock}
          variant="amber"
          onClick={onNavigateToOrders}
        />
        <StatCard
          label="Confirmed Revenue"
          value={`₹${(stats?.confirmed_revenue ?? 0).toFixed(0)}`}
          subtitle={`${confirmedOrders} paid & confirmed orders`}
          icon={CheckCircle2}
          variant="emerald"
          onClick={onNavigateToOrders}
        />
        <StatCard
          label="Avg Order Value"
          value={`₹${avgOrderValue.toFixed(0)}`}
          subtitle="Per active order basket"
          icon={TrendingUp}
          variant="default"
        />
      </div>

      {}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-700 uppercase tracking-wider">
                Order Pipeline Breakdown
              </span>
              <span className="text-slate-500 font-medium">
                {confirmedOrders} confirmed · {pendingOrders} pending · {cancelledOrders} cancelled
              </span>
            </div>

            <div className="h-3 w-full bg-slate-100 rounded-full overflow-hidden flex mt-3">
              <div
                style={{ width: `${confirmedPercentage}%` }}
                className="bg-emerald-500 transition-all"
                title={`Confirmed: ${confirmedOrders}`}
              />
              <div
                style={{ width: `${pendingPercentage}%` }}
                className="bg-amber-400 transition-all"
                title={`Pending: ${pendingOrders}`}
              />
              <div
                style={{ width: `${cancelledPercentage}%` }}
                className="bg-rose-400 transition-all"
                title={`Cancelled: ${cancelledOrders}`}
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2 sm:gap-3 pt-2 border-t border-slate-100 text-xs">
            <div className="p-2 sm:p-2.5 rounded-xl bg-emerald-50/60 border border-emerald-100 text-center">
              <span className="text-[10px] sm:text-[11px] text-emerald-700 font-semibold block truncate">Confirmed</span>
              <span className="text-sm sm:text-base font-bold text-emerald-900">{confirmedOrders}</span>
              <span className="text-[9px] sm:text-[10px] text-emerald-600 block">
                ({confirmedPercentage.toFixed(0)}%)
              </span>
            </div>
            <div className="p-2 sm:p-2.5 rounded-xl bg-amber-50/60 border border-amber-100 text-center">
              <span className="text-[10px] sm:text-[11px] text-amber-700 font-semibold block truncate">Pending</span>
              <span className="text-sm sm:text-base font-bold text-amber-900">{pendingOrders}</span>
              <span className="text-[9px] sm:text-[10px] text-amber-600 block">
                ({pendingPercentage.toFixed(0)}%)
              </span>
            </div>
            <div className="p-2 sm:p-2.5 rounded-xl bg-rose-50/60 border border-rose-100 text-center">
              <span className="text-[10px] sm:text-[11px] text-rose-700 font-semibold block truncate">Cancelled</span>
              <span className="text-sm sm:text-base font-bold text-rose-900">{cancelledOrders}</span>
              <span className="text-[9px] sm:text-[10px] text-rose-600 block">
                ({cancelledPercentage.toFixed(0)}%)
              </span>
            </div>
          </div>
        </div>

        {}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <span className="text-xs font-semibold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                <Award size={15} className="text-amber-500" />
                Popular Snacks
              </span>
              <span className="text-[11px] text-slate-400">Order Frequency</span>
            </div>

            <div className="divide-y divide-slate-100 mt-2 text-xs">
              {topProducts.length === 0 ? (
                <div className="py-6 text-center text-slate-400">No product orders recorded yet.</div>
              ) : (
                topProducts.slice(0, 4).map((p, idx) => (
                  <div key={p.product} className="py-2.5 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-slate-400 font-bold text-xs">
                        #{idx + 1}
                      </span>
                      <span className="font-semibold text-slate-800 capitalize">
                        {p.product}
                      </span>
                    </div>
                    <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-bold text-[11px]">
                      {p.count} ordered
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="text-[11px] text-slate-400 pt-3 border-t border-slate-100 text-center">
            Derived in real time from Neon PostgreSQL
          </div>
        </div>
      </div>

      {}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900 tracking-tight">Recent Orders</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Latest orders processed through the message extraction endpoint
            </p>
          </div>

          <button
            type="button"
            onClick={onNavigateToOrders}
            className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 transition-colors"
          >
            <span>View All Orders</span>
            <ArrowRight size={13} />
          </button>
        </div>

        {recentOrders.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-xs">
            No orders found in the database. Use the AI Order Converter to create your first order.
          </div>
        ) : (
          <div className="divide-y divide-slate-100 text-xs">
            {recentOrders.map((order) => (
              <div
                key={order.order_id}
                onClick={() => onSelectOrder(order.order_id)}
                className="p-4 hover:bg-slate-50/80 transition-colors cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div className="flex items-start sm:items-center gap-3">
                  <span className="font-mono font-bold text-slate-900 text-sm">
                    #{order.order_id}
                  </span>
                  <div>
                    <p className="font-medium text-slate-800 line-clamp-1">
                      {order.customer_message}
                    </p>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      {order.items?.length || 0} line item(s) ·{' '}
                      {new Date(order.created_at).toLocaleDateString('en-IN', {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3 self-end sm:self-center">
                  <span className="font-bold text-slate-900 text-sm">₹{order.total}</span>
                  <StatusBadge status={order.status} size="sm" />
                  <ExternalLink size={13} className="text-slate-400" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
