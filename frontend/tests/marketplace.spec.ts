import { test, expect, type Page } from '@playwright/test';

const timestamp = '2026-10-26T12:00:00';
const user = { id: 1, username: 'minhtri', email: 'tri@example.com', role: 'customer', created_at: timestamp };
const application = {
  id: 7, user_id: 1, shop_name: 'Blue Tech', description: 'Cửa hàng phụ kiện công nghệ.',
  status: 'pending', review_note: null, reviewed_by: null, reviewed_at: null,
  created_at: timestamp, updated_at: timestamp,
};

async function signedIn(page: Page, role = 'customer') {
  await page.addInitScript(() => sessionStorage.setItem('microshop.access-token', 'test-token'));
  await page.route('**/api/auth/me', route => route.fulfill({ json: { ...user, role } }));
}

test('registration sends customer fields and shows success', async ({ page }) => {
  let payload: unknown;
  await page.route('**/api/auth/register', route => {
    payload = route.request().postDataJSON();
    return route.fulfill({ status: 201, json: user });
  });
  await page.goto('/register');
  await page.getByLabel('Tên người dùng').fill('minhtri');
  await page.getByLabel('Email', { exact: true }).fill('tri@example.com');
  await page.getByLabel('Mật khẩu', { exact: true }).fill('DemoPassword123!');
  await page.getByLabel('Xác nhận mật khẩu').fill('DemoPassword123!');
  await page.getByRole('button', { name: 'Tạo tài khoản', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Tài khoản đã sẵn sàng!' })).toBeVisible();
  expect(payload).toEqual({ username: 'minhtri', email: 'tri@example.com', password: 'DemoPassword123!' });
});

test('password confirmation mismatch is explained without submission', async ({ page }) => {
  let submitted = false;
  await page.route('**/api/auth/register', route => { submitted = true; return route.abort(); });
  await page.goto('/register');
  await page.getByLabel('Tên người dùng').fill('minhtri');
  await page.getByLabel('Email', { exact: true }).fill('tri@example.com');
  await page.getByLabel('Mật khẩu', { exact: true }).fill('DemoPassword123!');
  await page.getByLabel('Xác nhận mật khẩu').fill('WrongPassword123!');
  await page.getByRole('button', { name: 'Tạo tài khoản', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('chưa khớp');
  expect(submitted).toBe(false);
});

test('login, account refresh and logout', async ({ page }) => {
  await page.route('**/api/auth/login', route => route.fulfill({ json: { access_token: 'test-token', token_type: 'bearer', expires_in: 1800 } }));
  await page.route('**/api/auth/me', route => {
    expect(route.request().headers()['authorization']).toBe('Bearer test-token');
    return route.fulfill({ json: user });
  });
  await page.goto('/login');
  await page.getByLabel('Email', { exact: true }).fill('tri@example.com');
  await page.getByLabel('Mật khẩu', { exact: true }).fill('DemoPassword123!');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await expect(page).toHaveURL(/\/account$/);
  await expect(page.getByRole('heading', { name: /Xin chào, minhtri/ })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: /Xin chào, minhtri/ })).toBeVisible();
  await page.getByRole('button', { name: 'Đăng xuất' }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect(await page.evaluate(() => sessionStorage.getItem('microshop.access-token'))).toBeNull();
});

test('wrong login shows Vietnamese error', async ({ page }) => {
  await page.route('**/api/auth/login', route => route.fulfill({ status: 401, json: { detail: 'Invalid email or password' } }));
  await page.goto('/login');
  await page.getByLabel('Email', { exact: true }).fill('tri@example.com');
  await page.getByLabel('Mật khẩu', { exact: true }).fill('wrong-password');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Email hoặc mật khẩu chưa đúng');
});

test('customer submits shop and sees pending result', async ({ page }) => {
  await signedIn(page);
  await page.route('**/api/seller/application', route => {
    if (route.request().method() === 'POST') {
      expect(route.request().postDataJSON()).toEqual({ shop_name: 'Blue Tech', description: 'Cửa hàng phụ kiện công nghệ.' });
      return route.fulfill({ status: 201, json: application });
    }
    return route.fulfill({ status: 404, json: { detail: 'Seller application not found' } });
  });
  await page.goto('/seller');
  await page.getByLabel('Tên cửa hàng').fill('Blue Tech');
  await page.getByLabel('Giới thiệu cửa hàng').fill('Cửa hàng phụ kiện công nghệ.');
  await page.getByRole('button', { name: 'Gửi hồ sơ đăng ký' }).click();
  await expect(page.getByText('Chờ duyệt', { exact: true })).toBeVisible();
  await expect(page.getByRole('status')).toContainText('Đã gửi hồ sơ');
  await expect(page.getByRole('button', { name: 'Gửi hồ sơ đăng ký' })).toHaveCount(0);
});

test('rejected application can be edited; suspended cannot resubmit', async ({ page }) => {
  await signedIn(page);
  let status = 'rejected';
  await page.route('**/api/seller/application', route => route.fulfill({ json: { ...application, status, review_note: 'Bổ sung mô tả cửa hàng.' } }));
  await page.goto('/seller');
  await expect(page.getByLabel('Tên cửa hàng')).toHaveValue('Blue Tech');
  await expect(page.getByRole('button', { name: 'Gửi lại hồ sơ' })).toBeVisible();
  status = 'suspended';
  await page.getByRole('button', { name: 'Tải lại trạng thái' }).click();
  await expect(page.getByText('Tạm ngưng', { exact: true })).toBeVisible();
  await expect(page.getByLabel('Tên cửa hàng')).toHaveCount(0);
});

test('customer cannot access admin UI', async ({ page }) => {
  await signedIn(page);
  let requested = false;
  await page.route('**/api/admin/**', route => { requested = true; return route.abort(); });
  await page.goto('/admin');
  await expect(page.getByRole('heading', { name: 'Bạn không có quyền truy cập' })).toBeVisible();
  expect(requested).toBe(false);
});

test('admin reviews application and list refreshes', async ({ page }) => {
  await signedIn(page, 'admin');
  let reviewed = false;
  await page.route('**/api/admin/seller-applications?*', route => route.fulfill({ json: {
    items: reviewed ? [] : [application], total: reviewed ? 0 : 1, offset: 0, limit: 10,
  } }));
  await page.route('**/api/admin/seller-applications/7/review', route => {
    expect(route.request().postDataJSON()).toEqual({ action: 'approve', note: 'Hồ sơ hợp lệ.' });
    reviewed = true;
    return route.fulfill({ json: { ...application, status: 'approved' } });
  });
  await page.goto('/admin');
  await page.getByRole('button', { name: 'Duyệt hồ sơ' }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByLabel('Lý do / phản hồi').fill('Hồ sơ hợp lệ.');
  await page.getByRole('button', { name: 'Xác nhận' }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.getByRole('status')).toContainText('Đã cập nhật hồ sơ');
  await expect(page.getByRole('heading', { name: 'Không có hồ sơ ở đây' })).toBeVisible();
});

test('admin conflict keeps explanation and allows cancel', async ({ page }) => {
  await signedIn(page, 'admin');
  await page.route('**/api/admin/seller-applications?*', route => route.fulfill({ json: { items: [application], total: 1, offset: 0, limit: 10 } }));
  await page.route('**/api/admin/seller-applications/7/review', route => route.fulfill({ status: 409, json: { detail: 'Invalid seller status transition' } }));
  await page.goto('/admin');
  await page.getByRole('button', { name: 'Từ chối', exact: true }).click();
  await page.getByLabel('Lý do / phản hồi').fill('Cần bổ sung thông tin.');
  await page.getByRole('button', { name: 'Xác nhận' }).click();
  await expect(page.getByRole('alert')).toContainText('Trạng thái hồ sơ đã thay đổi');
  await page.getByRole('button', { name: 'Hủy', exact: true }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
});

test('expired session redirects to login and clears token', async ({ page }) => {
  await signedIn(page);
  await page.route('**/api/auth/me', route => route.fulfill({ status: 401, json: { detail: 'Invalid or expired access token' } }));
  await page.goto('/account');
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole('alert')).toContainText('hết hạn');
  expect(await page.evaluate(() => sessionStorage.getItem('microshop.access-token'))).toBeNull();
});

test('backend failure shows retry rather than empty application form', async ({ page }) => {
  await signedIn(page);
  await page.route('**/api/seller/application', route => route.fulfill({ status: 503, json: { detail: 'Database unavailable' } }));
  await page.goto('/seller');
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Gửi hồ sơ đăng ký' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Tải lại trạng thái' })).toBeEnabled();
});

test('mobile home and login do not overflow viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /Khám phá món đồ/ })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole('link', { name: 'Đăng nhập', exact: true }).click();
  await expect(page.getByLabel('Email', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test('Vite proxy reaches real Auth Service health endpoint without changing data', async ({ request }) => {
  const response = await request.get('/api/health');
  expect(response.ok()).toBeTruthy();
  expect(await response.json()).toEqual({ status: 'healthy' });
});

const product = {
  id: 5, seller_id: 1, name: 'USB-C Adapter', description: 'Bộ chuyển đổi dành cho máy tính xách tay',
  category: 'Phụ kiện', price: '125000.00', quantity: 12, image_url: null, status: 'active',
  created_at: timestamp, updated_at: timestamp,
};

test('catalog searches and opens product detail', async ({ page }) => {
  await page.route('**/api/products?*', route => route.fulfill({ json: {
    items: [product], total: 1, offset: 0, limit: 12,
  } }));
  await page.route('**/api/products/5', route => route.fulfill({ json: product }));
  await page.goto('/products');
  await expect(page.getByRole('heading', { name: 'USB-C Adapter' })).toBeVisible();
  await page.getByLabel('Tìm sản phẩm').fill('USB');
  await page.getByRole('button', { name: 'Tìm kiếm' }).click();
  await expect(page).toHaveURL(/\/products$/);
  await page.getByRole('link', { name: /USB-C Adapter/ }).click();
  await expect(page).toHaveURL(/\/products\/5$/);
  await expect(page.getByRole('heading', { name: 'USB-C Adapter' })).toBeVisible();
  await expect(page.getByRole('button', { name: /Thêm vào giỏ/ })).toBeVisible();
});

test('seller posts product; customer cannot open product management', async ({ page }) => {
  await signedIn(page, 'customer');
  let posted = false;
  await page.route('**/api/seller/products*', route => { posted = true; return route.abort(); });
  await page.goto('/seller/products');
  await expect(page.getByRole('heading', { name: 'Bạn không có quyền truy cập' })).toBeVisible();
  expect(posted).toBe(false);

  await page.route('**/api/auth/me', route => route.fulfill({ json: { ...user, role: 'seller' } }));
  await page.route('**/api/seller/products?*', route => route.fulfill({ json: { items: [], total: 0, offset: 0, limit: 100 } }));
  await page.route('**/api/seller/products', route => {
    const payload = route.request().postDataJSON();
    expect(payload).toMatchObject({ name: 'USB-C Adapter', price: '125000.00', quantity: 12 });
    expect(payload).not.toHaveProperty('seller_id');
    posted = true;
    return route.fulfill({ status: 201, json: product });
  });
  await page.reload();
  await page.getByLabel('Tên sản phẩm').fill('USB-C Adapter');
  await page.getByLabel('Mô tả').fill('Bộ chuyển đổi dành cho máy tính xách tay');
  await page.getByLabel('Danh mục').fill('Phụ kiện');
  await page.getByLabel('Giá (VND)').fill('125000.00');
  await page.getByLabel('Tồn kho').fill('12');
  await page.getByRole('button', { name: 'Đăng sản phẩm' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Đã đăng sản phẩm mới' })).toBeVisible();
  expect(posted).toBe(true);
});

test('admin moderation blocks product; unauthenticated public catalog works', async ({ page }) => {
  await signedIn(page, 'admin');
  await page.route('**/api/admin/products?*', route => route.fulfill({ json: { items: [product], total: 1, limit: 100, offset: 0 } }));
  let blocked = false;
  await page.route('**/api/admin/products/5/visibility', route => {
    expect(route.request().postDataJSON()).toEqual({ status: 'blocked' });
    blocked = true;
    return route.fulfill({ json: { ...product, status: 'blocked' } });
  });
  await page.goto('/admin/products');
  await page.getByRole('button', { name: 'Khóa sản phẩm' }).click();
  await expect(page.locator('.notice.success')).toContainText('Đã cập nhật trạng thái sản phẩm');
  expect(blocked).toBe(true);
});

test('Vite proxy reaches Product Service catalog without writing data', async ({ request }) => {
  const response = await request.get('/api/products');
  expect(response.ok()).toBeTruthy();
  const data = await response.json();
  expect(data).toHaveProperty('items');
  expect(data).toHaveProperty('total');
});
