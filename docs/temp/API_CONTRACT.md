# MicroShop — API contract cho Auth, Product và Order

> Auth/Product và Order backend đã có runtime local. Chi tiết Order được triển khai, cấu hình, trạng thái phục hồi và test: [Order backend](ORDER_BACKEND.md). Phần 4 bên dưới giữ bản thiết kế ban đầu để tham chiếu; nhãn **[DỰ KIẾN]** và các đoạn “chưa implement” của bản draft đã được thay thế bởi tài liệu runtime đó. Ví dụ JSON chỉ minh họa; không phải dữ liệu demo đã tạo trong MySQL.

## 1. Quy ước chung

### 1.1. Địa chỉ và routing

| Cách gọi | Auth | Product | Order |
|---|---|---|---|
| Frontend local qua Vite | `/api/auth/*`, `/api/seller/application`, `/api/admin/seller-applications` | `/api/products*`, `/api/seller/products*`, `/api/admin/products*` | `/api/orders*`, `/api/seller/orders*`, `/api/admin/orders*` **[DỰ KIẾN]** |
| Service trực tiếp trên Mac | `http://127.0.0.1:8001` | `http://127.0.0.1:8002` | `http://127.0.0.1:8004` |
| Gọi giữa container | `http://auth-service:8000` | `http://product-service:8000` | `http://order-service:8000` |

Vite bỏ tiền tố `/api` trước khi chuyển tới backend. Ví dụ browser gọi `GET /api/products/15` thì Product Service nhận `GET /products/15`. Nginx/API gateway cho production chưa được triển khai; không tự giả định URL/port production.

Chi tiết mapping route, header, lỗi, rule bảo mật và cấu hình target local xem [Gateway routing](GATEWAY_ROUTING.md). Frontend không gọi trực tiếp service bằng port riêng; các endpoint `/internal/*` chỉ dùng service-to-service.

### 1.2. Format, xác thực và lỗi

- Request/response JSON (`Content-Type: application/json`), UTF-8.
- API cần login gửi `Authorization: Bearer <access_token>`; các API catalog công khai không cần token.
- JWT do Auth Service cấp; Auth đọc **role hiện tại từ database** trên mỗi lần kiểm tra. Product hỏi `GET /auth/me` để xác minh token/role; không đọc bảng `users` của Auth Service.
- API ghi dữ liệu không nhận `role`, `seller_id`, `customer_id` hoặc `total_amount` từ client, trừ khi endpoint đặc biệt mô tả rõ. Các giá trị này phải đến từ token hoặc service có thẩm quyền.
- Giá truyền/nhận dưới dạng **chuỗi decimal** (`"125000.00"`); không truyền JSON float. Tiền tệ của MVP: **VND**, không đa tiền tệ.
- Các ID là integer dương. Query list dùng `offset`/`limit`; xem mặc định và giới hạn tại từng service.
- `created_at`/`updated_at`: ISO 8601. Auth/Product hiện dùng SQL `DATETIME` và response có thể không ghi timezone; Order **dự kiến** chuẩn hóa UTC có `Z`. Frontend không nên giả định tất cả timestamp hiện có đều có `Z`.
- Auth/Product hiện trả lỗi legacy `{"detail":"..."}` hoặc `detail` là mảng validation. API mới dùng `{"code","message","details","request_id"}`; `code` ổn định cho frontend, `message` chỉ là câu hiển thị. Chi tiết và mã lỗi chuẩn xem [Response và error format](API_RESPONSE_ERRORS.md); frontend client hỗ trợ cả hai format trong giai đoạn chuyển tiếp.

| HTTP | Ý nghĩa chung |
|---:|---|
| `200` | Đọc/cập nhật thành công hoặc request lặp an toàn. |
| `201` | Tạo bản ghi mới. |
| `401` | Thiếu, sai hoặc hết hạn token. |
| `403` | Có tài khoản nhưng không có quyền. |
| `404` | Không tìm thấy hoặc không được phép biết tài nguyên thuộc người khác. |
| `409` | Trùng dữ liệu, sai trạng thái, xung đột tồn kho hoặc idempotency. |
| `422` | Input không hợp lệ (Pydantic/FastAPI). |
| `503` | Service phụ thuộc không sẵn sàng; không trả kết quả thành công giả. |

### 1.3. Ma trận quyền

| Nghiệp vụ | Guest | Customer | Seller đã duyệt | Admin |
|---|:---:|:---:|:---:|:---:|
| Xem catalog và chi tiết sản phẩm | ✓ | ✓ | ✓ | ✓ |
| Đăng ký/đăng nhập | ✓ | — | — | — |
| Xem hồ sơ cá nhân | — | ✓ | ✓ | ✓ |
| Nộp hồ sơ bán hàng | — | ✓ | — | — |
| Đăng/sửa sản phẩm sở hữu | — | — | ✓ | — |
| Duyệt hồ sơ/khóa sản phẩm | — | — | — | ✓ |
| Tạo/xem đơn mua **[DỰ KIẾN]** | — | ✓ | ✓ | — |
| Xem/xử lý phần đơn bán **[DỰ KIẾN]** | — | — | ✓ | — |
| Xem toàn bộ đơn **[DỰ KIẾN]** | — | — | — | ✓ |

Seller vẫn được mua hàng với cùng tài khoản. Admin dùng để quản trị; mua hàng bằng admin nằm ngoài phạm vi MVP Order. Giỏ hàng hiện là `localStorage` (guest hoặc theo user ID), **không có `/cart` API**.

## 2. Auth Service — [HIỆN CÓ]

### 2.1. `POST /auth/register` — tạo customer

Không cần token. Dữ liệu gửi:

```json
{
  "username": "anhtuan",
  "email": "anhtuan@example.com",
  "password": "DemoPassword123!"
}
```

`username` 3–50 ký tự; email hợp lệ; password 8–72 ký tự và không quá **72 byte UTF-8** do bcrypt. Không chấp nhận trường lạ, đặc biệt `role`. Thành công `201`:

```json
{
  "id": 15,
  "username": "anhtuan",
  "email": "anhtuan@example.com",
  "role": "customer",
  "created_at": "2026-11-02T09:00:00"
}
```

Không trả password/hash. Email hoặc username đã tồn tại: `409`; input sai: `422`.

### 2.2. `POST /auth/login` — nhận JWT

Không cần token. **Hiện chỉ login bằng email**, không hỗ trợ username:

```json
{ "email": "anhtuan@example.com", "password": "DemoPassword123!" }
```

Thành công `200`:

```json
{
  "access_token": "<JWT>",
  "token_type": "bearer",
  "expires_in": 1800
}
```

Sai email/password: `401` cùng thông điệp `Invalid email or password`; input sai: `422`. `expires_in` tính bằng giây, mặc định 30 phút nếu cấu hình chưa thay đổi. JWT hiện mang `sub`, `iat`, `exp`, `iss`, `aud`; role không lấy từ dữ liệu client/claim cũ khi kiểm tra quyền.

### 2.3. `GET /auth/me` — tài khoản hiện tại

Yêu cầu Bearer token. Thành công `200` trả `UserResponse` như ở mục đăng ký, với **role mới nhất từ DB**. Token thiếu/sai/hết hạn hoặc user đã bị xóa: `401` (header `WWW-Authenticate: Bearer`).

### 2.4. `POST /seller/application` — customer gửi hồ sơ

Yêu cầu role `customer`. Chỉ gửi:

```json
{
  "shop_name": "Blue Tech",
  "description": "Cửa hàng phụ kiện công nghệ dành cho sinh viên."
}
```

`shop_name` 3–100 ký tự, `description` 10–1000 ký tự (loại whitespace đầu/cuối); không nhận `user_id`/`status`. Thành công `201`:

```json
{
  "id": 8,
  "user_id": 15,
  "shop_name": "Blue Tech",
  "description": "Cửa hàng phụ kiện công nghệ dành cho sinh viên.",
  "status": "pending",
  "review_note": null,
  "reviewed_by": null,
  "reviewed_at": null,
  "created_at": "2026-11-02T09:10:00",
  "updated_at": "2026-11-02T09:10:00"
}
```

Một user có tối đa một hồ sơ; hồ sơ `rejected` có thể cập nhật và gửi lại, giữ nguyên `id`. Hồ sơ đã `pending`/`approved`/`suspended`: `409`; không phải customer: `403`.

### 2.5. Các API seller và admin khác

| Method + path | Quyền | Thành công | Lỗi nghiệp vụ |
|---|---|---|---|
| `GET /seller/application` | Bất kỳ user đã login | `200` + hồ sơ của chính mình | Chưa có: `404` |
| `GET /seller/profile` | Seller có hồ sơ approved | `200` + hồ sơ shop | Không đủ quyền: `403` |
| `GET /admin/seller-applications` | Admin | `200` + page | Sai filter/limit: `422` |
| `POST /admin/seller-applications/{id}/review` | Admin | `200` + hồ sơ cập nhật | ID không tồn tại: `404`; chuyển trạng thái sai: `409` |

Danh sách admin có query `status=pending|approved|rejected|suspended` (tùy chọn), `offset=0`, `limit=20` (1–100), trả:

```json
{ "items": [], "total": 0, "offset": 0, "limit": 20 }
```

Body xét duyệt:

```json
{ "action": "approve", "note": "Thông tin cửa hàng hợp lệ." }
```

`action`: `approve|reject|suspend`; `note`: 3–500 ký tự. Chuyển trạng thái hợp lệ:

```text
pending   --approve--> approved    (customer → seller)
pending   --reject---> rejected    (vẫn customer)
rejected  --gửi lại--> pending     (vẫn customer)
approved  --suspend--> suspended  (seller → customer)
suspended --approve--> approved   (customer → seller)
```

`reviewed_by` và `reviewed_at` được server ghi. Thay đổi hồ sơ và `users.role` trong cùng transaction. Admin được tạo bằng lệnh tương tác `python -m app.create_admin`, **không có API public tạo admin**.

### 2.6. Health

`GET /health` → `200 {"status":"healthy"}` nếu process chạy; `GET /ready` → `200 {"status":"ready"}` khi database sẵn sàng, lỗi DB → `503`.

## 3. Product Service — [HIỆN CÓ]

### 3.1. Object `Product`

```json
{
  "id": 101,
  "seller_id": 15,
  "name": "USB-C Adapter",
  "description": "Bộ chuyển đổi USB-C dành cho laptop.",
  "category": "Phụ kiện",
  "price": "125000.00",
  "quantity": 12,
  "image_url": "https://example.com/adapter.png",
  "status": "active",
  "created_at": "2026-11-02T10:00:00",
  "updated_at": "2026-11-02T10:00:00"
}
```

`price > 0`, tối đa 12 chữ số tổng cộng và tối đa 2 chữ số thập phân; `quantity >= 0`. `image_url` tùy chọn, nếu có phải là URL HTTP(S), tối đa 500 ký tự; hiện chưa có upload ảnh. Status: `active` (công khai), `hidden` (seller tự ẩn), `blocked` (admin khóa). API đọc công khai chỉ trả active, kể cả sản phẩm đang hết hàng (`quantity=0`); UI không cho thêm hết hàng vào giỏ.

### 3.2. `GET /products` và `GET /products/{id}` — catalog công khai

`GET /products` không cần token. Query tùy chọn:

| Query | Mặc định | Ý nghĩa |
|---|---|---|
| `search` | Không | Tìm trong tên, không phân biệt hoa/thường; tối đa 120 ký tự. `%` và `_` được xử lý như văn bản, không là wildcard. |
| `category` | Không | Khớp danh mục; tối đa 60 ký tự. |
| `seller_id` | Không | Lọc theo ID seller dương. |
| `offset` | `0` | Vị trí bắt đầu, >= 0. |
| `limit` | `20` | Số dòng, 1–100. |

```http
GET /products?search=adapter&category=Ph%E1%BB%A5%20ki%E1%BB%87n&offset=0&limit=12
```

Trả `200` dạng `{ "items": [Product], "total": 1, "offset": 0, "limit": 12 }`, sắp xếp theo `id` giảm dần. `total` là tổng số khớp filter, không chỉ số dòng của trang hiện tại. `GET /products/{id}` trả `200 Product` nếu active; không có/ẩn/bị khóa: `404 {"detail":"Product not found"}`. Query/ID không hợp lệ: `422`.

### 3.3. `POST /seller/products` — đăng sản phẩm

Yêu cầu role `seller` được Auth Service xác nhận tại thời điểm gọi. Body **không có `seller_id`/`status`**:

```json
{
  "name": "USB-C Adapter",
  "description": "Bộ chuyển đổi USB-C dành cho laptop.",
  "category": "Phụ kiện",
  "price": "125000.00",
  "quantity": 12,
  "image_url": "https://example.com/adapter.png"
}
```

`name` 3–120 ký tự, `description` 10–2000, `category` 2–60; `image_url` được phép `null` hoặc bỏ qua. Thành công `201 Product`, `seller_id` do server lấy từ Auth, `status=active`. Customer/admin: `403`; Auth không sẵn sàng: `503`; sai input: `422`.

### 3.4. Quản lý theo role

| Method + path | Quyền | Thành công | Ghi chú/lỗi |
|---|---|---|---|
| `GET /seller/products?offset=0&limit=20` | Seller | `200` + page chỉ sản phẩm mình, gồm cả hidden/blocked | Sắp `id` giảm dần |
| `PUT /seller/products/{id}` | Seller sở hữu | `200 Product` | **Thay toàn bộ** các trường của body tạo sản phẩm; không sở hữu: `404`; admin đã khóa: `409` |
| `PATCH /seller/products/{id}/visibility` | Seller sở hữu | `200 Product` | Body `{"status":"active"}` hoặc `{"status":"hidden"}`; blocked: `409` |
| `GET /admin/products?offset=0&limit=20` | Admin | `200` + page tất cả status | Không có quyền: `403` |
| `PATCH /admin/products/{id}/visibility` | Admin | `200 Product` | Body `{"status":"blocked"}` hoặc `{"status":"active"}`; không tồn tại: `404` |

Giới hạn hiện tại: sản phẩm active của seller vừa bị **tạm ngưng** có thể vẫn hiện trong catalog. Trước khi đặt hàng cần xác nhận seller còn approved; về lâu dài cần đồng bộ/ẩn catalog sau khi suspend.

### 3.5. Health

`GET /health` và `GET /ready` hoạt động tương tự Auth; `/ready` kiểm tra kết nối `product_db`.

## 4. Order Service — bản thiết kế ban đầu

**Runtime hiện có:** [ORDER_BACKEND.md](ORDER_BACKEND.md), OpenAPI cổng 8004.
Khác biệt quan trọng so với draft: lưu durable intent trước khi reserve; worker
tiếp tục request cũ khi lỗi, đơn unpaid hết hạn sau 30 phút và được worker hoàn
kho. Không có TTL tự xóa reservation độc lập tại Product. Có trạng thái trung gian
`creating/confirming/cancelling/failing`, và attempt bị từ chối là `rejected`.

Khung Order hiện có `receiver_name`, phone 9–15 ký tự, tối đa 50 dòng hàng, `payment_status=unpaid`, `orders.status=pending`, và `Numeric(14,2)` cho tổng tiền. Draft bên dưới dùng những tên/giới hạn đó; các phần idempotency, reservation, mock payment, API đọc/ghi, readiness và timestamp `updated_at` vẫn phải thiết kế/triển khai thêm. Không xem hàm `build_order_quote()` (hiện chỉ đọc `/products/{id}` và so tồn kho) là giữ kho nguyên tử hoặc một endpoint đã chạy.

### 4.1. Phạm vi và ownership

- Order Service sở hữu `order_db.orders`, `order_db.seller_orders`, `order_db.order_items`; `customer_id`, `seller_id`, `product_id` là **liên kết ID logic**, không FK xuyên database.
- Order chỉ nhận `{product_id, quantity}`, thông tin giao hàng và `Idempotency-Key`; không nhận giá/seller/tổng tiền/trạng thái thanh toán từ frontend. Giỏ hàng browser không tự động biến thành đơn.
- Customer và seller đều có thể đặt hàng với tư cách người mua; admin không đặt hàng trong MVP. `GET /auth/me` được kiểm tra để lấy user/role hiện tại.
- Chỉ Product Service được xác nhận giá, sản phẩm active, tồn kho và người bán còn approved; Order lưu snapshot tên/giá/seller khi tạo đơn.
- Tiền dùng decimal string VND; backend tính `subtotal = unit_price_snapshot × quantity`, tổng đơn bằng tổng các phần seller. Không tin phép tính tạm của browser.
- Giỏ nhiều seller tạo **một order tổng** và **một seller_order cho mỗi seller**. Các line cùng seller nằm trong seller_order đó.

### 4.2. Trạng thái và chuyển trạng thái

```text
orders.payment_status: unpaid → paid
                      unpaid → failed
                      unpaid → cancelled (khách hủy trước thanh toán)

seller_orders.status: pending → confirmed → shipping → completed
                      pending → cancelled (khi đơn tổng bị hủy/thanh toán thất bại)
```

- Seller chỉ được chuyển phần đơn thuộc mình và **chỉ sau khi thanh toán thành công**.
- MVP cho customer hủy **trước khi thanh toán**; chưa xử lý refund sau khi đã paid.
- `payment_status` biểu thị thanh toán mô phỏng, `seller_orders.status` biểu thị tiến độ xử lý của từng seller; không trộn hai loại trạng thái.
- Đơn `paid` không được thanh toán lần nữa theo kết quả khác; lặp lại cùng kết quả trả cùng trạng thái nếu có thể.

### 4.3. `POST /orders` — tạo đơn nhiều seller

Quyền: customer hoặc seller đã đăng nhập. Header `Idempotency-Key: <UUID v4>` là **bắt buộc** để retry không tạo đơn/trừ kho lần nữa. Ví dụ:

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

Validation theo `OrderCreate` hiện có: 1–50 sản phẩm khác ID; quantity là số nguyên 1–99; `receiver_name` 2–100 ký tự, `phone` 9–15 ký tự, `address` 10–500, `note` tối đa 500 hoặc null. Hai dòng trùng `product_id` trả `422` thay vì ngầm gộp. `Idempotency-Key` là **đề xuất chưa implement**: UUID v4 hợp lệ, lưu gắn với customer + hash body request.

Thành công `201` (ví dụ phản hồi OrderDetail):

```json
{
  "id": 9001,
  "customer_id": 17,
  "total_amount": "300000.00",
  "payment_status": "unpaid",
  "status": "pending",
  "shipping": {
    "receiver_name": "Nguyễn An",
    "phone": "0912345678",
    "address": "123 Đường ABC, Quận 1, TP.HCM",
    "note": "Giao giờ hành chính"
  },
  "seller_orders": [
    {
      "id": 501,
      "seller_id": 15,
      "status": "pending",
      "subtotal": "250000.00",
      "items": [
        { "id": 1, "product_id": 101, "product_name_snapshot": "USB-C Adapter", "unit_price_snapshot": "125000.00", "quantity": 2, "subtotal": "250000.00" }
      ]
    },
    {
      "id": 502,
      "seller_id": 26,
      "status": "pending",
      "subtotal": "50000.00",
      "items": [
        { "id": 2, "product_id": 205, "product_name_snapshot": "Sổ tay", "unit_price_snapshot": "50000.00", "quantity": 1, "subtotal": "50000.00" }
      ]
    }
  ],
  "created_at": "2026-11-02T10:20:00Z"
}
```

| Tình huống | HTTP dự kiến |
|---|---:|
| Thiếu token | `401` |
| Role admin, không được đặt hàng trong MVP | `403` |
| Thiếu/sai Idempotency-Key, item trùng ID, quantity/address sai | `422` |
| Sản phẩm không tồn tại/hidden/blocked hoặc seller không còn approved | `409` (lý do ổn định riêng từng trường hợp) |
| Tồn kho không đủ / cùng key nhưng body khác | `409` |
| Auth/Product không sẵn sàng hoặc không xác định được kết quả giữ kho | `503`; không trả `201` giả |

Retry với **cùng key và cùng body** sau khi đơn đã được lưu: `200` với **cùng `id` và chi tiết đơn**, không trừ kho lần nữa; key cũ nhưng body khác trả `409`. Cần test cả request đồng thời, không chỉ gửi lặp tuần tự.

### 4.4. API đọc đơn mua

| Method + path | Quyền | Trả về |
|---|---|---|
| `GET /orders?offset=0&limit=20` | Customer/seller | `200 {"items":[OrderSummary],"total":...,"offset":...,"limit":...}` chỉ đơn của mình |
| `GET /orders/{order_id}` | Chủ đơn | `200 OrderDetail` gồm seller_orders và items snapshot |
| `POST /orders/{order_id}/cancel` | Chủ đơn, trước payment | `200 OrderDetail` sau khi hủy và giải phóng tồn kho |

List sắp xếp mới nhất trước, `offset>=0`, `limit` mặc định 20, tối đa 100. Nếu order thuộc người khác, trả `404` như ID không tồn tại để tránh lộ thông tin. Hủy đơn đã paid/cancelled: `409` (trừ request retry được xử lý idempotent theo chính sách cụ thể).

### 4.5. `POST /orders/{order_id}/mock-payment`

Quyền: chủ đơn. Body chỉ mô phỏng kết quả, **không gọi ngân hàng**:

```json
{ "outcome": "success" }
```

`outcome=success|failure`. Success từ `unpaid` trả `200 OrderDetail` với `payment_status=paid`; failure trả `payment_status=failed`, đánh dấu phần seller_order `cancelled` và giải phóng tồn kho theo luồng nhất quán. Thử thanh toán đơn người khác: `404`; cùng outcome gửi lại không tạo giao dịch/thay đổi tồn kho lần nữa; outcome khác sau khi đã kết thúc: `409`. Không đặt password, số thẻ hay thông tin thanh toán thật vào request/log.

### 4.6. API đơn bán của seller và giám sát của admin

| Method + path | Quyền | Kết quả |
|---|---|---|
| `GET /seller/orders?offset=0&limit=20` | Seller đang approved | Chỉ `seller_orders` có `seller_id` của token; kèm trạng thái thanh toán của order tổng |
| `GET /seller/orders/{seller_order_id}` | Seller sở hữu phần đơn | `200 SellerOrderDetail`; seller khác: `404` |
| `PATCH /seller/orders/{seller_order_id}/status` | Seller sở hữu | `200 SellerOrderDetail` nếu đơn đã paid và chuyển trạng thái hợp lệ; khác `409` |
| `GET /admin/orders?offset=0&limit=20` | Admin | Tất cả order, phân trang |
| `GET /admin/orders/{order_id}` | Admin | Chi tiết toàn bộ order |

Body seller cập nhật trạng thái:

```json
{ "status": "confirmed" }
```

Seller không được gửi `seller_id`/`order_id` để chọn đơn của người khác; backend lọc theo user ID được Auth xác thực. Với MVP, admin chỉ **xem** đơn, chưa ép thay trạng thái của seller hay hoàn tiền thật.

### 4.7. Phối hợp nội bộ để tránh bán vượt tồn kho

**Bản thiết kế cần triển khai và kiểm thử trước khi bật nút Đặt hàng:**

1. Order xác minh customer qua Auth; gọi Product để lấy sản phẩm **active**, giá và seller, đồng thời hỏi Auth xem seller còn **approved**. Việc tra seller theo ID cần endpoint **nội bộ dự kiến** (ví dụ `POST /internal/sellers/eligibility` nhận danh sách seller ID, trả trạng thái đã duyệt), có xác thực service-to-service; API hiện tại `/seller/profile` chỉ phục vụ chính seller đăng nhập, **chưa đáp ứng bước này**. Không tin giỏ localStorage.
2. Order tạo `reservation_key` gắn với `Idempotency-Key`; gọi endpoint nội bộ Product **[DỰ KIẾN]** `POST /internal/stock/reservations` với các `{product_id,quantity}`. Chỉ service Order có credential nội bộ mới gọi được; không expose qua Vite/Gateway.
3. Product lock những dòng sản phẩm theo **thứ tự ID cố định** trong một transaction, xác minh trạng thái và tồn kho, ghi reservation idempotent, trừ lượng khả dụng **nguyên tử trong product_db**; trả snapshot giá/tên/seller. Nếu một item thất bại thì rollback **toàn bộ batch** trong Product DB.
4. Order tính lại tổng tiền từ snapshot và tạo `orders`, `seller_orders`, `order_items` + idempotency record trong một transaction của `order_db`.
5. Nếu bước ghi `order_db` chắc chắn thất bại, Order gọi Product **[DỰ KIẾN]** `POST /internal/stock/reservations/{key}/release` (idempotent). Nếu gọi timeout/không biết kết quả, **không retry tạo reservation mới**: truy vấn trạng thái key cũ, đối soát rồi phục hồi.
6. Mock payment thành công chỉ xác nhận khi reservation vẫn còn hiệu lực; nếu đã hết hạn thì không được đánh dấu paid giả. Thất bại/hủy trước thanh toán thì release; reservation hết hạn cần worker/TTL reconciliation để tự trả kho nếu request chết giữa chừng.

Đây là **giao dịch phân tán**, không có transaction SQL duy nhất bao trùm hai database/service. `SELECT → kiểm tra quantity → UPDATE` qua hai service không đủ chống hai khách mua món cuối cùng. Ở phiên bản đầu, phải kiểm thử race, retry và failure/timeout; nếu chưa đảm bảo bước 2–6 thì **không cho checkout thật**. Hợp đồng endpoint nội bộ, thời hạn reservation, service credential và quy tắc đối soát sẽ được chốt khi implement Order; không được coi chúng là API đã chạy.

### 4.8. Các tình huống acceptance test Order bắt buộc

- Customer tạo đơn 2 sản phẩm từ 2 seller → 1 order tổng, 2 seller_orders, mỗi seller chỉ xem phần mình.
- Thay giá trên frontend hoặc gửi `total_amount`/`seller_id` giả → backend bỏ qua/từ chối và tính lại từ Product.
- Sản phẩm hidden/blocked/hết kho hoặc seller suspended → checkout từ chối, không tạo đơn từng phần.
- Hai request tranh mua món cuối → chỉ một request thành công; kho không âm.
- Retry cùng Idempotency-Key/body → cùng order ID, không trừ kho hai lần; cùng key/body khác → `409`.
- Auth/Product timeout; Order DB lỗi sau khi reserve; mock payment thất bại/hủy → xác minh không thất thoát tồn kho và có trạng thái đối soát.
- Customer khác truy cập `GET /orders/{id}` → `404`; seller khác xem/cập nhật seller_order → `404`.
- Seller chưa được duyệt hoặc vừa bị suspend không xử lý đơn bán; seller không xác nhận giao hàng trước khi đơn paid.

## 5. Thay đổi hợp đồng và nguồn kiểm chứng

- Endpoint **hiện có**: xem OpenAPI thực tế ở `http://127.0.0.1:8001/openapi.json` và `http://127.0.0.1:8002/openapi.json`, hoặc Swagger `/docs` trên từng port khi Docker đang chạy.
- Endpoint **dự kiến**: Order đã có model/schema/quote helper nhưng chưa có OpenAPI/runtime. Khi implement Order phải cập nhật file, code, frontend API client và integration test trong cùng PR.
- Nếu muốn thêm `/api/v1` hoặc dùng domain production, cần một quyết định versioning/gateway riêng; hiện frontend đang dùng `/api` làm tiền tố proxy local, backend **không** có `/api/v1`.
- Thay đổi phá vỡ client (đổi tên field, status, cách tính tiền, quyền) cần nêu rõ trong PR và điều chỉnh test. Không sửa mẫu response trong tài liệu rồi coi như backend đã đổi theo.
