import React, { useState } from 'react';
import { Modal } from '../common/Modal';
import type { Order, OrderModificationPayload, StructuredItemInput } from '../../api/types';
import { AlertBanner } from '../common/AlertBanner';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { Sparkles, ListPlus, Plus, Trash2 } from 'lucide-react';
import api from '../../api/client';

interface OrderModifyModalProps {
  order: Order | null;
  isOpen: boolean;
  onClose: () => void;
  onOrderModified: () => void;
}

export const OrderModifyModal: React.FC<OrderModifyModalProps> = ({
  order,
  isOpen,
  onClose,
  onOrderModified,
}) => {
  const [activeTab, setActiveTab] = useState<'ai-message' | 'structured'>('ai-message');
  const [modificationMessage, setModificationMessage] = useState('');
  const [clarificationQuestion, setClarificationQuestion] = useState<string | null>(null);
  const [isSubmittingMessage, setIsSubmittingMessage] = useState(false);
  const [actionType, setActionType] = useState<'add' | 'replace'>('add');
  const [customerNote, setCustomerNote] = useState('');
  const [structuredItems, setStructuredItems] = useState<StructuredItemInput[]>([
    { product: 'murukku', quantity: 500, unit: 'g' },
  ]);
  const [isSubmittingItems, setIsSubmittingItems] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  if (!order) return null;

  const isPending = order.status === 'payment_pending';
  const handleMessageSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!modificationMessage.trim()) return;

    setIsSubmittingMessage(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const response = await api.modifyOrderFromMessage(order.order_id, modificationMessage.trim());

      if (response.needs_clarification) {
        setClarificationQuestion(response.message);
        setModificationMessage('');
      } else {
        setSuccessMessage(response.message || 'Order modified successfully.');
        setClarificationQuestion(null);
        setModificationMessage('');
        setTimeout(() => {
          onOrderModified();
          onClose();
        }, 1200);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to apply order modification message');
    } finally {
      setIsSubmittingMessage(false);
    }
  };
  const handleAddItem = () => {
    setStructuredItems([
      ...structuredItems,
      { product: 'murukku', quantity: 250, unit: 'g' },
    ]);
  };

  const handleRemoveItem = (index: number) => {
    setStructuredItems(structuredItems.filter((_, i) => i !== index));
  };

  const handleItemChange = (index: number, field: keyof StructuredItemInput, value: any) => {
    const updated = [...structuredItems];
    updated[index] = { ...updated[index], [field]: value };
    setStructuredItems(updated);
  };

  const handleStructuredSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (structuredItems.length === 0) {
      setError('Please provide at least one item.');
      return;
    }

    setIsSubmittingItems(true);
    setError(null);
    setSuccessMessage(null);

    const payload: OrderModificationPayload = {
      customer_message: customerNote.trim() || `Manual modification (${actionType})`,
      items: structuredItems.map((item) => ({
        product: item.product,
        quantity: Number(item.quantity),
        unit: item.unit,
      })),
      action: actionType,
    };

    try {
      const res = await api.updateOrderItems(order.order_id, payload);
      setSuccessMessage(res.message || 'Order items updated successfully.');
      setTimeout(() => {
        onOrderModified();
        onClose();
      }, 1200);
    } catch (err: any) {
      setError(err.message || 'Failed to modify order items.');
    } finally {
      setIsSubmittingItems(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Modify Order #${order.order_id}`}
      description="Update line items or apply customer modification messages"
      maxWidth="lg"
    >
      {!isPending ? (
        <div className="space-y-4">
          <AlertBanner
            type="warning"
            title="Modification Not Permitted"
            message={`Order #${order.order_id} is currently '${order.status}'. The backend business rules only permit modifying orders that are in 'payment_pending' status.`}
          />
          <div className="flex justify-end pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg"
            >
              Close
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-5">
          {}
          <div className="flex border-b border-slate-200">
            <button
              type="button"
              onClick={() => {
                setActiveTab('ai-message');
                setError(null);
                setSuccessMessage(null);
              }}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 -mb-px transition-colors ${
                activeTab === 'ai-message'
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <Sparkles size={14} />
              AI Natural Message
            </button>
            <button
              type="button"
              onClick={() => {
                setActiveTab('structured');
                setError(null);
                setSuccessMessage(null);
              }}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 -mb-px transition-colors ${
                activeTab === 'structured'
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <ListPlus size={14} />
              Structured Items Editor
            </button>
          </div>

          {error && <AlertBanner type="error" message={error} onDismiss={() => setError(null)} />}
          {successMessage && <AlertBanner type="success" message={successMessage} />}

          {}
          {activeTab === 'ai-message' && (
            <form onSubmit={handleMessageSubmit} className="space-y-4">
              <div className="text-xs text-slate-600">
                Presents the customer message to the backend LLM engine (
                <code className="text-indigo-600 font-mono">PATCH /orders/{order.order_id}/modify-message</code>
                ). The AI understands requests like &quot;add 500g murukku&quot; or &quot;laddu 250g podhum&quot;.
              </div>

              {clarificationQuestion && (
                <div className="p-3.5 bg-amber-50 rounded-lg border border-amber-200">
                  <div className="text-xs font-bold text-amber-800 flex items-center gap-1.5 mb-1">
                    <span>Clarification Needed:</span>
                  </div>
                  <p className="text-xs text-amber-900">{clarificationQuestion}</p>
                  <p className="text-[11px] text-amber-700 mt-1 italic">
                    Type your clarification answer below (e.g., &quot;500g&quot; or &quot;murukku&quot;).
                  </p>
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">
                  {clarificationQuestion ? 'Customer Clarification Response' : 'Customer Modification Message'}
                </label>
                <textarea
                  rows={3}
                  value={modificationMessage}
                  onChange={(e) => setModificationMessage(e.target.value)}
                  placeholder={
                    clarificationQuestion
                      ? 'e.g. 500g or 1kg'
                      : 'e.g. add 500g mixture, or laddu 250g podhum'
                  }
                  className="w-full text-xs font-sans rounded-lg border border-slate-300 p-2.5 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  required
                />
              </div>

              {}
              {!clarificationQuestion && (
                <div className="space-y-1">
                  <span className="text-[11px] font-medium text-slate-400">Quick suggestions:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {['add 500g mixture', 'add 1kg laddu', 'laddu 250g podhum'].map((text) => (
                      <button
                        key={text}
                        type="button"
                        onClick={() => setModificationMessage(text)}
                        className="text-[11px] px-2 py-0.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded transition-colors"
                      >
                        {text}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!modificationMessage.trim() || isSubmittingMessage}
                  className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded-lg shadow-xs flex items-center gap-2"
                >
                  {isSubmittingMessage && <LoadingSpinner size="sm" />}
                  <span>Apply Modification</span>
                </button>
              </div>
            </form>
          )}

          {}
          {activeTab === 'structured' && (
            <form onSubmit={handleStructuredSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Modification Action
                  </label>
                  <select
                    value={actionType}
                    onChange={(e) => setActionType(e.target.value as 'add' | 'replace')}
                    className="w-full text-xs rounded-lg border border-slate-300 p-2 bg-white"
                  >
                    <option value="add">Add to existing items</option>
                    <option value="replace">Replace all existing items</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Modification Note / Message
                  </label>
                  <input
                    type="text"
                    value={customerNote}
                    onChange={(e) => setCustomerNote(e.target.value)}
                    placeholder="e.g. Added via admin dashboard"
                    className="w-full text-xs rounded-lg border border-slate-300 p-2"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-700">Items to Apply</span>
                  <button
                    type="button"
                    onClick={handleAddItem}
                    className="text-xs text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1"
                  >
                    <Plus size={13} /> Add Item Row
                  </button>
                </div>

                <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                  {structuredItems.map((item, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2 p-2 bg-slate-50 border border-slate-200 rounded-lg"
                    >
                      <select
                        value={item.product}
                        onChange={(e) => handleItemChange(idx, 'product', e.target.value)}
                        className="text-xs rounded border border-slate-300 p-1.5 bg-white flex-1"
                      >
                        <option value="murukku">Murukku</option>
                        <option value="thattai">Thattai</option>
                        <option value="mixture">Mixture</option>
                        <option value="laddu">Laddu</option>
                      </select>

                      <input
                        type="number"
                        min="1"
                        step="any"
                        value={item.quantity}
                        onChange={(e) =>
                          handleItemChange(idx, 'quantity', parseFloat(e.target.value) || 0)
                        }
                        className="w-20 text-xs rounded border border-slate-300 p-1.5"
                        placeholder="Qty"
                        required
                      />

                      <select
                        value={item.unit}
                        onChange={(e) => handleItemChange(idx, 'unit', e.target.value)}
                        className="w-20 text-xs rounded border border-slate-300 p-1.5 bg-white"
                      >
                        <option value="g">g (grams)</option>
                        <option value="kg">kg (kilo)</option>
                      </select>

                      {structuredItems.length > 1 && (
                        <button
                          type="button"
                          onClick={() => handleRemoveItem(idx)}
                          className="p-1.5 text-slate-400 hover:text-rose-600 rounded transition-colors"
                          aria-label="Remove item"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingItems}
                  className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded-lg shadow-xs flex items-center gap-2"
                >
                  {isSubmittingItems && <LoadingSpinner size="sm" />}
                  <span>Save Changes</span>
                </button>
              </div>
            </form>
          )}
        </div>
      )}
    </Modal>
  );
};
