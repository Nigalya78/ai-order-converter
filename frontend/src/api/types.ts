export type OrderStatus = 'payment_pending' | 'confirmed' | 'cancelled';

export interface OrderItem {
  product: string;
  quantity?: number | null;
  unit?: 'packet' | 'kg' | 'g' | null;
}

export interface OrderChange {
  action: 'add' | 'set_quantity' | 'remove';
  product?: string | null;
  quantity?: number | null;
  unit?: 'packet' | 'kg' | 'g' | null;
}

export type ExtractionIntent =
  | 'new_order'
  | 'modify_order'
  | 'product_enquiry'
  | 'cancel_order'
  | 'unclear';

export interface OrderExtraction {
  intent: ExtractionIntent;
  items: OrderItem[];
  needs_clarification: boolean;
  clarification_question?: string | null;
  changes: OrderChange[];
}

export interface ValidatedItem {
  product: string;
  variant?: string;
  quantity?: number | string;
  unit?: string;
  price: number;
}

export interface OrderProcessingResult {
  items: ValidatedItem[];
  errors: string[];
  total: number;
  valid: boolean;
}

export interface ProductPriceDetail {
  size: string;
  price: number;
}

export interface ExtractResponse {
  extraction: OrderExtraction;
  order?: OrderProcessingResult | null;
  order_id?: number | null;
  status?: OrderStatus | null;
  message?: string;
  product?: string;
  prices?: ProductPriceDetail[];
}

export interface Order {
  order_id: number;
  customer_message: string;
  items: ValidatedItem[];
  total: number;
  status: OrderStatus;
  created_at: string;
}

export interface OrdersListResponse {
  count: number;
  orders: Order[];
}

export interface OrderStatusUpdatePayload {
  status: OrderStatus;
}

export interface OrderStatusUpdateResponse {
  order_id: number;
  status: OrderStatus;
  message: string;
}

export interface StructuredItemInput {
  product: string;
  quantity: number;
  unit: 'kg' | 'g' | 'packet';
}

export interface OrderModificationPayload {
  customer_message: string;
  items: StructuredItemInput[];
  action?: 'add' | 'replace';
}

export interface ModifyItemsResponse {
  order_id: number;
  items: ValidatedItem[];
  total: number;
  message: string;
}

export interface ModifyMessagePayload {
  message: string;
}

export interface ModifyMessageResponse {
  order_id: number;
  needs_clarification?: boolean;
  message: string;
  changes?: OrderChange[];
  items?: ValidatedItem[];
  total?: number;
}

export interface ProductVariant {
  size: string;
  price: number;
}

export interface ProductCatalogItem {
  id: string;
  name: string;
  category: string;
  description: string;
  variants: ProductVariant[];
}

export interface CatalogResponse {
  products: ProductCatalogItem[];
}

export interface TopProductStat {
  product: string;
  count: number;
}

export interface OrderStatsResponse {
  total_orders: number;
  pending_orders: number;
  confirmed_orders: number;
  cancelled_orders: number;
  total_revenue: number;
  confirmed_revenue: number;
  avg_order_value: number;
  top_products: TopProductStat[];
}

export interface ReceiptResponse {
  order_id: number;
  receipt: string;
  whatsapp_url: string;
}

export interface CartItem {
  product: string;
  variant?: string;
  quantity: number;
  unit: string;
  price: number;
}

export interface CartState {
  items: CartItem[];
  total: number;
}

export interface ChatRequest {
  session_id?: string | null;
  message: string;
}

export interface ChatResponse {
  session_id: string;
  reply: string;
  intent: string;
  cart: CartState;
  pending_confirmation: boolean;
  order_id?: number | null;
  status?: OrderStatus | null;
}

export interface ChatMessage {
  id?: number;
  session_id: string;
  role: 'customer' | 'assistant';
  content: string;
  metadata?: any;
  created_at?: string;
}

export interface ChatSessionResponse {
  session_id: string;
  cart: CartState;
  pending_confirmation: boolean;
  created_order_id?: number | null;
  messages: ChatMessage[];
}

export interface ApiError {
  message: string;
  status?: number;
  detail?: string | string[];
}
