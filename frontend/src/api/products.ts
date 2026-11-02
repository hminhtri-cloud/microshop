import { request } from './client';
import type { Product, ProductInput, ProductPage } from './types';

export const productsApi = {
  list: (filters: { search?: string; category?: string; offset?: number } = {}, signal?: AbortSignal) => {
    const params = new URLSearchParams({ limit: '12', offset: String(filters.offset ?? 0) });
    if (filters.search) params.set('search', filters.search);
    if (filters.category) params.set('category', filters.category);
    return request<ProductPage>(`/products?${params}`, { signal }, false);
  },
  get: (id: number, signal?: AbortSignal) => request<Product>(`/products/${id}`, { signal }, false),
  sellerList: () => request<ProductPage>('/seller/products?limit=100'),
  create: (data: ProductInput) => request<Product>('/seller/products', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: ProductInput) => request<Product>(`/seller/products/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  setSellerVisibility: (id: number, status: 'active' | 'hidden') => request<Product>(
    `/seller/products/${id}/visibility`, { method: 'PATCH', body: JSON.stringify({ status }) },
  ),
  adminList: () => request<ProductPage>('/admin/products?limit=100'),
  setAdminVisibility: (id: number, status: 'active' | 'blocked') => request<Product>(
    `/admin/products/${id}/visibility`, { method: 'PATCH', body: JSON.stringify({ status }) },
  ),
};
