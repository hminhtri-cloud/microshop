import { request } from './client';
import type { ApplicationPage, ReviewAction, SellerApplication, User } from './types';

export const authApi = {
  me: () => request<User>('/auth/me'),
  login: (email: string, password: string) => request<{ access_token: string }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  }, false),
  register: (username: string, email: string, password: string) => request<User>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, email, password }),
  }, false),
  application: () => request<SellerApplication>('/seller/application'),
  apply: (shop_name: string, description: string) => request<SellerApplication>('/seller/application', {
    method: 'POST',
    body: JSON.stringify({ shop_name, description }),
  }),
  applications: (status: string, offset: number, signal?: AbortSignal) => request<ApplicationPage>(
    `/admin/seller-applications?limit=10&offset=${offset}${status ? `&status=${status}` : ''}`,
    { signal },
  ),
  review: (id: number, action: ReviewAction, note: string) => request<SellerApplication>(
    `/admin/seller-applications/${id}/review`,
    { method: 'POST', body: JSON.stringify({ action, note }) },
  ),
};
