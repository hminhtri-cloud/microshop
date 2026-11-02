export type Role = 'customer' | 'seller' | 'admin';
export type SellerStatus = 'pending' | 'approved' | 'rejected' | 'suspended';
export type ReviewAction = 'approve' | 'reject' | 'suspend';

export interface User {
  id: number;
  username: string;
  email: string;
  role: Role;
  created_at: string;
}

export interface SellerApplication {
  id: number;
  user_id: number;
  shop_name: string;
  description: string;
  status: SellerStatus;
  review_note: string | null;
  reviewed_by: number | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApplicationPage {
  items: SellerApplication[];
  total: number;
  offset: number;
  limit: number;
}

export type ProductStatus = 'active' | 'hidden' | 'blocked';

export interface Product {
  id: number;
  seller_id: number;
  name: string;
  description: string;
  category: string;
  price: string;
  quantity: number;
  image_url: string | null;
  status: ProductStatus;
  created_at: string;
  updated_at: string;
}

export interface ProductPage {
  items: Product[];
  total: number;
  offset: number;
  limit: number;
}

export interface ProductInput {
  name: string;
  description: string;
  category: string;
  price: string;
  quantity: number;
  image_url: string | null;
}

export interface ShippingInfo {
  receiver_name: string;
  phone: string;
  address: string;
  note?: string | null;
}

export interface OrderItemInput {
  product_id: number;
  quantity: number;
}

export interface OrderCreateInput {
  items: OrderItemInput[];
  shipping: ShippingInfo;
}

export type PaymentStatus = 'unpaid' | 'paid' | 'failed' | 'cancelled';
export type SellerOrderStatus = 'pending' | 'confirmed' | 'shipping' | 'completed' | 'cancelled';

export interface OrderItem {
  id: number;
  product_id: number;
  product_name_snapshot: string;
  unit_price_snapshot: string;
  quantity: number;
  subtotal: string;
}

export interface SellerOrder {
  id: number;
  seller_id: number;
  status: SellerOrderStatus;
  subtotal: string;
  items: OrderItem[];
}

export interface Order {
  id: number;
  customer_id: number;
  total_amount: string;
  payment_status: PaymentStatus;
  status: string;
  shipping: ShippingInfo;
  seller_orders: SellerOrder[];
  created_at: string;
  updated_at?: string;
}

export interface OrderSummary {
  id: number;
  total_amount: string;
  payment_status: PaymentStatus;
  status: string;
  created_at: string;
}

export interface OrderPage {
  items: OrderSummary[];
  total: number;
  offset: number;
  limit: number;
}

export interface MockPaymentInput {
  outcome: 'success' | 'failure';
}

export interface SellerOrderPage {
  items: SellerOrder[];
  total: number;
  offset: number;
  limit: number;
}
