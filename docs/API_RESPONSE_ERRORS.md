# Response và error format — MicroShop

Tài liệu này là format thống nhất cho frontend/backend. Auth và Product hiện vẫn trả lỗi FastAPI legacy; API client đã đọc được cả format mới và legacy để có thể chuyển từng service mà không làm frontend vỡ.

## 1. Response thành công

Không bọc thêm một lớp `data` cho response hiện có. Resource trả trực tiếp theo schema của endpoint:

```http
200 OK
Content-Type: application/json
```

```json
{
  "id": 15,
  "name": "USB-C Adapter",
  "price": "125000.00",
  "quantity": 8
}
```

Tạo resource dùng `201 Created`; cập nhật/đọc dùng `200 OK`; xóa thành công nếu sau này có endpoint delete có thể dùng `204 No Content` nếu frontend không cần response body. Không trả `200` cho thao tác thất bại.

### Response phân trang

Tất cả list dùng cùng shape:

```json
{
  "items": [],
  "total": 0,
  "offset": 0,
  "limit": 20
}
```

`total` là tổng số record sau filter, `offset`/`limit` là giá trị server thực sự áp dụng. Tiền là decimal string, ID là integer dương, thời gian là ISO 8601. Order khi triển khai chuẩn hóa timestamp UTC có `Z`; frontend không tự tính lại tiền từ số float.

## 2. Error format mới

API mới và các endpoint được sửa nên trả:

```json
{
  "code": "INSUFFICIENT_STOCK",
  "message": "Sản phẩm không đủ số lượng để đặt hàng.",
  "details": {
    "product_id": 101,
    "available": 1,
    "requested": 2
  },
  "request_id": "req_01JABC123"
}
```

Quy ước:

- `code`: bắt buộc, uppercase `SCREAMING_SNAKE_CASE`, ổn định để frontend xử lý logic/dịch thông báo; không đổi chỉ vì sửa câu chữ.
- `message`: bắt buộc, câu an toàn cho người dùng; không chứa stack trace, SQL, token, password hay thông tin service nội bộ.
- `details`: tùy chọn, dữ liệu có cấu trúc để gắn lỗi vào field hoặc giải thích conflict; không đưa secret/PII không cần thiết.
- `request_id`: tùy chọn nhưng nên có ở production để trace log; không phải ID resource và frontend không dùng để quyết định quyền.
- Không trả HTML, plaintext stack trace hoặc schema lỗi khác nhau cho cùng một endpoint.

## 3. Error validation

Input lỗi dùng `422 Unprocessable Entity` và code `VALIDATION_ERROR`:

```json
{
  "code": "VALIDATION_ERROR",
  "message": "Dữ liệu gửi lên chưa hợp lệ.",
  "details": [
    { "field": "shipping.phone", "message": "Số điện thoại không hợp lệ." },
    { "field": "items[0].quantity", "message": "Số lượng phải từ 1 đến 99." }
  ],
  "request_id": "req_01JABC123"
}
```

Frontend hiển thị `details[].message` cạnh field nếu có, còn `message` là fallback chung. Backend không trả giá trị input nhạy cảm trong `details`.

## 4. Mã lỗi chuẩn theo HTTP

| HTTP | Code gợi ý | Ý nghĩa và hướng xử lý |
|---:|---|---|
| `400` | `BAD_REQUEST` | Request không đúng cấu trúc giao thức |
| `401` | `AUTHENTICATION_REQUIRED`, `INVALID_TOKEN` | Login lại; không retry vô hạn |
| `403` | `FORBIDDEN`, `SELLER_NOT_APPROVED` | Hiển thị không có quyền; không retry |
| `404` | `RESOURCE_NOT_FOUND`, `ORDER_NOT_FOUND` | Hiển thị không tồn tại; resource của user khác cũng có thể dùng 404 |
| `409` | `DUPLICATE_RESOURCE`, `INSUFFICIENT_STOCK`, `IDEMPOTENCY_CONFLICT`, `INVALID_STATUS_TRANSITION` | Hiển thị conflict và hướng dẫn sửa/reload |
| `422` | `VALIDATION_ERROR` | Gắn lỗi vào form |
| `429` | `RATE_LIMITED` | Chờ theo `Retry-After`, không retry nhanh liên tục |
| `500` | `INTERNAL_ERROR` | Thông báo chung, log bằng request ID; không lộ chi tiết |
| `502` | `UPSTREAM_ERROR` | Service phụ thuộc trả lỗi; có thể retry có kiểm soát |
| `503` | `SERVICE_UNAVAILABLE` | Service chưa sẵn sàng; không báo thành công giả |
| `504` | `UPSTREAM_TIMEOUT` | Không biết kết quả upstream; với order phải query/reconcile idempotency key |

## 5. Lỗi Order bắt buộc

| Code | HTTP | Khi dùng |
|---|---:|---|
| `INSUFFICIENT_STOCK` | `409` | Một hoặc nhiều item không đủ tồn kho; không tạo order từng phần |
| `PRODUCT_UNAVAILABLE` | `409` | Product hidden/blocked/không tồn tại |
| `SELLER_NOT_APPROVED` | `409` | Seller của item không còn được duyệt |
| `IDEMPOTENCY_CONFLICT` | `409` | Cùng key nhưng request body khác |
| `ORDER_NOT_FOUND` | `404` | Order không tồn tại hoặc không thuộc user |
| `ORDER_ALREADY_PAID` | `409` | Thử thanh toán lại order đã kết thúc |
| `RESERVATION_EXPIRED` | `409` | Reservation hết hạn, không được đánh dấu paid |
| `INVALID_STATUS_TRANSITION` | `409` | Seller chuyển trạng thái không theo chuỗi hợp lệ |
| `ORDER_DEPENDENCY_UNAVAILABLE` | `503` | Auth/Product/DB chưa sẵn sàng |
| `ORDER_RECONCILIATION_REQUIRED` | `503` | Timeout không rõ kết quả giữ kho/ghi order; cần đối soát, không tạo reservation mới |

## 6. Legacy compatibility

Auth/Product hiện có:

```json
{ "detail": "Invalid email or password" }
```

hoặc lỗi validation FastAPI:

```json
{
  "detail": [
    { "loc": ["body", "email"], "msg": "value is not a valid email" }
  ]
}
```

Không đổi hàng loạt trong cùng PR chỉ để đổi format. Trong thời gian chuyển tiếp:

- Backend cũ tiếp tục trả `detail`.
- `frontend/src/api/client.ts` chuyển legacy detail thành `ApiError` với `code=LEGACY_ERROR` hoặc `VALIDATION_ERROR`.
- Backend mới trả `code/message/details/request_id`.
- Khi sửa Auth/Product, thêm test contract và cập nhật mapping message; không để component tự đọc `detail`.
- Không dùng nội dung tiếng Anh hiện tại làm mã logic lâu dài.

## 7. Frontend handling

`ApiError` có các trường `status`, `code`, `message`, `details`, `requestId`. Component thường chỉ cần `errorMessage(error)` để hiển thị; form chuyên biệt có thể đọc `code`/`details`:

```ts
try {
  await ordersApi.create(payload, key);
} catch (error) {
  if (error instanceof ApiError && error.code === 'INSUFFICIENT_STOCK') {
    // Tải lại giá/tồn kho, giữ người dùng ở checkout.
  }
}
```

Không retry tự động cho `400`, `401`, `403`, `404`, `409`, `422`. Chỉ retry có giới hạn cho network/`502`/`503`/`504`, và với thao tác tạo order phải dùng lại cùng `Idempotency-Key`.

## 8. Definition of Done

- Endpoint mới có success schema, status code, error code và ví dụ JSON trong contract.
- Mỗi lỗi nghiệp vụ có một `code` ổn định, không dùng message để phân nhánh logic.
- Validation trả field path rõ ràng; lỗi server không lộ stack trace/secret.
- Frontend API client parse cả format mới và legacy; component không tự parse response lỗi.
- Có test success, validation, auth, permission, not-found, conflict và upstream failure.
- Gateway giữ nguyên status/body và có thể thêm `request_id`, không đổi lỗi thành `200`.
