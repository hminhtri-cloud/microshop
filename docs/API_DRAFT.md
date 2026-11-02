# API draft — danh sách endpoint để chia việc

Tài liệu này là **bản nháp một trang theo nhóm công việc**, dùng để tạo issue và chia nhiệm vụ. Trường dữ liệu, ví dụ request/response, lỗi và luồng tồn kho chi tiết nằm tại [API contract](API_CONTRACT.md). Khi code và draft khác nhau, route/schema trong source và OpenAPI thực tế là trạng thái **đang chạy**; sửa draft bằng PR trước khi coi phần mới là đã hoàn thành.

## 1. Trạng thái hiện tại

| Service | Có thể gọi qua HTTP? | Phần đã có |
|---|---|---|
| Auth (`:8001`) | Có | Register, login email, `/me`, hồ sơ seller, admin duyệt/tạm ngưng, health/ready |
| Product (`:8002`) | Có | Catalog công khai, seller CRUD, admin kiểm duyệt, health/ready |
| Order | **Chưa** | Đã có `models.py`, `schemas.py`, `service.py` (quote), Auth/Product client, DB config; chưa có router/main/Compose/order_db |

Giỏ hàng hiện ở browser `localStorage` dưới dạng `{productId, quantity}`; **chưa có `/cart` API, chưa có checkout**, không gọi giỏ hàng browser là đơn hàng đã lưu.

## 2. Auth — endpoint đã có

| Method + path (trên backend) | Vai trò | Ý nghĩa | Trả thành công |
|---|---|---|---|
| `POST /auth/register` | Guest | Tạo customer; không nhận role từ client | `201 User` |
| `POST /auth/login` | Guest | Email/password → JWT | `200 Token` |
| `GET /auth/me` | Đã login | Thông tin và role mới nhất từ DB | `200 User` |
| `POST /seller/application` | Customer | Gửi hoặc gửi lại hồ sơ rejected | `201 SellerApplication` |
| `GET /seller/application` | Đã login | Xem hồ sơ của mình | `200 SellerApplication` |
| `GET /seller/profile` | Seller approved | Xem shop của mình | `200 SellerApplication` |
| `GET /admin/seller-applications` | Admin | Lọc/phân trang hồ sơ | `200 Page` |
| `POST /admin/seller-applications/{id}/review` | Admin | `approve/reject/suspend` | `200 SellerApplication` |
| `GET /health`, `GET /ready` | Công khai | Liveness và DB readiness | `200`; ready lỗi DB `503` |

**Cần bổ sung cho Order:** API **nội bộ**, chỉ Order gọi, để kiểm tra theo **danh sách seller ID** seller nào còn `approved` (gợi ý `POST /internal/sellers/eligibility`). `/seller/profile` hiện chỉ kiểm tra tài khoản đang gửi token của chính mình; không đủ cho checkout sản phẩm nhiều seller. Phải có xác thực service-to-service, không expose endpoint nội bộ qua gateway.

## 3. Product — endpoint đã có

| Method + path | Vai trò | Ý nghĩa | Trả thành công |
|---|---|---|---|
| `GET /products` | Công khai | Tìm/lọc/phân trang active | `200 ProductPage` |
| `GET /products/{id}` | Công khai | Chi tiết active; hidden/blocked trả `404` | `200 Product` |
| `GET /seller/products` | Seller | Sản phẩm của mình, gồm hidden/blocked | `200 ProductPage` |
| `POST /seller/products` | Seller | Tạo sản phẩm, server gán seller_id | `201 Product` |
| `PUT /seller/products/{id}` | Seller sở hữu | Cập nhật **đủ trường** | `200 Product` |
| `PATCH /seller/products/{id}/visibility` | Seller sở hữu | Active/hidden, không mở blocked | `200 Product` |
| `GET /admin/products` | Admin | Xem mọi sản phẩm | `200 ProductPage` |
| `PATCH /admin/products/{id}/visibility` | Admin | Active/blocked | `200 Product` |
| `GET /health`, `GET /ready` | Công khai | Liveness và DB readiness | `200`; ready lỗi DB `503` |

**Cần bổ sung cho Order:** API **nội bộ** giữ/trả tồn kho nguyên tử cho **cả giỏ nhiều sản phẩm**; check status, quantity và seller hợp lệ, trả snapshot authoritative. Retry theo key không được trừ kho lần hai; có đối soát khi timeout/Order DB lỗi. Cần xử lý sản phẩm active của seller vừa bị suspend còn xuất hiện ở catalog. Các endpoint nội bộ là **dự kiến**, chưa chạy.

## 4. Order — dự kiến endpoint và contract MVP

### Quy ước input

- User gửi `Authorization: Bearer <JWT>`; Order hỏi Auth `/auth/me` lấy customer ID/role. Customer hoặc seller được mua; admin không mua trong MVP.
- `POST /orders` nhận **`Idempotency-Key: UUID v4`** để retry an toàn; phần này chưa có trong khung Order hiện tại.
- Input `items` (1–50 dòng): `{product_id, quantity}`; quantity integer 1–99, không trùng product ID.
- Input `shipping`: `{receiver_name, phone, address, note?}` theo `schemas.py` hiện tại (không dùng tên `recipient_name`); phone 9–15 ký tự.
- Client không được gửi `price`, `seller_id`, `customer_id`, `total_amount`, `payment_status`; backend lấy quyền, giá, seller, tồn kho từ Auth/Product và tự tính.
- Tiền JSON là chuỗi decimal VND; snapshot `product_name_snapshot`, `unit_price_snapshot` nằm trong order_items. Khung model dùng `payment_status="unpaid"`, `orders.status="pending"`, tổng tiền `Numeric(14,2)`.

### Bảng endpoint cần implement

| Method + path | Ai gọi | Thành công | Trường hợp cần test |
|---|---|---|---|
| `GET /health`, `GET /ready` | Công khai | `200`/`503` khi DB lỗi | Không báo ready nếu order_db chưa kết nối |
| `POST /orders` | Customer/seller | `201 OrderDetail` gồm `seller_orders[]`/`items[]`; retry cùng key/body: `200` cùng ID | Sản phẩm hidden, seller suspended, thiếu kho, request lặp/đồng thời, Auth/Product timeout |
| `GET /orders?offset=0&limit=20` | Chủ đơn | `200 Page<OrderSummary>` | Không thấy đơn người khác |
| `GET /orders/{id}` | Chủ đơn | `200 OrderDetail` | ID người khác → `404` |
| `POST /orders/{id}/mock-payment` | Chủ đơn | `200 OrderDetail`; body `{"outcome":"success"}` hoặc `"failure"` | Không thanh toán 2 lần, kiểm tra reservation còn hiệu lực |
| `POST /orders/{id}/cancel` | Chủ đơn, chưa paid | `200 OrderDetail`, hoàn tồn kho | Đã paid → `409`, retry không trả kho hai lần |
| `GET /seller/orders?offset=0&limit=20` | Seller approved | `200 Page<SellerOrderSummary>` | Chỉ phần đơn thuộc seller |
| `GET /seller/orders/{id}` | Seller sở hữu | `200 SellerOrderDetail` | Người khác → `404` |
| `PATCH /seller/orders/{id}/status` | Seller sở hữu | `200 SellerOrderDetail`; `{"status":"confirmed"}` v.v. | Chỉ xử lý sau paid; không nhảy trạng thái |
| `GET /admin/orders?offset=0&limit=20` | Admin | `200 Page<OrderSummary>` | Customer/seller → `403` |
| `GET /admin/orders/{id}` | Admin | `200 OrderDetail` | Không lộ endpoint cho user thường |

Thứ tự seller order: `pending → confirmed → shipping → completed`; đơn chưa thanh toán không được chuyển sang `confirmed`. Mock payment: `unpaid → paid|failed|cancelled`. Mọi đường dẫn Order phía trên là **mục tiêu**, không phải API có sẵn để frontend gọi.

### Ví dụ POST /orders (draft)

```http
POST /orders
Authorization: Bearer <JWT>
Idempotency-Key: 22d3a5bb-b88b-4e57-9442-6a63c5f2d981
Content-Type: application/json
```

```json
{
  "items": [
    { "product_id": 101, "quantity": 2 },
    { "product_id": 205, "quantity": 1 }
  ],
  "shipping": {
    "receiver_name": "Nguyễn An",
    "phone": "0912345678",
    "address": "123 Đường ABC, Quận 1, TP.HCM",
    "note": "Giao giờ hành chính"
  }
}
```

Response target: `OrderDetail` có `id`, `customer_id`, `total_amount` dạng chuỗi, `payment_status="unpaid"`, `status="pending"`, shipping, `seller_orders[]`; từng seller order có `seller_id`, `subtotal`, `items[]` chứa tên/giá snapshot. Chi tiết ví dụ phản hồi: [API contract §4.3](API_CONTRACT.md#43-post-orders--tạo-đơn-nhiều-seller).

**Tình trạng khung code:** `build_order_quote()` hiện chỉ lấy giá/seller/tồn kho bằng `GET /products/{id}` và tính tổng; **không đặt reservation, không trừ kho, không idempotency, không lưu order**. Không bật nút checkout chỉ vì quote helper chạy được. Thiết kế batch reservation, giải phóng kho, TTL và lỗi phân tán: [API contract §4.7](API_CONTRACT.md#47-phối-hợp-nội-bộ-để-tránh-bán-vượt-tồn-kho).

## 5. Thứ tự chia issue và Definition of Done

1. Auth nội bộ: xác minh seller approved cho Order (quyền service-to-service).
2. Product: reserve/release kho batch nguyên tử + idempotency; ẩn seller suspended khỏi catalog.
3. Order nền tảng: chạy `order_db`/Docker/Compose, `/health`, `/ready`, migration phù hợp.
4. Order ghi: `POST /orders` với Auth, Product, reservation, idempotency, snapshot và chia theo seller.
5. Order đọc: danh sách/chi tiết chỉ cho chủ đơn; admin/seller chỉ xem phạm vi tương ứng.
6. Mock payment/cancel và seller status; mới bật checkout trên frontend sau khi test race/retry/release thành công.

Một endpoint hoàn thành khi: có route/schema/status code đúng contract; kiểm tra quyền **ở backend**; test hành vi thành công + sai input + quyền + lỗi service phụ thuộc; cập nhật OpenAPI/README và có thể demo bằng request thật. Không đánh dấu xong chỉ vì tạo file hoặc trả response hard-code.

## 6. GitHub issues

| Thứ tự đề xuất | Issue | Công việc |
|---:|---|---|
| 1 | [#1 — Auth: seller eligibility nội bộ](https://github.com/hminhtri-cloud/microshop/issues/1) | Kiểm tra seller approved theo ID cho Order |
| 1 | [#3 — Product: ẩn sản phẩm seller suspended](https://github.com/hminhtri-cloud/microshop/issues/3) | Sửa catalog công khai trước khi bật checkout |
| 1 | [#4 — Order: khởi tạo service và order_db](https://github.com/hminhtri-cloud/microshop/issues/4) | Docker/Compose, DB, health, readiness; giữ khung code đã có |
| 2 | [#2 — Product: atomic stock reservation](https://github.com/hminhtri-cloud/microshop/issues/2) | Giữ/trả kho batch, idempotency, test đồng thời; phụ thuộc #1 |
| 3 | [#5 — Order: POST /orders](https://github.com/hminhtri-cloud/microshop/issues/5) | Đơn nhiều seller, snapshot, idempotency; phụ thuộc #1, #2, #4 |
| 4 | [#6 — Order: GET /orders, GET /orders/{id}](https://github.com/hminhtri-cloud/microshop/issues/6) | Buyer chỉ xem đơn mình |
| 4 | [#7 — Order: mock payment/cancel](https://github.com/hminhtri-cloud/microshop/issues/7) | Chuyển payment state và giải phóng kho an toàn |
| 5 | [#8 — Order: seller order APIs](https://github.com/hminhtri-cloud/microshop/issues/8) | Danh sách/chi tiết/trạng thái phần đơn của seller |
| 5 | [#9 — Order: admin order APIs](https://github.com/hminhtri-cloud/microshop/issues/9) | Admin xem toàn bộ đơn và chi tiết |

Các issue trên đang mở, **không có nghĩa là API đã chạy**. Không tạo issue mới cho endpoint Auth/Product đã triển khai, trừ khi có bug hoặc yêu cầu mở rộng riêng. Có thể chia #1/#3/#4 cho ba thành viên làm song song; #5 chỉ bắt đầu khi các phụ thuộc của nó đã chạy và được kiểm thử.
