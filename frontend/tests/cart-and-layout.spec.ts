import { test, expect, type Page } from '@playwright/test';

const stamp = '2026-10-26T12:00:00';
const adapter = {
  id: 5, seller_id: 1, name: 'USB-C Adapter', description: 'Bộ chuyển đổi cho máy tính',
  category: 'Phụ kiện', price: '125000.00', quantity: 3, image_url: null,
  status: 'active', created_at: stamp, updated_at: stamp,
};
const notebook = {
  ...adapter, id: 6, seller_id: 2, name: 'Sổ tay', description: 'Sổ tay ghi chép mỗi ngày',
  price: '50000.00', quantity: 5,
};

async function mockProducts(page: Page) {
  let stock = adapter.quantity;
  let hidden = false;
  await page.route('**/api/products/5', route => hidden
    ? route.fulfill({ status: 404, json: { detail: 'Product not found' } })
    : route.fulfill({ json: { ...adapter, quantity: stock } }));
  await page.route('**/api/products/6', route => route.fulfill({ json: notebook }));
  await page.route('**/api/products?*', route => route.fulfill({ json: {
    items: [adapter, notebook], total: 2, offset: 0, limit: 12,
  } }));
  return { changeStock: (value: number) => { stock = value; }, hide: () => { hidden = true; } };
}

async function loginAs(page: Page, role: string, id = 10) {
  await page.route('**/api/auth/me', route => route.fulfill({ json: {
    id, username: role, email: `${role}@example.com`, role, created_at: stamp,
  } }));
  await page.route('**/api/auth/login', route => route.fulfill({ json: {
    access_token: `token-${id}`, token_type: 'bearer', expires_in: 1800,
  } }));
  await page.goto('/login');
  await page.getByLabel('Email', { exact: true }).fill(`${role}@example.com`);
  await page.getByLabel('Mật khẩu', { exact: true }).fill('test-password');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await expect(page).toHaveURL(/\/account$/);
}

test('guest cart stores only IDs and quantities; multiple sellers and estimated total survive reload', async ({ page }) => {
  await mockProducts(page);
  let orderRequests = 0;
  await page.route('**/api/orders**', route => { orderRequests += 1; return route.abort(); });
  await page.goto('/products/5');
  await page.getByLabel('Số lượng thêm vào giỏ').fill('2');
  await page.getByRole('button', { name: /Thêm vào giỏ/ }).click();
  await page.goto('/products/6');
  await page.getByRole('button', { name: /Thêm vào giỏ/ }).click();
  await expect(page.getByLabel('3 sản phẩm trong giỏ')).toBeVisible();
  await page.goto('/cart');
  await expect(page.getByRole('link', { name: 'USB-C Adapter' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Sổ tay' })).toBeVisible();
  await expect(page.getByText('300.000 ₫')).toBeVisible();
  await expect(page.getByRole('button', { name: /Đặt hàng/ })).toBeDisabled();
  expect(orderRequests).toBe(0);
  expect(await page.evaluate(() => JSON.parse(localStorage.getItem('microshop.cart.v1.guest')!)))
    .toEqual([{ productId: 5, quantity: 2 }, { productId: 6, quantity: 1 }]);
  await page.reload();
  await expect(page.getByLabel('3 sản phẩm trong giỏ')).toBeVisible();
  await expect(page.getByText('300.000 ₫')).toBeVisible();
  await page.getByRole('button', { name: 'Giảm số lượng USB-C Adapter' }).click();
  await expect(page.getByLabel('2 sản phẩm trong giỏ')).toBeVisible();
  await expect(page.getByText('175.000 ₫')).toBeVisible();
});

test('price/stock are rechecked; hidden products remain removable and cannot be counted as valid', async ({ page }) => {
  const controls = await mockProducts(page);
  await page.goto('/products/5');
  await page.getByLabel('Số lượng thêm vào giỏ').fill('3');
  await page.getByRole('button', { name: /Thêm vào giỏ/ }).click();
  controls.changeStock(1);
  await page.goto('/cart');
  await expect(page.getByText('Chỉ còn 1 sản phẩm')).toBeVisible();
  await expect(page.getByText(/Giỏ có sản phẩm không còn hợp lệ/)).toBeVisible();
  await page.getByRole('button', { name: 'Giảm số lượng USB-C Adapter' }).click();
  await page.getByRole('button', { name: 'Giảm số lượng USB-C Adapter' }).click();
  await expect(page.getByText('125.000 ₫')).toBeVisible();
  controls.hide();
  await page.getByRole('button', { name: 'Kiểm tra lại giá & tồn kho' }).click();
  await expect(page.getByText('Sản phẩm không còn hiển thị')).toBeVisible();
  await page.getByRole('button', { name: 'Xóa khỏi giỏ' }).click();
  await expect(page.getByRole('heading', { name: 'Giỏ hàng đang trống' })).toBeVisible();
});

test('customer, seller and admin have separate workspaces and cart buckets', async ({ page }) => {
  await mockProducts(page);
  await page.goto('/products/5');
  await page.getByRole('button', { name: /Thêm vào giỏ/ }).click();
  await expect(page.getByLabel('1 sản phẩm trong giỏ')).toBeVisible();
  await loginAs(page, 'customer');
  await expect(page.getByLabel('0 sản phẩm trong giỏ')).toBeVisible();
  await page.route('**/api/seller/application', route => route.fulfill({ status: 404, json: { detail: 'Seller application not found' } }));
  await page.goto('/seller');
  await expect(page.getByRole('navigation', { name: 'Điều hướng người bán' }).getByRole('link', { name: 'Hồ sơ cửa hàng' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Điều hướng người bán' }).getByRole('link', { name: 'Sản phẩm của tôi' })).toHaveCount(0);
  await page.goto('/seller/products');
  await expect(page.getByRole('heading', { name: 'Bạn không có quyền truy cập' })).toBeVisible();
  await page.goto('/admin');
  await expect(page.getByRole('heading', { name: 'Bạn không có quyền truy cập' })).toBeVisible();

  await page.route('**/api/auth/me', route => route.fulfill({ json: {
    id: 10, username: 'seller', email: 'seller@example.com', role: 'seller', created_at: stamp,
  } }));
  await page.reload();
  await page.goto('/seller');
  await expect(page.getByRole('navigation', { name: 'Điều hướng người bán' }).getByRole('link', { name: 'Sản phẩm của tôi' })).toBeVisible();
  await page.getByRole('button', { name: 'Đăng xuất' }).click();
  await page.goto('/cart');
  await expect(page.getByLabel('1 sản phẩm trong giỏ')).toBeVisible();

  await loginAs(page, 'admin', 20);
  await page.route('**/api/admin/seller-applications?*', route => route.fulfill({ json: { items: [], total: 0, offset: 0, limit: 10 } }));
  await page.goto('/admin');
  await expect(page.getByRole('navigation', { name: 'Điều hướng quản trị' }).getByRole('link', { name: 'Kiểm duyệt sản phẩm' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Điều hướng quản trị' }).getByRole('link', { name: 'Hồ sơ người bán' })).toBeVisible();
});

test('mobile cart and seller layout stay within viewport', async ({ page }) => {
  await mockProducts(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/products/5');
  await page.getByRole('button', { name: /Thêm vào giỏ/ }).click();
  await page.goto('/cart');
  await expect(page.getByRole('heading', { name: 'Giỏ hàng của bạn.' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.route('**/api/seller/application', route => route.fulfill({ status: 404, json: { detail: 'Seller application not found' } }));
  await page.route('**/api/auth/me', route => route.fulfill({ json: {
    id: 10, username: 'customer', email: 'customer@example.com', role: 'customer', created_at: stamp,
  } }));
  await page.evaluate(() => sessionStorage.setItem('microshop.access-token', 'token'));
  await page.goto('/seller');
  await expect(page.getByRole('navigation', { name: 'Điều hướng người bán' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('overstock cannot be added and damaged cart data does not break the storefront', async ({ page }) => {
  await mockProducts(page);
  await page.goto('/products/5');
  await page.getByLabel('Số lượng thêm vào giỏ').fill('3');
  await page.getByRole('button', { name: /Thêm vào giỏ/ }).click();
  await page.getByRole('button', { name: /Thêm vào giỏ/ }).click();
  await expect(page.getByRole('alert')).toContainText('vượt quá tồn kho');
  await expect(page.getByLabel('3 sản phẩm trong giỏ')).toBeVisible();
  await page.evaluate(() => localStorage.setItem('microshop.cart.v1.guest', '[{"productId":5,"quantity":-8}]'));
  await page.reload();
  await expect(page.getByLabel('0 sản phẩm trong giỏ')).toBeVisible();
  await page.goto('/cart');
  await expect(page.getByRole('heading', { name: 'Giỏ hàng đang trống' })).toBeVisible();
});
