# Frontend routes — MicroShop

Tài liệu này chốt sơ đồ URL của frontend React, quyền truy cập và luồng điều hướng. Đây là tài liệu giao diện, không phải danh sách backend API. Backend vẫn phải kiểm tra quyền độc lập; việc ẩn menu hoặc dùng route guard không phải cơ chế bảo mật.

## 1. Quy ước chung

- Base URL local: `http://127.0.0.1:5173`.
- Các route dùng chữ thường, danh từ số nhiều cho collection: `/products`, `/orders`.
- ID dùng path parameter: `/products/:id`, `/orders/:orderId`.
- Bộ lọc, tìm kiếm và phân trang dùng query string, ví dụ `/products?search=usb&category=electronics` và `/orders?offset=0&limit=20`.
- Refresh trực tiếp một URL phải được Vite fallback về `index.html`; frontend tự hiển thị trang tương ứng.
- Không đưa JWT, giá, seller ID hoặc tổng tiền vào URL. Giỏ hàng chỉ giữ `productId` và `quantity` trong browser.
- Sau khi đăng nhập thành công, chuyển về `/account` ở milestone hiện tại; khi triển khai checkout có thể lưu `returnTo` an toàn để quay lại trang cần thiết.
- Khi logout, xóa session trên browser và chuyển về `/login`; các trang protected không được render dữ liệu cũ.

## 2. Route đang chạy

| Route | Màn hình | Quyền | Trạng thái |
|---|---|---|---|
| `/` | Storefront, sản phẩm mới và CTA | Công khai | Đã có |
| `/products` | Catalog, tìm kiếm/lọc/phân trang | Công khai | Đã có |
| `/products/:id` | Chi tiết sản phẩm, chọn số lượng và thêm giỏ | Công khai | Đã có |
| `/cart` | Giỏ hàng browser, kiểm tra giá/tồn kho, tạm tính | Công khai | Đã có; chưa đặt hàng |
| `/login` | Đăng nhập | Khách chưa đăng nhập | Đã có; user đã đăng nhập chuyển `/account` |
| `/register` | Đăng ký customer | Khách chưa đăng nhập | Đã có |
| `/account` | Thông tin tài khoản và role | Đã đăng nhập | Đã có |
| `/seller` | Nộp/theo dõi hồ sơ seller | Customer hoặc seller; admin chuyển `/admin` | Đã có |
| `/seller/products` | Quản lý sản phẩm của shop | Seller approved | Đã có |
| `/admin` | Duyệt/từ chối/tạm ngưng seller | Admin | Đã có |
| `/admin/products` | Kiểm duyệt sản phẩm | Admin | Đã có |
| `*` | Trang không tồn tại | Công khai | Đã có; link về `/` |

Route hiện được khai báo tại `frontend/src/App.tsx`. Header dùng khu điều hướng riêng khi URL bắt đầu bằng `/seller` hoặc `/admin`; seller/admin vẫn có thể quay lại khu mua sắm bằng `/products`.

## 3. Route dự kiến cho Order

Các route sau chỉ được bật sau khi Order Service có API runtime và frontend có client tương ứng. Trước thời điểm đó, `/cart` tiếp tục hiển thị nút đặt hàng bị vô hiệu hóa, không tạo order giả.

| Route | Màn hình | Quyền | Điểm vào | Backend chính |
|---|---|---|---|---|
| `/checkout` | Xác nhận sản phẩm, địa chỉ nhận hàng và tổng tiền cuối | Customer hoặc seller đã đăng nhập | `/cart` | `POST /orders` |
| `/orders` | Danh sách đơn đã mua | Customer/seller, chỉ đơn của mình | Header hoặc trang account | `GET /orders` |
| `/orders/:orderId` | Chi tiết order tổng, seller orders và item snapshot | Chủ đơn | `/orders` hoặc sau checkout | `GET /orders/{id}` |
| `/orders/:orderId/payment` | Kết quả/thao tác thanh toán mô phỏng | Chủ đơn, order chưa kết thúc | `/orders/:orderId` | `POST /orders/{id}/mock-payment` |
| `/seller/orders` | Danh sách phần đơn seller cần xử lý | Seller approved | Seller workspace | `GET /seller/orders` |
| `/seller/orders/:sellerOrderId` | Chi tiết phần đơn của seller | Seller sở hữu phần đơn | `/seller/orders` | `GET /seller/orders/{id}` |
| `/admin/orders` | Danh sách toàn bộ order | Admin | Admin workspace | `GET /admin/orders` |
| `/admin/orders/:orderId` | Chi tiết order cho admin | Admin | `/admin/orders` | `GET /admin/orders/{id}` |

### Route không tạo riêng

- Không có `/checkout/success`: trạng thái cuối đọc từ `/orders/:orderId`, tránh hai nguồn sự thật.
- Không có `/payment/card`: MVP chỉ có mock payment, không nhận số thẻ/password/payment secret.
- Không có `/seller/orders/:id/edit`: seller chỉ chuyển trạng thái bằng action trong detail; không cho sửa dữ liệu snapshot.
- Không có `/admin/orders/:id/refund`: MVP chưa hỗ trợ refund thật.
- Không có `/cart/:sellerId`: giỏ nhiều seller vẫn là một order tổng, backend tách thành các `seller_orders`.

## 4. Luồng điều hướng dự kiến

### Customer mua hàng

```text
/ 
  -> /products
  -> /products/:id
  -> /cart
  -> /login (nếu chưa đăng nhập)
  -> /checkout
  -> POST /orders
  -> /orders/:orderId
  -> /orders/:orderId/payment (mock)
  -> /orders/:orderId với payment_status=paid|failed
```

- `/checkout` phải kiểm tra lại catalog/tồn kho trước khi gửi order; không tin giá tạm tính trong cart.
- Nếu Auth/Product lỗi, hiển thị lỗi có thể thử lại, không chuyển sang trang thành công.
- Nếu tồn kho hoặc seller không hợp lệ, giữ người dùng ở checkout, đánh dấu item cần xử lý và không xóa giỏ toàn bộ.
- Sau `201`, xóa các line tương ứng khỏi cart và chuyển tới order detail. Retry cùng `Idempotency-Key` chỉ hiển thị cùng order.
- Nếu user bấm back hoặc refresh checkout, không tạo request mới nếu chưa thay đổi input; client cần giữ trạng thái submit phù hợp.

### Seller đăng ký và bán hàng

```text
/account -> /seller -> (approved) /seller/products
/seller/products -> /seller/orders -> /seller/orders/:sellerOrderId
```

- Customer chỉ được nộp/theo dõi hồ sơ ở `/seller`.
- Seller chưa approved vẫn vào `/seller` nhưng không được vào `/seller/products` hoặc `/seller/orders`.
- Seller bị suspend có thể thấy thông báo trạng thái nhưng không được xử lý đơn mới; backend quyết định theo role/trạng thái mới nhất.
- Seller vẫn có thể mua hàng và dùng `/cart`, `/checkout`, `/orders` nếu đang đăng nhập hợp lệ.

### Admin

```text
/account -> /admin
/admin -> /admin/products
/admin -> /admin/orders
/admin/orders -> /admin/orders/:orderId
```

- Admin không có quyền đặt hàng trong MVP; nếu truy cập `/checkout` từ dữ liệu cũ, frontend hiển thị 403/không khả dụng và backend vẫn từ chối.
- Admin xem toàn bộ order nhưng không được frontend giả lập quyền cập nhật trạng thái seller hoặc refund.

## 5. Route guard và trạng thái truy cập

| Tình huống | Hành vi frontend |
|---|---|
| Chưa đăng nhập vào route protected | Redirect `/login`; sau khi có quyết định UX mới thêm `returnTo` |
| Auth đang tải | Hiển thị loading, không render nội dung protected tạm thời |
| JWT có nhưng `/auth/me` lỗi | Hiển thị lỗi và nút thử lại; không tự coi user là admin/seller |
| Sai role | Hiển thị trang 403 có link `/account`; không redirect vòng lặp |
| Seller role nhưng bị suspend sau khi mở trang | API trả lỗi quyền; refresh user và khóa action, không chỉ dựa vào state cũ |
| Resource không tồn tại hoặc không thuộc user | Hiển thị 404 chung, không tiết lộ resource của người khác |
| API timeout/5xx | Hiển thị lỗi và retry; không điều hướng sang success |
| Form submit đang chạy | Disable nút/action; dùng idempotency cho create order |
| Browser reload trên route con | Giữ route nếu Vite fallback hoạt động; gọi lại API cần thiết |

Frontend hiện đã có `Protected` cho login/admin/seller. Khi thêm Order nên mở rộng guard theo quyền, nhưng ownership của order phải kiểm tra ở backend. Không đưa `customer_id`/`seller_id` vào URL để quyết định quyền.

## 6. Wireframe nội dung từng màn hình

### `/checkout`

```text
[Quay lại giỏ hàng]
Xác nhận đơn hàng

┌ Sản phẩm từ nhiều shop ───────┐  ┌ Tóm tắt đơn ───────┐
│ item, giá snapshot, số lượng  │  │ Tạm tính            │
│ item, giá snapshot, số lượng  │  │ Phí/ghi chú MVP     │
└───────────────────────────────┘  │ Tổng tiền backend   │
┌ Thông tin giao hàng ──────────┐  │ [Đặt hàng]          │
│ receiver_name, phone, address │  └─────────────────────┘
│ note                           │
└────────────────────────────────┘
```

### `/orders`

```text
Đơn đã mua                         [Tất cả / pending / paid / failed]
┌ #order ─ ngày ─ trạng thái ─ tổng tiền ─ [Xem chi tiết] ┐
┌ #order ─ ngày ─ trạng thái ─ tổng tiền ─ [Xem chi tiết] ┐
[Trước] [Sau]
```

### `/orders/:orderId`

```text
Đơn hàng #9001        payment: unpaid/paid/failed    [Hủy đơn]
Thông tin giao hàng
Seller A: status pending
  item snapshot x quantity        subtotal
Seller B: status pending
  item snapshot x quantity        subtotal
Tổng đơn                                      [Thanh toán mô phỏng]
```

### `/seller/orders` và `/admin/orders`

Giữ layout workspace hiện tại: sidebar theo role, toolbar filter/pagination, list/table responsive và detail page. Seller chỉ thấy seller order thuộc mình; admin thấy order tổng và các seller order con. Mobile chuyển bảng thành card, không ẩn trạng thái hoặc tổng tiền quan trọng.

## 7. Mapping route frontend với API

| Frontend | API/read model | Ghi chú |
|---|---|---|
| `/products`, `/products/:id` | Product catalog | Giá/tồn kho hiển thị chỉ là snapshot tạm thời |
| `/cart` | `GET /products/{id}` từng line hiện tại | Chưa có persisted cart API |
| `/checkout` | Auth `/auth/me`, Product internal reservation, `POST /orders` | Không gọi trực tiếp internal API từ browser |
| `/orders` | `GET /orders` | Filter status có thể dùng query backend sau khi contract chốt |
| `/orders/:orderId` | `GET /orders/{id}` | Dữ liệu order snapshot, không lấy giá mới để sửa lịch sử |
| `/orders/:orderId/payment` | `POST /orders/{id}/mock-payment` | Chỉ mock, action idempotent |
| `/seller/orders` | `GET /seller/orders` | Filter theo seller từ JWT server-side |
| `/seller/orders/:sellerOrderId` | `GET/PATCH /seller/orders/{id}` | Không cho client chọn seller_id |
| `/admin/orders` | `GET /admin/orders` | Admin read-only trong MVP |
| `/admin/orders/:orderId` | `GET /admin/orders/{id}` | Không có refund thật |

## 8. Definition of Done cho route mới

- Có entry trong bảng route, wireframe tối thiểu và link điều hướng từ trang trước.
- Có loading, empty, error, unauthorized/forbidden, not-found và mobile layout.
- Có route guard frontend nhưng vẫn có kiểm tra ownership/role ở backend.
- Có API client typed, không gọi internal service trực tiếp từ browser.
- Có test điều hướng và quyền: guest, customer, seller approved/suspended, admin và resource người khác.
- Checkout chỉ hiển thị thành công sau response tạo order thật; retry/refresh không tạo order trùng.
- Cập nhật `README.md`, `docs/API_DRAFT.md` và OpenAPI/API contract khi contract thay đổi.

## 9. Thứ tự triển khai đề xuất

1. Giữ các route hiện tại và thêm placeholder link “Đơn mua” cho user đã đăng nhập.
2. Implement Order Service bootstrap và API `POST /orders`/read trước khi bật `/checkout`.
3. Tạo `/checkout`, sau đó `/orders` và `/orders/:orderId`.
4. Tạo seller order pages và admin order pages.
5. Bổ sung mock payment/cancel, race/retry tests và cập nhật E2E.

Các route dự kiến trong tài liệu này không được coi là đã triển khai cho tới khi có route React, API runtime, test và phân quyền tương ứng.
