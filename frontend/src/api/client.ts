import type {
  ExtractResponse,
  Order,
  OrdersListResponse,
  OrderStatus,
  OrderStatusUpdateResponse,
  OrderModificationPayload,
  ModifyItemsResponse,
  ModifyMessageResponse,
  CatalogResponse,
  OrderStatsResponse,
  ReceiptResponse,
  ChatResponse,
  ChatSessionResponse,
} from './types';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = BASE_URL) {
    this.baseUrl = baseUrl;
  }

  public getBaseUrl(): string {
    return this.baseUrl;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...options.headers,
    };

    let response: Response;
    try {
      response = await fetch(url, {
        ...options,
        headers,
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Network error';
      throw new Error(
        `Unable to connect to backend at ${this.baseUrl}. Please ensure the FastAPI server is running. (${msg})`
      );
    }

    if (!response.ok) {
      let errorMessage = `Request failed with status ${response.status}`;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          if (Array.isArray(errorData.detail)) {
            errorMessage = errorData.detail
              .map((d: any) => (typeof d === 'string' ? d : d.msg || JSON.stringify(d)))
              .join(', ');
          } else if (typeof errorData.detail === 'string') {
            errorMessage = errorData.detail;
          } else {
            errorMessage = JSON.stringify(errorData.detail);
          }
        } else if (errorData.errors && Array.isArray(errorData.errors)) {
          errorMessage = errorData.errors.join(', ');
        } else if (errorData.message) {
          errorMessage = errorData.message;
        }
      } catch {
      }
      const error = new Error(errorMessage);
      (error as any).status = response.status;
      throw error;
    }

    return response.json() as Promise<T>;
  }

  /**
   * Process a customer message into an order, enquiry, or clarification request
   * POST /extract
   */
  async extractMessage(message: string): Promise<ExtractResponse> {
    return this.request<ExtractResponse>('/extract', {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  }

  /**
   * List all orders, optionally filtered by status or search keyword
   * GET /orders?status=...&search=...
   */
  async getOrders(status?: OrderStatus, search?: string): Promise<OrdersListResponse> {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (search) params.append('search', search);
    const queryString = params.toString() ? `?${params.toString()}` : '';
    return this.request<OrdersListResponse>(`/orders${queryString}`, {
      method: 'GET',
    });
  }

  /**
   * Get single order by order_id
   * GET /orders/{order_id}
   */
  async getOrderById(orderId: number): Promise<Order> {
    return this.request<Order>(`/orders/${orderId}`, {
      method: 'GET',
    });
  }

  /**
   * Update order status
   * PATCH /orders/{order_id}/status
   */
  async updateOrderStatus(orderId: number, status: OrderStatus): Promise<OrderStatusUpdateResponse> {
    return this.request<OrderStatusUpdateResponse>(`/orders/${orderId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  }

  /**
   * Modify order line items directly (structured items)
   * PATCH /orders/{order_id}/items
   */
  async updateOrderItems(
    orderId: number,
    payload: OrderModificationPayload
  ): Promise<ModifyItemsResponse> {
    return this.request<ModifyItemsResponse>(`/orders/${orderId}/items`, {
      method: 'PATCH',
      body: JSON.stringify({
        customer_message: payload.customer_message,
        items: payload.items,
        action: payload.action || 'add',
      }),
    });
  }

  /**
   * Modify order using a natural language customer message
   * PATCH /orders/{order_id}/modify-message
   */
  async modifyOrderFromMessage(
    orderId: number,
    message: string
  ): Promise<ModifyMessageResponse> {
    return this.request<ModifyMessageResponse>(`/orders/${orderId}/modify-message`, {
      method: 'PATCH',
      body: JSON.stringify({ message }),
    });
  }

  /**
   * Fetch product catalogue dynamically
   * GET /catalog
   */
  async getCatalog(): Promise<CatalogResponse> {
    return this.request<CatalogResponse>('/catalog', {
      method: 'GET',
    });
  }

  /**
   * Fetch aggregated analytics and operational KPIs
   * GET /orders/stats
   */
  async getOrderStats(): Promise<OrderStatsResponse> {
    return this.request<OrderStatsResponse>('/orders/stats', {
      method: 'GET',
    });
  }

  /**
   * Fetch formatted WhatsApp customer receipt
   * GET /orders/{order_id}/receipt
   */
  async getOrderReceipt(orderId: number): Promise<ReceiptResponse> {
    return this.request<ReceiptResponse>(`/orders/${orderId}/receipt`, {
      method: 'GET',
    });
  }

  /**
   * Send customer message in conversational chat-to-order flow
   * POST /chat
   */
  async sendChatMessage(sessionId: string | null, message: string): Promise<ChatResponse> {
    return this.request<ChatResponse>('/chat', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, message }),
    });
  }

  /**
   * Retrieve conversation history, draft cart, and session state
   * GET /chat/sessions/{session_id}
   */
  async getChatSession(sessionId: string): Promise<ChatSessionResponse> {
    return this.request<ChatSessionResponse>(`/chat/sessions/${sessionId}`, {
      method: 'GET',
    });
  }

  /**
   * Reset conversation draft cart and state
   * POST /chat/sessions/{session_id}/reset
   */
  async resetChatSession(sessionId: string): Promise<{ message: string; session: any }> {
    return this.request<{ message: string; session: any }>(`/chat/sessions/${sessionId}/reset`, {
      method: 'POST',
    });
  }
}

export const api = new ApiClient();
export default api;
