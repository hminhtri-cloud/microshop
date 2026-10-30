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

const TOKEN_KEY = 'microshop.access-token';
export const session = {
  get: () => sessionStorage.getItem(TOKEN_KEY),
  set: (value: string) => sessionStorage.setItem(TOKEN_KEY, value),
  clear: () => sessionStorage.removeItem(TOKEN_KEY),
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

const messages: Record<string, string> = {
  'Invalid email or password': 'Email hoặc mật khẩu chưa đúng.',
  'Invalid or expired access token': 'Phiên đăng nhập đã hết hạn. Anh/chị vui lòng đăng nhập lại.',
  'Email already registered': 'Email này đã được đăng ký.',
  'Username already taken': 'Tên người dùng đã được sử dụng.',
  'Username or email already registered': 'Tên người dùng hoặc email đã được đăng ký.',
  'Insufficient permissions': 'Tài khoản không có quyền thực hiện thao tác này.',
  'Invalid seller status transition': 'Trạng thái hồ sơ đã thay đổi. Vui lòng tải lại danh sách.',
  'An application already exists; contact admin if suspended': 'Hồ sơ đã tồn tại. Nếu bị tạm ngưng, vui lòng liên hệ quản trị viên.',
  'An application already exists': 'Hồ sơ đăng ký đã tồn tại.',
  'Product is blocked by an administrator': 'Sản phẩm đang bị quản trị viên khóa. Vui lòng liên hệ quản trị viên.',
  'Product not found': 'Sản phẩm không còn hiển thị hoặc đã bị gỡ.',
};

export async function request<T>(path: string, options: RequestInit = {}, authenticated = true): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body) headers.set('Content-Type', 'application/json');
  const token = authenticated ? session.get() : null;
  if (token) headers.set('Authorization', `Bearer ${token}`);
  let response: Response;
  try {
    response = await fetch(`/api${path}`, { ...options, headers, signal: options.signal ?? AbortSignal.timeout(15000) });
  } catch (error) {
    if (options.signal?.aborted) throw error;
    throw new ApiError(0, 'Không kết nối được máy chủ. Kiểm tra backend và thử lại.');
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && token) {
      session.clear();
      window.dispatchEvent(new Event('microshop:unauthorized'));
    }
    const detail = data?.detail;
    const text = typeof detail === 'string'
      ? (messages[detail] || detail)
      : Array.isArray(detail)
        ? detail.map((item: { loc?: string[]; msg?: string }) => `${item.loc?.slice(1).join('.') || 'Dữ liệu'}: ${item.msg || 'Không hợp lệ'}`).join(' · ')
        : 'Máy chủ gặp lỗi. Vui lòng thử lại sau.';
    throw new ApiError(response.status, text);
  }
  return data as T;
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Đã có lỗi xảy ra. Vui lòng thử lại.';
}

export const api = {
  me: () => request<User>('/auth/me'),
  login: (email: string, password: string) => request<{ access_token: string }>('/auth/login', {
    method: 'POST', body: JSON.stringify({ email, password }),
  }, false),
  register: (username: string, email: string, password: string) => request<User>('/auth/register', {
    method: 'POST', body: JSON.stringify({ username, email, password }),
  }, false),
  application: () => request<SellerApplication>('/seller/application'),
  apply: (shop_name: string, description: string) => request<SellerApplication>('/seller/application', {
    method: 'POST', body: JSON.stringify({ shop_name, description }),
  }),
  applications: (status: string, offset: number, signal?: AbortSignal) => request<ApplicationPage>(
    `/admin/seller-applications?limit=10&offset=${offset}${status ? `&status=${status}` : ''}`, { signal },
  ),
  review: (id: number, action: ReviewAction, note: string) => request<SellerApplication>(
    `/admin/seller-applications/${id}/review`, { method: 'POST', body: JSON.stringify({ action, note }) },
  ),
  products: (filters: { search?: string; category?: string; offset?: number } = {}, signal?: AbortSignal) => {
    const params = new URLSearchParams({ limit: '12', offset: String(filters.offset ?? 0) });
    if (filters.search) params.set('search', filters.search);
    if (filters.category) params.set('category', filters.category);
    return request<ProductPage>(`/products?${params}`, { signal }, false);
  },
  product: (id: number, signal?: AbortSignal) => request<Product>(`/products/${id}`, { signal }, false),
  sellerProducts: () => request<ProductPage>('/seller/products?limit=100'),
  createProduct: (data: ProductInput) => request<Product>('/seller/products', { method: 'POST', body: JSON.stringify(data) }),
  updateProduct: (id: number, data: ProductInput) => request<Product>(`/seller/products/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  sellerVisibility: (id: number, status: 'active' | 'hidden') => request<Product>(
    `/seller/products/${id}/visibility`, { method: 'PATCH', body: JSON.stringify({ status }) },
  ),
  adminProducts: () => request<ProductPage>('/admin/products?limit=100'),
  moderateProduct: (id: number, status: 'active' | 'blocked') => request<Product>(
    `/admin/products/${id}/visibility`, { method: 'PATCH', body: JSON.stringify({ status }) },
  ),
};
