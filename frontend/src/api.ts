// Compatibility facade. New code should import a domain client from ./api/*.
export { ApiError, errorMessage, request, session } from './api/client';
export { authApi } from './api/auth';
export { ordersApi } from './api/order';
export { productsApi } from './api/products';
export type * from './api/types';

import { authApi } from './api/auth';
import { ordersApi } from './api/order';
import { productsApi } from './api/products';

// Keep existing component imports working while the client is migrated by domain.
export const api = {
  me: authApi.me,
  login: authApi.login,
  register: authApi.register,
  application: authApi.application,
  apply: authApi.apply,
  applications: authApi.applications,
  review: authApi.review,
  products: productsApi.list,
  product: productsApi.get,
  sellerProducts: productsApi.sellerList,
  createProduct: productsApi.create,
  updateProduct: productsApi.update,
  sellerVisibility: productsApi.setSellerVisibility,
  adminProducts: productsApi.adminList,
  moderateProduct: productsApi.setAdminVisibility,
  createOrder: ordersApi.create,
  orders: ordersApi.list,
  order: ordersApi.get,
  cancelOrder: ordersApi.cancel,
  mockPayment: ordersApi.mockPayment,
  sellerOrders: ordersApi.sellerList,
  sellerOrder: ordersApi.sellerGet,
  updateSellerOrderStatus: ordersApi.sellerSetStatus,
  adminOrders: ordersApi.adminList,
  adminOrder: ordersApi.adminGet,
};
