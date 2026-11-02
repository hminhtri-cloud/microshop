import { request } from './client';
import type {
  MockPaymentInput,
  Order,
  OrderCreateInput,
  OrderPage,
  SellerOrder,
  SellerOrderPage,
} from './types';

export const ordersApi = {
  create: (data: OrderCreateInput, idempotencyKey: string) => request<Order>('/orders', {
    method: 'POST',
    headers: { 'Idempotency-Key': idempotencyKey },
    body: JSON.stringify(data),
  }),
  list: (offset = 0, limit = 20, signal?: AbortSignal) => request<OrderPage>(
    `/orders?offset=${offset}&limit=${limit}`, { signal },
  ),
  get: (id: number, signal?: AbortSignal) => request<Order>(`/orders/${id}`, { signal }),
  cancel: (id: number) => request<Order>(`/orders/${id}/cancel`, { method: 'POST' }),
  mockPayment: (id: number, data: MockPaymentInput) => request<Order>(`/orders/${id}/mock-payment`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  sellerList: (offset = 0, limit = 20, signal?: AbortSignal) => request<SellerOrderPage>(
    `/seller/orders?offset=${offset}&limit=${limit}`, { signal },
  ),
  sellerGet: (id: number, signal?: AbortSignal) => request<SellerOrder>(`/seller/orders/${id}`, { signal }),
  sellerSetStatus: (id: number, status: SellerOrder['status']) => request<SellerOrder>(
    `/seller/orders/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status }) },
  ),
  adminList: (offset = 0, limit = 20, signal?: AbortSignal) => request<OrderPage>(
    `/admin/orders?offset=${offset}&limit=${limit}`, { signal },
  ),
  adminGet: (id: number, signal?: AbortSignal) => request<Order>(`/admin/orders/${id}`, { signal }),
};
