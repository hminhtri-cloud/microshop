# Frontend API client structure

API client frontend được chia theo domain để component chỉ gọi hàm có ý nghĩa, không tự biết gateway target hay format header. Public URL vẫn đi qua `/api`; chi tiết routing nằm ở [Gateway routing](GATEWAY_ROUTING.md).

## Cấu trúc

```text
frontend/src/
├── api.ts              # compatibility facade cho component cũ
└── api/
    ├── client.ts       # request(), session, ApiError, timeout, JWT, lỗi
    ├── types.ts        # types Auth/Product/Order dùng chung
    ├── auth.ts         # authApi: login, register, me, seller application
    ├── products.ts     # productsApi: catalog, seller/admin product
    └── order.ts        # ordersApi: buyer, seller/admin order, payment
```

## Nguyên tắc sử dụng

Code mới import theo domain:

```ts
import { ordersApi } from './api/orders';
import type { OrderCreateInput } from './api/types';

const order = await ordersApi.create(payload, idempotencyKey);
```

Không làm:

```ts
fetch('http://127.0.0.1:8004/orders');
```

hoặc gọi `fetch()` trực tiếp trong component. `client.ts` là nơi duy nhất chịu trách nhiệm cho `/api`, bearer token, timeout, parse lỗi và xử lý 401.

## Compatibility facade

`frontend/src/api.ts` vẫn export `api`, `ApiError`, `errorMessage`, `session` và các types cũ để các màn hình hiện tại không phải đổi toàn bộ trong một PR. Các method mới có thể gọi qua facade, nhưng màn hình mới nên import `authApi`, `productsApi` hoặc `ordersApi` trực tiếp.

| Domain | Module | Ví dụ |
|---|---|---|
| Auth | `authApi` | `login`, `register`, `me`, `application`, `review` |
| Product | `productsApi` | `list`, `get`, `create`, `update`, visibility |
| Order | `ordersApi` | `create`, `list`, `get`, `cancel`, mock payment, seller/admin |
| Shared | `request` | URL, JWT, JSON, timeout, `ApiError` |

## Order client contract

`ordersApi.create()` bắt buộc nhận `idempotencyKey` riêng:

```ts
const payload: OrderCreateInput = {
  items: [{ product_id: 101, quantity: 2 }],
  shipping: {
    receiver_name: 'Nguyen An',
    phone: '0912345678',
    address: '123 Duong ABC',
  },
};

await ordersApi.create(payload, crypto.randomUUID());
```

Trong thực tế, retry cùng một lần submit phải dùng lại key cũ; không tạo UUID mới cho mỗi retry. Frontend không tự tính giá authoritative, không gửi `seller_id`/`customer_id`/`total_amount`, và không gọi API nội bộ reservation.

## Khi thêm endpoint

1. Chốt path, role, request/response/status trong `docs/API_CONTRACT.md`.
2. Thêm hoặc sửa type trong `api/types.ts`.
3. Thêm method vào module đúng domain; dùng `request()` thay vì `fetch()` mới.
4. Nếu cần retry an toàn, truyền `Idempotency-Key` qua options/header.
5. Cập nhật component, route docs và API client test/E2E.
6. Chạy `npm run build` và kiểm tra lỗi ownership/role ở backend không bị thay bằng frontend guard.

## Trạng thái

- Auth/Product client: đang dùng cho các màn hình hiện tại.
- Order types/client: đã tạo theo contract dự kiến nhưng **chưa gọi được runtime** vì Order Service chưa có router/container.
- `ordersApi` không làm cho checkout hoạt động; chỉ cung cấp typed client để dùng khi backend issue #4/#5 và các phụ thuộc hoàn thành.
