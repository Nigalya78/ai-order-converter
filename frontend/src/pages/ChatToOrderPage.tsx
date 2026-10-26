import React, { useState, useEffect, useRef } from 'react';
import type { ChatMessage, CartState, ChatResponse } from '../api/types';
import api from '../api/client';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import {
  Send,
  Sparkles,
  Bot,
  User,
  ShoppingBag,
  Trash2,
  CheckCircle2,
  Check,
  Copy,
  RotateCcw,
  Package,
  ArrowRight,
  X,
} from 'lucide-react';

interface ChatToOrderPageProps {
  onNavigateToOrder: (orderId: number) => void;
  onShowToast?: (title: string, message?: string, type?: 'success' | 'error' | 'info') => void;
}

const STORAGE_SESSION_KEY = 'snack_chat_session_id';

export const ChatToOrderPage: React.FC<ChatToOrderPageProps> = ({
  onNavigateToOrder,
  onShowToast,
}) => {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [cart, setCart] = useState<CartState>({ items: [], total: 0 });
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [copiedOrderId, setCopiedOrderId] = useState<number | null>(null);
  const [isCartOpenMobile, setIsCartOpenMobile] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);
  const handleStartNewSession = () => {
    localStorage.removeItem(STORAGE_SESSION_KEY);
    setSessionId(null);
    setCart({ items: [], total: 0 });
    setMessages([
      {
        session_id: 'new',
        role: 'assistant',
        content:
          'Vanakkam! Welcome to Snack House Assistant. I can help you explore our traditional South Indian snacks, check prices, build your order, and confirm it anytime.\n\nWhat would you like to try today?',
      },
    ]);
    setIsInitializing(false);
  };

  useEffect(() => {
    const savedSessionId = localStorage.getItem(STORAGE_SESSION_KEY);
    if (savedSessionId) {
      setSessionId(savedSessionId);
      api
        .getChatSession(savedSessionId)
        .then((res) => {
          setCart(res.cart || { items: [], total: 0 });
          if (res.messages && res.messages.length > 0) {
            setMessages(res.messages);
          } else {
            setMessages([
              {
                session_id: savedSessionId,
                role: 'assistant',
                content:
                  'Vanakkam! Welcome to Snack House Assistant. I can help you explore our traditional South Indian snacks, check prices, build your order, and confirm it anytime.\n\nWhat would you like to try today?',
              },
            ]);
          }
        })
        .catch(() => {
          handleStartNewSession();
        })
        .finally(() => {
          setIsInitializing(false);
        });
    } else {
      handleStartNewSession();
    }
  }, []);

  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend ?? inputValue).trim();
    if (!text || isLoading) return;

    setInputValue('');
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
    }
    const tempUserMsg: ChatMessage = {
      session_id: sessionId || 'temp',
      role: 'customer',
      content: text,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setIsLoading(true);

    try {
      const response: ChatResponse = await api.sendChatMessage(sessionId, text);
      if (response.session_id) {
        setSessionId(response.session_id);
        localStorage.setItem(STORAGE_SESSION_KEY, response.session_id);
      }
      if (response.cart) {
        setCart(response.cart);
      }
      const assistantMsg: ChatMessage = {
        session_id: response.session_id,
        role: 'assistant',
        content: response.reply,
        metadata: {
          intent: response.intent,
          order_id: response.order_id,
          status: response.status,
          cart: response.cart,
        },
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      if (response.order_id && response.intent === 'order_placed') {
        if (onShowToast) {
          onShowToast('Order Placed!', `Order #${response.order_id} recorded in Neon PostgreSQL`, 'success');
        }
      }
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        session_id: sessionId || 'error',
        role: 'assistant',
        content: `Sorry, I encountered an error: ${err.message || 'Unable to connect to the backend server.'}. Please verify FastAPI is running.`,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetCart = async () => {
    if (!sessionId) {
      setCart({ items: [], total: 0 });
      return;
    }
    try {
      await api.resetChatSession(sessionId);
      setCart({ items: [], total: 0 });
      if (onShowToast) {
        onShowToast('Cart Reset', 'Draft items cleared', 'info');
      }
    } catch {
    }
  };

  const handleCopyReceipt = (orderId: number, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedOrderId(orderId);
    if (onShowToast) {
      onShowToast('Receipt Copied', 'Receipt copied to clipboard', 'success');
    }
    setTimeout(() => setCopiedOrderId(null), 2000);
  };

  const samplePrompts = [
    'What snacks are available?',
    'What is the price of 500g murukku?',
    'Add 500g murukku and 250g mixture',
    'Add 250g laddu too',
    'What is my total?',
    'Place the order',
  ];

  return (
    <div className="flex flex-col lg:flex-row gap-4 sm:gap-6 max-w-7xl mx-auto h-[calc(100dvh-5rem)] lg:h-[calc(100vh-6.5rem)] min-h-[520px]">
      {/* Left / Main: Chat Thread Container */}
      <div className="flex-1 bg-white rounded-2xl border border-slate-200/90 shadow-xs flex flex-col overflow-hidden">
        {/* Chat Header */}
        <div className="p-3.5 sm:p-4 border-b border-slate-100 bg-slate-50/70 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-violet-500 flex items-center justify-center text-white shadow-xs shrink-0">
              <Bot size={20} />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-slate-900 truncate">
                  Snack House AI Assistant
                </h2>
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full shrink-0">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  Online
                </span>
              </div>
              <p className="text-[11px] text-slate-500 truncate">
                {sessionId ? `Session #${sessionId.substring(0, 8)}` : 'Interactive Ordering Engine'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Mobile Cart Trigger */}
            <button
              type="button"
              onClick={() => setIsCartOpenMobile(!isCartOpenMobile)}
              className="lg:hidden relative p-2 text-slate-600 hover:text-indigo-600 bg-slate-100 hover:bg-slate-200 rounded-xl transition-colors"
              title="View Draft Cart"
            >
              <ShoppingBag size={16} />
              {cart.items.length > 0 && (
                <span className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-indigo-600 text-white font-bold text-[9px] flex items-center justify-center">
                  {cart.items.length}
                </span>
              )}
            </button>

            <button
              type="button"
              onClick={handleStartNewSession}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-xl transition-all shadow-2xs"
              title="Start a fresh conversation"
            >
              <RotateCcw size={12} />
              <span className="hidden sm:inline">New Chat</span>
            </button>
          </div>
        </div>

        {/* Scrollable Chat Messages Thread */}
        <div className="flex-1 p-4 sm:p-5 overflow-y-auto space-y-4">
          {isInitializing ? (
            <div className="h-full flex items-center justify-center">
              <LoadingSpinner size="md" />
            </div>
          ) : (
            messages.map((msg, index) => {
              const isAssistant = msg.role === 'assistant';
              const orderId = msg.metadata?.order_id;
              const isOrderPlaced = msg.metadata?.intent === 'order_placed';

              return (
                <div
                  key={index}
                  className={`flex gap-3 max-w-[85%] sm:max-w-[78%] ${
                    isAssistant ? 'mr-auto items-start' : 'ml-auto flex-row-reverse items-end'
                  }`}
                >
                  {/* Avatar */}
                  <div
                    className={`h-7 w-7 rounded-lg flex items-center justify-center shrink-0 text-white text-xs ${
                      isAssistant
                        ? 'bg-indigo-600'
                        : 'bg-slate-800'
                    }`}
                  >
                    {isAssistant ? <Sparkles size={14} /> : <User size={14} />}
                  </div>

                  {/* Message Bubble */}
                  <div className="space-y-2.5 min-w-0">
                    <div
                      className={`p-3.5 sm:p-4 rounded-2xl text-xs sm:text-[13px] leading-relaxed shadow-2xs ${
                        isAssistant
                          ? 'bg-slate-100/90 text-slate-800 rounded-tl-xs border border-slate-200/60'
                          : 'bg-indigo-600 text-white rounded-br-xs'
                      }`}
                    >
                      <div className="whitespace-pre-wrap font-sans">{msg.content}</div>
                    </div>

                    {/* Order Placed Special Card */}
                    {isOrderPlaced && orderId && (
                      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3.5 space-y-2.5 animate-fadeIn">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-1.5 text-emerald-950 font-bold text-xs">
                            <CheckCircle2 size={16} className="text-emerald-600" />
                            <span>PostgreSQL Order #{orderId}</span>
                          </div>
                          <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                            Payment Pending
                          </span>
                        </div>

                        <p className="text-[11px] text-emerald-800">
                          Order has been logged in the operational database. You can manage status, print slips, or share the receipt on WhatsApp.
                        </p>

                        <div className="flex items-center gap-2 pt-1 border-t border-emerald-200/60">
                          <button
                            type="button"
                            onClick={() => onNavigateToOrder(orderId)}
                            className="inline-flex items-center gap-1 px-3 py-1 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg transition-colors shadow-2xs"
                          >
                            <span>Open Order #{orderId}</span>
                            <ArrowRight size={12} />
                          </button>

                          <button
                            type="button"
                            onClick={() => handleCopyReceipt(orderId, msg.content)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-emerald-900 bg-white border border-emerald-300 rounded-lg hover:bg-emerald-100/50 transition-colors"
                          >
                            {copiedOrderId === orderId ? (
                              <>
                                <Check size={12} className="text-emerald-600" />
                                <span>Copied</span>
                              </>
                            ) : (
                              <>
                                <Copy size={12} />
                                <span>Copy Receipt</span>
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}

          {isLoading && (
            <div className="flex gap-3 mr-auto items-start max-w-[80%]">
              <div className="h-7 w-7 rounded-lg bg-indigo-600 flex items-center justify-center shrink-0 text-white">
                <Sparkles size={14} />
              </div>
              <div className="p-3 rounded-2xl bg-slate-100 rounded-tl-xs border border-slate-200 flex items-center gap-2">
                <LoadingSpinner size="sm" />
                <span className="text-xs text-slate-500 font-medium">Assistant is thinking...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Quick Suggestion Chips */}
        <div className="px-3.5 py-2 border-t border-slate-100 bg-slate-50/50 overflow-x-auto scrollbar-none flex items-center gap-1.5 shrink-0">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider shrink-0 mr-1">
            Presets:
          </span>
          {samplePrompts.map((prompt, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleSendMessage(prompt)}
              disabled={isLoading}
              className="text-[11px] whitespace-nowrap px-2.5 py-1 rounded-lg bg-white border border-slate-200 text-slate-700 hover:text-indigo-600 hover:border-indigo-300 hover:bg-indigo-50/50 transition-colors shadow-2xs shrink-0 disabled:opacity-50"
            >
              {prompt}
            </button>
          ))}
        </div>

        {/* Message Input Box */}
        <div className="p-3 sm:p-4 border-t border-slate-200/80 bg-white shrink-0">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center gap-2"
          >
            <textarea
              ref={inputRef}
              rows={1}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              placeholder="Ask for snacks, enquire prices, add items, or type 'Place order'..."
              className="flex-1 max-h-32 min-h-[42px] py-2 px-3.5 text-xs sm:text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 resize-none transition-all"
            />

            <button
              type="submit"
              disabled={isLoading || !inputValue.trim()}
              className="h-[42px] px-4 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 disabled:opacity-50 disabled:cursor-not-allowed shadow-xs transition-all flex items-center gap-1.5 shrink-0"
              aria-label="Send message"
            >
              {isLoading ? <LoadingSpinner size="sm" /> : <Send size={15} />}
              <span className="hidden sm:inline">Send</span>
            </button>
          </form>
        </div>
      </div>

      {/* Mobile Cart Backdrop Overlay */}
      {isCartOpenMobile && (
        <div
          className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-40 lg:hidden animate-fadeIn"
          onClick={() => setIsCartOpenMobile(false)}
          aria-hidden="true"
        />
      )}

      {/* Right / Side: Live Draft Cart Panel */}
      <div
        className={`fixed inset-y-0 right-0 z-50 w-full sm:w-96 max-w-[90vw] lg:static lg:z-auto lg:w-80 shrink-0 bg-white lg:rounded-2xl border-l lg:border border-slate-200/90 shadow-2xl lg:shadow-xs flex flex-col overflow-hidden transition-transform duration-200 ease-in-out ${
          isCartOpenMobile ? 'translate-x-0' : 'translate-x-full lg:translate-x-0 hidden lg:flex'
        }`}
      >
        <div className="p-4 border-b border-slate-100 bg-slate-50/80 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <ShoppingBag size={18} className="text-indigo-600" />
            <h3 className="text-sm font-bold text-slate-900">Live Draft Cart</h3>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
              {cart.items.length} {cart.items.length === 1 ? 'item' : 'items'}
            </span>
            <button
              type="button"
              onClick={() => setIsCartOpenMobile(false)}
              className="lg:hidden p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors"
              aria-label="Close cart drawer"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Cart Line Items */}
        <div className="flex-1 p-4 overflow-y-auto space-y-2.5">
          {cart.items.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-400 space-y-2">
              <div className="h-12 w-12 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-center text-slate-400">
                <Package size={22} />
              </div>
              <p className="text-xs font-semibold text-slate-600">Cart is empty</p>
              <p className="text-[11px] text-slate-400 max-w-xs">
                Ask the assistant to add snacks like &quot;Add 500g murukku&quot; or &quot;250g mixture&quot;.
              </p>
            </div>
          ) : (
            cart.items.map((item, idx) => (
              <div
                key={idx}
                className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between text-xs hover:border-slate-300 transition-colors"
              >
                <div>
                  <h4 className="font-bold text-slate-900 capitalize">{item.product}</h4>
                  <span className="text-[11px] text-slate-500 font-medium">
                    {item.variant || `${item.quantity}${item.unit}`}
                  </span>
                </div>
                <div className="text-right">
                  <span className="font-black text-slate-900 text-xs">₹{item.price}</span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Cart Total & Order Placement Action */}
        <div className="p-4 border-t border-slate-200/90 bg-slate-50/70 space-y-3 shrink-0">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              Calculated Total
            </span>
            <span className="text-lg font-black text-slate-900">₹{cart.total?.toFixed(0) || '0'}</span>
          </div>

          <div className="space-y-2">
            <button
              type="button"
              disabled={cart.items.length === 0 || isLoading}
              onClick={() => {
                handleSendMessage('Yes, place the order');
                setIsCartOpenMobile(false);
              }}
              className="w-full py-2.5 px-4 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 disabled:opacity-40 disabled:cursor-not-allowed shadow-xs transition-all flex items-center justify-center gap-2"
            >
              <CheckCircle2 size={15} />
              <span>Confirm &amp; Place Order</span>
            </button>

            {cart.items.length > 0 && (
              <button
                type="button"
                onClick={handleResetCart}
                className="w-full py-1.5 px-3 rounded-lg text-[11px] font-semibold text-slate-500 hover:text-rose-600 hover:bg-rose-50 transition-colors flex items-center justify-center gap-1.5"
              >
                <Trash2 size={13} />
                <span>Clear Draft Cart</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
export default ChatToOrderPage;
