# Frontend Gateway Routing — MicroShop

Tài liệu này chốt cách frontend gọi backend thông qua một tiền tố `/api`. Browser không gọi trực tiếp từng service bằng port riêng. Ở local, Vite proxy đóng vai trò gateway phát triển; ở production, reverse proxy/API gateway phải giữ cùng public contract để frontend không đổi URL.

## 1. Mục tiêu

- Frontend chỉ biết một origin và một public prefix: `/api`.
- Không để browser biết port nội bộ, hostname container, credential service-to-service hoặc database.
- Gateway chỉ routing và chuyển tiếp request; quyền, ownership, validation và business rule vẫn thuộc backend service.
- Giữ URL frontend ổn định khi Auth/Product/Order đổi port hoặc chạy trong container.
- Không expose endpoint nội bộ như stock reservation hoặc seller eligibility ra browser.

## 2. Luồng request

### Local development

```text
Browser :5173
    │ fetch('/api' + path)
    ▼
Vite dev/preview proxy
    ├── /api/auth/*, /api/seller/application, /api/admin/seller-applications
    │       └── Auth Service :8001, bỏ prefix /api
    ├── /api/products*, /api/seller/products*, /api/admin/products*
    │       └── Product Service :8002, bỏ prefix /api
    └── /api/orders*, /api/seller/orders*, /api/admin/orders*
            └── Order Service, bỏ prefix /api khi service được bật
```

Browser gọi `GET /api/products/15`; service nhận `GET /products/15`. Browser không gọi `http://127.0.0.1:8001` hoặc `:8002` trực tiếp.

### Production dự kiến

```text
Browser
  │ https://app.example.com/api/...
  ▼
Reverse proxy/API gateway :443
  ├── /api/auth/*             → auth-service:8000
  ├── /api/seller/application → auth-service:8000
  ├── /api/admin/seller-*     → auth-service:8000
  ├── /api/products*          → product-service:8000
  ├── /api/seller/products*   → product-service:8000
  ├── /api/admin/products*    → product-service:8000
  └── /api/orders*            → order-service:8000
```

Production gateway chưa được triển khai trong repo. Sơ đồ trên là target architecture, không phải hostname/port đã chạy.

## 3. Public route mapping

| Browser path | Backend path sau khi bỏ `/api` | Service | Trạng thái |
|---|---|---|---|
| `/api/auth/*` | `/auth/*` | Auth | Đang dùng |
| `/api/seller/application` | `/seller/application` | Auth | Đang dùng |
| `/api/admin/seller-applications*` | `/admin/seller-applications*` | Auth | Đang dùng |
| `/api/products*` | `/products*` | Product | Đang dùng |
| `/api/seller/products*` | `/seller/products*` | Product | Đang dùng |
| `/api/admin/products*` | `/admin/products*` | Product | Đang dùng |
| `/api/orders*` | `/orders*` | Order | Dự kiến |
| `/api/seller/orders*` | `/seller/orders*` | Order | Dự kiến |
| `/api/admin/orders*` | `/admin/orders*` | Order | Dự kiến |

Rule cụ thể hơn phải được đánh giá trước rule tổng quát. Ví dụ `/api/seller/products` phải đi Product, không bị rule `/api` chuyển nhầm sang Auth. `frontend/vite.config.ts` hiện đã đặt các rule Product trước rule tổng quát `/api`.

## 4. Frontend client contract

Mọi request phải đi qua `frontend/src/api.ts` và helper `request()`:

```ts
request<Product>('/products/15', {}, false)
request<Order>('/orders', {
  method: 'POST',
  headers: { 'Idempotency-Key': key },
  body: JSON.stringify(payload),
})
```

Quy tắc:

- Dùng path tương đối `/api/...`, không hard-code service URL trong component.
- Helper tự thêm `Content-Type: application/json` khi có body.
- Request protected tự thêm `Authorization: Bearer <access_token>` từ session storage.
- Catalog public có thể gọi với `authenticated=false`; không cần gửi token nếu không có.
- Request có body JSON phải dùng `JSON.stringify`; không gửi password, JWT hoặc credential service trong query string.
- Các request tạo order phải gửi `Idempotency-Key` do client tạo một lần cho một lần submit logic; retry dùng lại key, không tạo key mới.
- Dùng `AbortSignal`/timeout để không giữ màn hình loading vô hạn; request bị hủy bởi component không được hiển thị lỗi giả.
- Component không tự quyết định route service, không gọi `fetch()` trực tiếp nếu đã có API client.

## 5. Header được chuyển tiếp

### Browser → gateway

| Header | Khi nào | Quy tắc |
|---|---|---|
| `Authorization` | API cần đăng nhập | Gateway chuyển nguyên trạng tới service; service tự verify JWT/role hiện tại |
| `Content-Type` | Request JSON | `application/json` |
| `Idempotency-Key` | `POST /api/orders` và action cần retry | Gateway chuyển nguyên trạng tới Order; không tự thay đổi |
| `Accept` | Mặc định | `application/json` |

Gateway không được tự gán `customer_id`, `seller_id`, `role`, `total_amount` hoặc trạng thái order dựa trên header/query của browser. Các giá trị này phải được Auth/Order xác thực.

### Service-to-service

Order gọi Auth/Product bằng network nội bộ, không qua browser gateway:

```text
Order → Auth: seller eligibility / identity check
Order → Product: stock reservation, release, confirmation, product snapshot
```

Các request này cần credential service-to-service riêng, timeout, retry có điều kiện và audit log không chứa secret. Không đưa các route `/internal/*` vào public `/api` mapping.

## 6. HTTP status và lỗi

Gateway không biến mọi lỗi backend thành `200`. Tối thiểu phải giữ status code và JSON body:

```json
{ "detail": "..." }
```

| Status | Frontend xử lý |
|---:|---|
| `200` | Hiển thị dữ liệu/kết quả cập nhật |
| `201` | Tạo thành công; với order chuyển tới detail |
| `400`/`422` | Hiển thị lỗi tại form hoặc field |
| `401` | Xóa session nếu token hết hạn, chuyển `/login` hoặc cho login lại |
| `403` | Hiển thị không có quyền, không retry tự động |
| `404` | Hiển thị resource không tồn tại; với order của user khác không tiết lộ thêm |
| `409` | Hiển thị conflict như hết kho, idempotency body khác, trạng thái không hợp lệ |
| `502`/`503`/`504` | Hiển thị service tạm thời không sẵn sàng; cho retry, không báo thành công |
| Network/timeout | Hiển thị không kết nối; với order phải query/reconcile key cũ trước khi submit lại |

Gateway có thể thêm request ID để tracing nhưng không được đổi schema lỗi mà frontend đã dùng. Nếu production chuẩn hóa lỗi, cần cập nhật `api.ts`, API contract và test cùng một PR.

## 7. Cấu hình local hiện tại

Các biến target trong `frontend/vite.config.ts`:

| Biến | Mặc định | Dùng cho |
|---|---|---|
| `AUTH_API_TARGET` | `http://127.0.0.1:8001` | Auth routes và route seller/admin application |
| `PRODUCT_API_TARGET` | `http://127.0.0.1:8002` | Product routes |
| `ORDER_API_TARGET` | Chưa có | Cần thêm khi Order Service chạy |

Khi bổ sung Order vào Vite proxy, dùng target riêng và rewrite cùng quy tắc:

```ts
'/api/orders': {
  target: process.env.ORDER_API_TARGET || 'http://127.0.0.1:8003',
  changeOrigin: true,
  rewrite: (path: string) => path.replace(/^\/api/, ''),
},
```

Rule `/api/orders` phải đặt trước rule `/api` tổng quát. Không dùng `ORDER_API_TARGET` trỏ vào Auth/Product và không commit secret vào file cấu hình.

## 8. Gateway security rules

- Chỉ expose public `/api` routes được liệt kê trong bảng mapping.
- Chặn `/internal/*`, `/docs` nội bộ, health của service nội bộ và database port khỏi internet production; health public nếu cần phải có route riêng.
- Dùng HTTPS ở production; không truyền JWT qua HTTP public.
- Giới hạn body size, timeout và rate limit theo route; login/register và order cần chính sách riêng.
- Không cache response của `/auth/me`, order, seller/admin data hoặc response chứa thông tin riêng tư.
- Catalog GET có thể cache ngắn hạn nhưng phải xác định rõ vấn đề stale price/stock; checkout luôn lấy dữ liệu authoritative ở backend.
- CORS chỉ cần cấu hình nếu frontend và gateway khác origin; ưu tiên cùng origin để tránh CORS.
- Log method, public path, status, duration và request ID; không log `Authorization`, password, payment data hoặc service credential.

## 9. Definition of Done

- Mọi frontend API call dùng `/api` và API client chung.
- Có mapping rõ tới đúng service và rule cụ thể đứng trước rule tổng quát.
- Auth header, `Idempotency-Key`, timeout và status code được giữ nguyên.
- Internal service endpoint không thể gọi từ browser.
- Có test proxy cho Auth/Product/Order, gồm route không nhầm service và lỗi upstream.
- Local và production giữ cùng public path; chỉ thay target/hostname ở gateway.
- README, API contract và tài liệu frontend route được cập nhật khi thêm route.

## 10. Tài liệu liên quan

- [API contract](API_CONTRACT.md): request/response, role và backend ownership.
- [Frontend routes](FRONTEND_ROUTES.md): URL màn hình và luồng điều hướng.
- [API draft](API_DRAFT.md): endpoint Order dự kiến và issue triển khai.
- `frontend/src/api.ts`: API client hiện tại.
- `frontend/vite.config.ts`: proxy local hiện tại.
