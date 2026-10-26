import React, { useState, useEffect } from 'react';
import type { ExtractResponse } from '../api/types';
import api from '../api/client';
import { StatusBadge } from '../components/common/StatusBadge';
import { AlertBanner } from '../components/common/AlertBanner';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import {
  Sparkles,
  Send,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  ShoppingBag,
  ArrowRight,
  Info,
  Package,
  Copy,
  Check,
  Zap,
} from 'lucide-react';

interface MessageToOrderPageProps {
  onOrderCreated: (orderId: number) => void;
  initialMessage?: string;
}

export const MessageToOrderPage: React.FC<MessageToOrderPageProps> = ({
  onOrderCreated,
  initialMessage = '',
}) => {
  const [customerMessage, setCustomerMessage] = useState(initialMessage);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ExtractResponse | null>(null);
  const [elapsedMs, setElapsedMs] = useState<number | null>(null);
  const [copiedReceipt, setCopiedReceipt] = useState(false);

  useEffect(() => {
    if (initialMessage) {
      setCustomerMessage(initialMessage);
    }
  }, [initialMessage]);

  const samplePrompts = [
    {
      title: 'Standard Multi-Item',
      message: 'I want 500g murukku and 1kg laddu',
      tag: 'English',
    },
    {
      title: 'Tanglish Order',
      message: 'murukku 500g venum',
      tag: 'Tanglish',
    },
    {
      title: 'Colloquial Fractions',
      message: 'I need half kg laddu and kaal kg thattai',
      tag: 'Fractions',
    },
    {
      title: 'Price Enquiry',
      message: 'What is the price of thattai 500g?',
      tag: 'Enquiry',
    },
    {
      title: 'Spelling Variation',
      message: '250g laddoo and 500g muruku',
      tag: 'Fuzzy',
    },
    {
      title: 'Missing Quantity',
      message: 'I need some laddu',
      tag: 'Clarify',
    },
  ];

  const handleExtract = async (messageToSubmit?: string) => {
    const text = messageToSubmit ?? customerMessage;
    if (!text.trim()) {
      setError('Please enter a customer message to process.');
      return;
    }

    setIsLoading(true);
    setError(null);
    setResult(null);
    const start = performance.now();

    try {
      const response = await api.extractMessage(text.trim());
      setResult(response);
      setElapsedMs(Math.round(performance.now() - start));
    } catch (err: any) {
      setError(err.message || 'Failed to process message with AI backend.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleApplyClarification = (clarificationText: string) => {
    const combined = `${customerMessage}. Customer clarification: ${clarificationText}`;
    setCustomerMessage(combined);
    handleExtract(combined);
  };

  const generateQuickReceipt = (res: ExtractResponse) => {
    if (!res.order_id || !res.order) return '';
    const items = res.order.items
      .map(
        (it) =>
          `• ${it.product.toUpperCase()} (${it.variant || `${it.quantity}${it.unit}`}) - ₹${it.price}`
      )
      .join('\n');

    return `📦 *Snack Order Confirmation*\nOrder ID: *#${res.order_id}*\nStatus: *⏳ Payment Pending*\n\n*Items:*\n${items}\n\n*Grand Total: ₹${res.order.total}*\n\nThank you for ordering with us! 🙏`;
  };

  const handleCopyReceipt = () => {
    if (!result) return;
    const text = generateQuickReceipt(result);
    navigator.clipboard.writeText(text);
    setCopiedReceipt(true);
    setTimeout(() => setCopiedReceipt(false), 2000);
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {}
      <div className="bg-gradient-to-r from-indigo-950 via-slate-900 to-indigo-900 text-white rounded-2xl p-6 sm:p-8 shadow-md border border-indigo-900/50">
        <div className="flex items-start gap-4">
          <div className="h-12 w-12 rounded-xl bg-indigo-500/20 backdrop-blur-xs flex items-center justify-center shrink-0 border border-indigo-400/30">
            <Sparkles size={24} className="text-indigo-300" />
          </div>
          <div>
            <h2 className="text-xl font-bold tracking-tight">AI Message-to-Order Conversion</h2>
            <p className="mt-1 text-xs sm:text-sm text-indigo-200/90 leading-relaxed max-w-2xl">
              Handles informal WhatsApp, SMS, and chat messages in English, Tanglish, and Tamil
              fractions. Powered by a high-speed hybrid regex normalizer with Ollama Llama 3.1
              fallback.
            </p>
          </div>
        </div>
      </div>

      {}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-4">
        <div>
          <div className="flex items-center justify-between mb-2">
            <label
              htmlFor="customer-message-input"
              className="text-xs font-semibold text-slate-700 uppercase tracking-wider flex items-center gap-1.5"
            >
              <span>Customer Message</span>
              <span className="text-indigo-600 font-mono text-[10px] lowercase">
                (POST /extract)
              </span>
            </label>
            <span className="text-[11px] text-slate-400">
              Supports fractions (&ldquo;half kg&rdquo;, &ldquo;kaal kg&rdquo;), Tanglish &amp; typos
            </span>
          </div>

          <textarea
            id="customer-message-input"
            rows={4}
            value={customerMessage}
            onChange={(e) => setCustomerMessage(e.target.value)}
            placeholder="e.g. I need half kg murukku and 1kg laddu, or thattai 500g evvalavu?"
            className="w-full text-sm font-sans rounded-xl border border-slate-300 p-3.5 focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600 transition-colors"
          />
        </div>

        {}
        <div className="space-y-1.5">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            One-Click Test Presets:
          </span>
          <div className="flex flex-wrap gap-2">
            {samplePrompts.map((sample, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  setCustomerMessage(sample.message);
                  handleExtract(sample.message);
                }}
                className="text-xs px-2.5 py-1.5 bg-slate-50 hover:bg-indigo-50 border border-slate-200 hover:border-indigo-200 rounded-lg text-slate-700 hover:text-indigo-900 transition-colors flex items-center gap-1.5 text-left"
              >
                <span className="text-[10px] font-mono px-1 py-0.2 rounded bg-slate-200/60 text-slate-600">
                  {sample.tag}
                </span>
                <span className="font-medium">{sample.title}</span>
              </button>
            ))}
          </div>
        </div>

        {}
        <div className="flex items-center justify-between pt-2">
          <button
            type="button"
            onClick={() => {
              setCustomerMessage('');
              setResult(null);
              setError(null);
              setElapsedMs(null);
            }}
            className="text-xs text-slate-500 hover:text-slate-800 font-medium"
          >
            Clear input
          </button>

          <button
            type="button"
            disabled={isLoading || !customerMessage.trim()}
            onClick={() => handleExtract()}
            className="inline-flex items-center gap-2 px-5 py-2.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg shadow-xs transition-colors"
          >
            {isLoading ? (
              <>
                <LoadingSpinner size="sm" />
                <span>Processing with AI...</span>
              </>
            ) : (
              <>
                <Send size={14} />
                <span>Extract &amp; Process Order</span>
              </>
            )}
          </button>
        </div>
      </div>

      {}
      {error && <AlertBanner type="error" message={error} onDismiss={() => setError(null)} />}

      {}
      {result && (
        <div className="space-y-6 animate-fadeIn">
          {}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Detected Intent:
                </span>
                <span className="px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-slate-100 text-slate-800 border border-slate-200 font-mono">
                  {result.extraction?.intent || 'unknown'}
                </span>
                {elapsedMs !== null && (
                  <span className="inline-flex items-center gap-1 text-[11px] text-slate-500 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded-full">
                    <Zap size={11} className="text-amber-500" />
                    {elapsedMs}ms
                  </span>
                )}
              </div>

              {result.order_id && (
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-slate-600">Created Order ID:</span>
                  <span className="font-mono font-bold text-sm text-indigo-600">
                  </span>
                  {result.status && <StatusBadge status={result.status} size="sm" />}
                </div>
              )}
            </div>

            {}
            {result.message && (
              <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-800 flex items-start gap-2.5">
                <Info size={16} className="text-indigo-600 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold text-slate-900">Backend Response Message: </span>
                  <span>{result.message}</span>
                </div>
              </div>
            )}

            {}
            {result.order && result.order.valid && (
              <div className="space-y-4 pt-2">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                    <CheckCircle2 size={16} className="text-emerald-600" />
                    Validated Line Items
                  </h4>
                  {result.order_id && (
                    <button
                      type="button"
                      onClick={() => onOrderCreated(result.order_id!)}
                      className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
                    >
                      <span>Open Full Order View</span>
                      <ArrowRight size={13} />
                    </button>
                  )}
                </div>

                <div className="border border-slate-200 rounded-xl overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs min-w-[420px]">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold text-[11px] uppercase tracking-wider">
                        <th className="py-2.5 px-4">Product</th>
                        <th className="py-2.5 px-4">Variant / Size</th>
                        <th className="py-2.5 px-4">Quantity</th>
                        <th className="py-2.5 px-4">Unit</th>
                        <th className="py-2.5 px-4 text-right">Price</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-slate-700">
                      {result.order.items.map((item, idx) => (
                        <tr key={idx} className="hover:bg-slate-50/80">
                          <td className="py-2.5 px-4 font-semibold text-slate-900 capitalize">
                            {item.product}
                          </td>
                          <td className="py-2.5 px-4">
                            <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-medium text-[11px]">
                              {item.variant || `${item.quantity}${item.unit}`}
                            </span>
                          </td>
                          <td className="py-2.5 px-4">{item.quantity}</td>
                          <td className="py-2.5 px-4 font-mono">{item.unit}</td>
                          <td className="py-2.5 px-4 text-right font-medium">₹{item.price}</td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr className="bg-slate-50/80 border-t border-slate-200 font-semibold text-slate-900 text-xs">
                        <td colSpan={4} className="py-2.5 px-4 text-right uppercase tracking-wider">
                          Calculated Total
                        </td>
                        <td className="py-2.5 px-4 text-right text-sm font-bold text-emerald-600">
                          ₹{result.order.total}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>

                {}
                {result.order_id && (
                  <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="text-xs font-bold text-emerald-950">
                          Order #{result.order_id} Logged to PostgreSQL
                        </p>
                        <p className="text-[11px] text-emerald-700 mt-0.5">
                          Status initialized to payment_pending. Ready for customer receipt dispatch.
                        </p>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={handleCopyReceipt}
                          className="px-3 py-1.5 text-xs font-semibold text-emerald-900 bg-white border border-emerald-300 rounded-lg hover:bg-emerald-100/60 transition-colors flex items-center gap-1.5"
                        >
                          {copiedReceipt ? (
                            <>
                              <Check size={13} className="text-emerald-600" />
                              <span>Copied!</span>
                            </>
                          ) : (
                            <>
                              <Copy size={13} />
                              <span>Copy WhatsApp Receipt</span>
                            </>
                          )}
                        </button>

                        <button
                          type="button"
                          onClick={() => onOrderCreated(result.order_id!)}
                          className="px-3.5 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow-xs transition-colors flex items-center gap-1.5"
                        >
                          <ShoppingBag size={13} />
                          <span>Manage Order #{result.order_id}</span>
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {}
            {result.order && !result.order.valid && result.order.errors.length > 0 && (
              <div className="space-y-3 pt-2">
                <AlertBanner
                  type="warning"
                  title="Order Validation Issues"
                  message={
                    <div className="space-y-1.5">
                      <p>
                        The backend parsed the message but encountered item validation errors:
                      </p>
                      <ul className="list-disc list-inside space-y-0.5 text-xs font-medium">
                        {result.order.errors.map((errText, i) => (
                          <li key={i}>{errText}</li>
                        ))}
                      </ul>
                    </div>
                  }
                />
              </div>
            )}

            {}
            {(result.extraction?.needs_clarification ||
              result.extraction?.clarification_question) && (
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl space-y-3">
                <div className="flex items-center gap-2 text-amber-900 font-semibold text-xs uppercase tracking-wider">
                  <HelpCircle size={16} className="text-amber-600" />
                  <span>Clarification Required by Assistant</span>
                </div>
                <p className="text-xs text-amber-950 font-medium">
                  {result.extraction?.clarification_question ||
                    result.message ||
                    'Please specify the quantity or package size.'}
                </p>

                <div className="pt-2 border-t border-amber-200/60">
                  <span className="text-[11px] text-amber-800 font-medium block mb-1.5">
                    Quick Clarification Responses:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {['250g', '500g', '1kg'].map((size) => (
                      <button
                        key={size}
                        type="button"
                        onClick={() => handleApplyClarification(size)}
                        className="text-xs px-2.5 py-1 bg-white hover:bg-amber-100 border border-amber-300 rounded text-amber-900 font-medium transition-colors"
                      >
                        Reply &ldquo;{size}&rdquo;
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {}
            {result.extraction?.intent === 'product_enquiry' && (
              <div className="space-y-3 pt-2">
                <div className="flex items-center gap-2">
                  <Package size={16} className="text-indigo-600" />
                  <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                    Catalog Price Enquiry for: {result.product || 'Product'}
                  </span>
                </div>

                {result.prices && result.prices.length > 0 ? (
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                    {result.prices.map((p, i) => (
                      <div
                        key={i}
                        className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-center"
                      >
                        <span className="text-xs font-semibold text-slate-500 block">{p.size}</span>
                        <span className="text-base font-bold text-indigo-700">₹{p.price}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 italic">No price details configured.</p>
                )}
              </div>
            )}

            {}
            {result.extraction?.intent === 'cancel_order' && (
              <div className="p-4 bg-slate-100 border border-slate-200 rounded-xl space-y-2">
                <div className="flex items-center gap-2 text-slate-800 font-semibold text-xs uppercase tracking-wider">
                  <AlertTriangle size={15} className="text-amber-500" />
                  <span>Cancellation Request</span>
                </div>
                <p className="text-xs text-slate-700 leading-relaxed">
                  {result.message ||
                    'Cancellation request detected. Please navigate to the Orders list to locate and cancel the specific order.'}
                </p>
              </div>
            )}

            {}
            <details className="pt-2 text-xs text-slate-500 border-t border-slate-100">
              <summary className="cursor-pointer font-medium hover:text-slate-800 select-none">
                View Raw Schema Extraction Payload
              </summary>
              <pre className="mt-2 p-3 bg-slate-900 text-slate-200 rounded-lg font-mono text-[11px] overflow-x-auto">
                {JSON.stringify(result, null, 2)}
              </pre>
            </details>
          </div>
        </div>
      )}
    </div>
  );
};
