import React, { useState, useEffect } from 'react';
import type { Order } from '../../api/types';
import { StatusBadge } from '../common/StatusBadge';
import api from '../../api/client';
import {
  ArrowLeft,
  Edit3,
  CheckCircle2,
  MessageSquare,
  Clock,
  Share2,
  Copy,
  Check,
  Printer,
  ExternalLink,
} from 'lucide-react';

interface OrderDetailProps {
  order: Order;
  onBack: () => void;
  onOpenStatusModal: () => void;
  onOpenModifyModal: () => void;
  onShowToast?: (title: string, message?: string, type?: 'success' | 'error' | 'info') => void;
}

export const OrderDetail: React.FC<OrderDetailProps> = ({
  order,
  onBack,
  onOpenStatusModal,
  onOpenModifyModal,
  onShowToast,
}) => {
  const [receiptText, setReceiptText] = useState<string>('');
  const [whatsappUrl, setWhatsappUrl] = useState<string>('');
  const [copied, setCopied] = useState(false);

  const isPending = order.status === 'payment_pending';

  useEffect(() => {
    api
      .getOrderReceipt(order.order_id)
      .then((res) => {
        setReceiptText(res.receipt);
        setWhatsappUrl(res.whatsapp_url);
      })
      .catch(() => {
      });
  }, [order]);

  const handleCopyReceipt = () => {
    if (!receiptText) return;
    navigator.clipboard.writeText(receiptText);
    setCopied(true);
    if (onShowToast) {
      onShowToast('Receipt Copied', 'WhatsApp message copied to clipboard', 'success');
    }
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePrint = () => {
    window.print();
  };

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      return d.toLocaleDateString('en-IN', {
        weekday: 'short',
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  const messageLines = (order.customer_message || '').split('\n').filter(Boolean);

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {}
      <div className="hidden print:block border-b-2 border-slate-900 pb-4 mb-6">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-xl font-black tracking-tight">SNACK HOUSE ORDERS</h1>
            <p className="text-xs text-slate-500">Order Packing Slip &amp; Dispatch Note</p>
          </div>
          <div className="text-right">
            <span className="font-mono font-bold text-lg">#{order.order_id}</span>
            <p className="text-xs text-slate-500">{formatDate(order.created_at)}</p>
          </div>
        </div>
      </div>

      {}
      <div className="flex flex-wrap items-center justify-between gap-3 no-print">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white border border-slate-200 px-3.5 py-1.5 rounded-xl shadow-2xs hover:bg-slate-50 transition-colors"
        >
          <ArrowLeft size={14} />
          <span>Back to Orders</span>
        </button>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handlePrint}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 hover:text-slate-900 bg-white border border-slate-300 px-3.5 py-1.5 rounded-xl hover:bg-slate-50 transition-colors shadow-2xs"
            title="Print packing slip or invoice"
          >
            <Printer size={13} />
            <span>Print Slip</span>
          </button>

          {isPending && (
            <button
              type="button"
              onClick={onOpenModifyModal}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-indigo-700 bg-indigo-50 border border-indigo-200 hover:bg-indigo-100 rounded-xl transition-colors shadow-2xs"
            >
              <Edit3 size={13} />
              <span>Modify Order</span>
            </button>
          )}

          <button
            type="button"
            onClick={onOpenStatusModal}
            className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-xl shadow-xs transition-colors"
          >
            <span>Change Status</span>
          </button>
        </div>
      </div>

      {}
      <div className="bg-white rounded-2xl border border-slate-200/90 shadow-xs overflow-hidden print-card">
        {}
        <div className="p-6 border-b border-slate-100 bg-slate-50/50 flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold text-slate-900 tracking-tight font-mono">
                Order #{order.order_id}
              </h2>
              <StatusBadge status={order.status} size="md" />
            </div>
            <p className="text-xs text-slate-500 mt-1 flex items-center gap-1.5">
              <Clock size={13} /> Placed on {formatDate(order.created_at)}
            </p>
          </div>

          <div className="text-right">
            <span className="text-xs uppercase tracking-wider text-slate-500 font-semibold block">
              Total Amount
            </span>
            <span className="text-2xl font-black text-slate-900 tracking-tight">
              ₹{order.total?.toFixed(0) || '0'}
            </span>
          </div>
        </div>

        {}
        <div className="p-6 space-y-6">
          {}
          <div className="space-y-2">
            <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
              <MessageSquare size={14} className="text-slate-400" />
              Customer Request &amp; Audit Trail
            </h3>
            <div className="bg-slate-50 rounded-xl border border-slate-200 p-4 space-y-2">
              {messageLines.map((line, idx) => {
                const isMod = line.toLowerCase().startsWith('modification:');
                return (
                  <div
                    key={idx}
                    className={`text-xs ${
                      isMod
                        ? 'p-2.5 bg-indigo-50/90 border border-indigo-100 rounded-lg text-indigo-950 font-medium'
                        : 'text-slate-800 leading-relaxed font-sans'
                    }`}
                  >
                    {line}
                  </div>
                );
              })}
            </div>
          </div>

          {}
          <div className="space-y-2">
            <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Order Line Items ({order.items?.length || 0})
            </h3>
            <div className="border border-slate-200 rounded-xl overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs min-w-[500px]">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold text-[10px] uppercase tracking-wider">
                    <th className="py-2.5 px-4 w-12">#</th>
                    <th className="py-2.5 px-4">Product Name</th>
                    <th className="py-2.5 px-4">Variant / Size</th>
                    <th className="py-2.5 px-4">Quantity</th>
                    <th className="py-2.5 px-4">Unit</th>
                    <th className="py-2.5 px-4 text-right">Unit Price</th>
                    <th className="py-2.5 px-4 text-right">Subtotal</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {order.items && order.items.length > 0 ? (
                    order.items.map((item, index) => {
                      const displayVariant =
                        item.variant ||
                        (typeof item.quantity === 'number' && item.unit
                          ? `${item.quantity}${item.unit}`
                          : item.quantity || '—');
                      const displayQty =
                        typeof item.quantity === 'number' ? item.quantity : '—';
                      const displayUnit = item.unit || '—';

                      return (
                        <tr key={index} className="hover:bg-slate-50/80">
                          <td className="py-3 px-4 font-mono text-slate-400">{index + 1}</td>
                          <td className="py-3 px-4 font-bold text-slate-900 capitalize">
                            {item.product}
                          </td>
                          <td className="py-3 px-4">
                            <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-semibold text-[11px]">
                              {displayVariant}
                            </span>
                          </td>
                          <td className="py-3 px-4 font-medium">{displayQty}</td>
                          <td className="py-3 px-4 font-mono text-slate-600">{displayUnit}</td>
                          <td className="py-3 px-4 text-right font-medium text-slate-600">
                            ₹{item.price}
                          </td>
                          <td className="py-3 px-4 text-right font-bold text-slate-900">
                            ₹{item.price}
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan={7} className="py-6 text-center text-slate-400">
                        No items found in this order.
                      </td>
                    </tr>
                  )}
                </tbody>
                <tfoot>
                  <tr className="bg-slate-50/90 border-t border-slate-200 font-bold text-slate-900 text-xs">
                    <td colSpan={6} className="py-3.5 px-4 text-right uppercase tracking-wider">
                      Order Grand Total
                    </td>
                    <td className="py-3.5 px-4 text-right text-base font-black text-indigo-600">
                      ₹{order.total?.toFixed(0) || '0'}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>

          {}
          {receiptText && (
            <div className="bg-emerald-50/50 border border-emerald-200/80 rounded-xl p-4 sm:p-5 space-y-3 no-print">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Share2 size={16} className="text-emerald-700" />
                  <span className="text-xs font-bold text-emerald-950 uppercase tracking-wider">
                    Customer WhatsApp Receipt
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleCopyReceipt}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-emerald-900 bg-white border border-emerald-300 rounded-lg hover:bg-emerald-100/60 transition-colors shadow-2xs"
                  >
                    {copied ? (
                      <>
                        <Check size={13} className="text-emerald-600" />
                        <span>Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy size={13} />
                        <span>Copy Receipt</span>
                      </>
                    )}
                  </button>

                  {whatsappUrl && (
                    <a
                      href={whatsappUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg transition-colors shadow-2xs"
                    >
                      <span>Share on WhatsApp</span>
                      <ExternalLink size={12} />
                    </a>
                  )}
                </div>
              </div>

              <pre className="p-3.5 bg-white rounded-lg border border-emerald-200/60 font-mono text-xs text-slate-800 whitespace-pre-wrap break-words leading-relaxed shadow-2xs">
                {receiptText}
              </pre>
            </div>
          )}

          {}
          <div className="p-4 bg-blue-50/70 border border-blue-200/80 rounded-xl text-xs text-blue-900 flex items-start gap-2.5 no-print">
            <CheckCircle2 size={16} className="text-blue-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold">Lifecycle State Machine: </span>
              {order.status === 'payment_pending' && (
                <span>
                  This order is currently pending payment. It can be modified or transitioned to
                  &lsquo;confirmed&rsquo; or &lsquo;cancelled&rsquo;.
                </span>
              )}
              {order.status === 'confirmed' && (
                <span>
                  This order has been confirmed. It can only be transitioned to
                  &lsquo;cancelled&rsquo; if the customer withdraws. Modifications are locked.
                </span>
              )}
              {order.status === 'cancelled' && (
                <span>
                  This order is cancelled. In accordance with database validation rules, cancelled
                  orders cannot be reopened or edited.
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
