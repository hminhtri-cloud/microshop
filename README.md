# MicroShop — Marketplace

**Làm việc nhóm:** xem [Git workflow](docs/GIT_WORKFLOW.md) để tạo branch,
Pull Request, review và kiểm tra CI trước khi merge.

**API contract:** xem [thiết kế Auth, Product và Order](docs/API_CONTRACT.md) —
có phân biệt các endpoint đang chạy với Order Service mới có khung code.
Nhóm có thể dùng [API draft và danh sách issue backend](docs/API_DRAFT.md) để
chia việc trước khi triển khai Order.
Sơ đồ URL, quyền truy cập và luồng màn hình frontend nằm trong
[Frontend routes](docs/FRONTEND_ROUTES.md).
Quy ước frontend gọi gateway và mapping service nằm trong
[Gateway routing](docs/GATEWAY_ROUTING.md).
Cấu trúc API client theo domain nằm trong
[API client structure](docs/API_CLIENT_STRUCTURE.md).
Format response và error message nằm trong
[API response/errors](docs/API_RESPONSE_ERRORS.md).
Kiến trúc triển khai Docker Compose, Kubernetes và AWS nằm trong
[Deployment architecture](docs/DEPLOYMENT_ARCHITECTURE.md).
Cấu trúc thư mục hạ tầng và deployment nằm trong
[infrastructure/](infrastructure/README.md) và [deploy/](deploy/README.md).
Diagram kiến trúc tổng thể nằm trong
[Architecture Diagram](docs/ARCHITECTURE_DIAGRAM.md).

React + Vite + TypeScript, FastAPI và MySQL. Auth Service có đăng ký/login,
JWT, hồ sơ seller và admin duyệt seller. Product Service có catalog, tìm kiếm,
quản lý sản phẩm theo seller và admin kiểm duyệt. Frontend có khu mua sắm,
giỏ hàng tạm thời và menu riêng cho người mua, seller, admin. Order Service
và thanh toán mô phỏng sẽ được làm ở các milestone tiếp theo.

## Giao diện web local

Chạy backend trước bằng `docker compose up -d --build --wait`, sau đó mở
terminal thứ hai tại `microshop/frontend`:

```bash
npm ci
npm run dev
```

Mở **http://127.0.0.1:5173/**. Vite chuyển `/api/auth/*`, `/api/seller/application`,
`/api/admin/seller-applications` tới Auth Service (`127.0.0.1:8001`), các
đường dẫn sản phẩm tới Product Service (`127.0.0.1:8002`). Không cần mở CORS
hay đưa mật khẩu database vào browser. Các trang hiện có: `/`, `/register`,
`/login`, `/account`, `/seller`, `/admin`, `/products`, `/products/:id`,
`/cart`, `/seller/products` và `/admin/products`.
Tạo admin bằng lệnh ở mục "Tạo admin lần đầu" bên dưới, không có tài khoản
admin mặc định. Sau khi admin duyệt seller, quay lại trang người bán và bấm
"Tải lại trạng thái" để xem kết quả. Hồ sơ và sản phẩm đọc/ghi MySQL local;
giỏ hàng chỉ lưu trên browser; đặt hàng chưa có.

```bash
cd frontend
npm run build
npx playwright install chromium   # chạy một lần trên máy mới
npm run test:e2e
```

Playwright mock các thao tác ghi nên không tạo user/hồ sơ/sản phẩm test trên
MySQL; test chỉ đọc `/api/health` và `/api/products` từ backend thật để kiểm
tra proxy. Cần cả Auth Service lẫn Product Service đang chạy để chạy toàn bộ
test. Browser lưu JWT trong
`sessionStorage` (mất khi đóng tab); logout xóa token trên browser, chưa có
server-side token revocation. Chỉ dùng môi trường local này để học và demo;
trước khi triển khai public cần thiết kế HTTPS và chính sách lưu token phù hợp.

### Ba khu vực giao diện

| Khu vực | Trang | Ai thấy |
|---|---|---|
| Mua sắm | `/`, `/products`, `/products/:id`, `/cart` | Khách, customer, seller, admin |
| Người bán | `/seller` | Customer nộp/theo dõi hồ sơ; seller quản lý shop |
| Người bán | `/seller/products` | Chỉ seller được duyệt |
| Quản trị | `/admin`, `/admin/products` | Chỉ admin |

Trang chủ `/` là **storefront dành cho người mua**: giới thiệu sản phẩm mới và
liên kết vào catalog/giỏ hàng. Kênh bán hàng chỉ là một liên kết phụ từ trang
mua sắm. Seller và admin có menu công việc riêng; seller vẫn được mua hàng.
Các trang đơn mua, đơn bán và quản trị đơn chưa có vì chưa có Order Service.
Menu công việc chỉ ghi “Sắp có”, không giả lập rằng đã đặt hàng được.

### Giỏ hàng frontend: cách thử

1. Từ trang chủ mở **Sản phẩm**, chọn sản phẩm seller đã đăng (hoặc bấm
   **Thêm vào giỏ** ngay trên thẻ sản phẩm).
2. Trên trang chi tiết, chọn số lượng rồi bấm **Thêm vào giỏ**.
3. Mở **Giỏ hàng** (`/cart`) để tăng/giảm số lượng, xóa và xem tổng **tạm tính**.
4. Thử sản phẩm từ seller khác; cả hai vẫn nằm trong cùng giỏ.
5. Reload trang: giỏ vẫn còn trên trình duyệt này. Đăng nhập tài khoản khác sẽ
   thấy giỏ của tài khoản đó, không thấy giỏ của tài khoản trước. Giỏ khách
   được giữ riêng và không tự gộp vào giỏ của tài khoản sau khi login.

Giỏ chỉ lưu `{ productId, quantity }` trong `localStorage` theo khóa guest hoặc
ID tài khoản; nó **không lưu giá, thông tin sản phẩm hay JWT**. Khi mở giỏ hoặc
bấm **Kiểm tra lại giá & tồn kho**, frontend lấy thông tin mới từ Product Service.
Sản phẩm đã ẩn/khóa/biến mất hoặc vượt tồn kho được đánh dấu để xóa/chỉnh số
lượng. Tổng tiền chỉ là hiển thị dự kiến (tính bằng số nguyên cents, không tính
tiền qua float); backend phải tính lại giá/tồn kho lúc tạo order.

Nút **Đặt hàng — sắp ra mắt** cố ý bị vô hiệu hóa: chưa có Order Service nên
không có đơn nào được ghi vào database, chưa trừ kho và chưa có thanh toán giả.
Giỏ local ở guest và mỗi user trên cùng browser chỉ là trạng thái giao diện,
không đồng bộ giữa thiết bị. Trên máy dùng chung, guest kế tiếp có thể thấy
giỏ guest cũ vì browser vẫn giữ `localStorage`.

## Milestone 1: Nền tảng Auth local

Yêu cầu: Docker Desktop đang chạy và Docker Compose v2.

1. Mở terminal tại thư mục `microshop`.
2. Nếu chưa có `.env`, sao chép `.env.example` thành `.env` và điền mật khẩu local.
   Sinh `JWT_SECRET` bằng `openssl rand -hex 32` và điền vào `.env` (không commit).
3. Chạy:

```bash
docker compose config --quiet
docker compose up -d --build --wait
docker compose ps
```

Swagger: http://localhost:8001/docs

| Endpoint | Ý nghĩa |
|---|---|
| `POST /auth/register` | Đăng ký customer; không nhận role admin từ client |
| `POST /auth/login` | JSON email/password → JWT, token_type, expires_in |
| `GET /auth/me` | Bearer JWT → thông tin tài khoản hiện tại |
| `GET /health` | Process HTTP đang hoạt động (liveness) |
| `GET /ready` | Kết nối database thành công; lỗi database trả HTTP 503 |

Ví dụ kiểm tra:

```bash
curl --fail http://localhost:8001/health
curl --fail http://localhost:8001/ready
```

Trong Swagger, thử đăng ký username/email mới; lần đầu trả 201, đăng ký
lại cùng email/username trả 409. Response không chứa password/hash.

## Cấu hình và dữ liệu hiện có

- `.env` tại root là cấu hình local và được `.gitignore` loại trừ.
- `.env.example` chỉ chứa placeholder để chia sẻ.
- Compose truyền biến môi trường vào container; FastAPI không tự đọc file `.env`.
- Container gọi database qua `mysql:3306`; từ Mac dùng `127.0.0.1:3307`.
- Chỉ bind các cổng local vào loopback, không expose lên mạng LAN.
- Volume `mysql_data` được giữ nguyên khi chạy `docker compose down`.
- Không dùng `docker compose down -v` nếu muốn giữ dữ liệu.
- Với volume cũ, phải giữ credential đã khởi tạo. Đổi mật khẩu trong `.env`
  **không** tự đổi mật khẩu trong MySQL. Cần thay đổi tài khoản DB có kiểm soát.
- `services/.env` cũ không được sử dụng bởi cấu hình mới.

## Kiểm thử cấu hình và authentication

Chạy test trong container riêng. Test authentication chạy qua HTTP với database
SQLite in-memory; test readiness dùng mock connection. Không đọc/ghi MySQL thật:

```bash
docker compose run --rm --no-deps \
  -e DATABASE_URL=sqlite:// \
  -v "$PWD/services/auth-service/tests:/tests:ro" \
  auth-service python -m unittest discover -s /tests -v
```

## Debug

```bash
docker compose logs --tail 100 auth-service mysql
docker compose ps
```

Nếu MySQL unhealthy, kiểm tra credential với volume hiện có trước khi đổi
cấu hình. Không xóa volume để xử lý lỗi kết nối.

## Luồng khởi động

```text
Compose đọc .env → MySQL khởi động → SELECT 1 healthcheck thành công
→ Auth khởi động → tạo bảng còn thiếu ở lifespan → /ready thành công
```

`create_all` hiện chỉ phục vụ bootstrap local, không thay thế migration khi
thay đổi schema. Chưa có retry tự động ở app ngoài cơ chế restart của Compose.

## Tiếp theo

Order Service để xác nhận giỏ hàng nhiều seller, tạo đơn và thanh toán mô phỏng.
Mỗi milestone có test và hướng dẫn kiểm tra riêng.

## Thử login và JWT trong Swagger

1. Mở http://localhost:8001/docs.
2. `POST /auth/register`: tạo customer với username, email và password.
3. `POST /auth/login`: gửi email/password vừa tạo.
4. Sao chép `access_token`, bấm **Authorize**, dán token (không thêm chữ Bearer).
5. Gọi `GET /auth/me`: trả thông tin tài khoản, không có password/hash.
6. Bấm Logout trong hộp Authorize rồi gọi `/auth/me`: trả 401.

Login sai email/password trả cùng thông báo 401. Token hết hạn, chữ ký sai
hoặc tài khoản không còn tồn tại đều bị từ chối. Access token mặc định có hạn
30 phút. Chưa triển khai refresh token hoặc thu hồi token phía server; logout
client chỉ xóa token phía client.

Password bcrypt bị giới hạn **72 byte UTF-8**, không chỉ 72 ký tự. Input vượt
giới hạn trả 422 thay vì bị cắt ngắn. Đăng ký hiện chỉ tạo customer; gửi thêm
`role=admin` bị từ chối. Helper `require_roles` bảo vệ các API admin và seller.

Luồng xác thực:

```text
Login → tìm email trong auth_db → verify bcrypt → ký JWT (sub, iat, exp, iss, aud)
/auth/me → verify chữ ký và claims → lấy user/role hiện tại từ DB → response
```

## Marketplace: đăng ký và duyệt seller

### Quy tắc nghiệp vụ

- Đăng ký tài khoản luôn tạo `customer`.
- Customer gửi hồ sơ bán hàng gồm tên shop và mô tả; trạng thái ban đầu là `pending`.
- Chỉ admin được duyệt. Khi duyệt, hồ sơ chuyển `approved`, tài khoản chuyển `seller`.
- Seller vẫn có thể sử dụng các chức năng mua hàng khi chúng được triển khai.
- Từ chối hồ sơ giữ role `customer`; người dùng có thể sửa thông tin và gửi lại.
- Tạm ngưng seller chuyển role về `customer`, hồ sơ thành `suspended`.
  Người dùng vẫn đăng nhập/mua hàng được, nhưng không còn quyền bán hàng.
- Seller bị tạm ngưng không được gửi hồ sơ mới để vượt qua quyết định của admin.
- Admin có thể duyệt lại hồ sơ suspended để khôi phục quyền seller.
- Role được đọc từ database trên mỗi request; token cũ không giữ quyền seller
  sau khi bị tạm ngưng. Tính chất này hiện áp dụng trong Auth Service; các
  service tương lai phải có cơ chế kiểm tra quyền hiện tại tương ứng.

| Endpoint | Quyền | Kết quả |
|---|---|---|
| `POST /seller/application` | customer | Tạo hồ sơ hoặc gửi lại hồ sơ rejected; HTTP 201 |
| `GET /seller/application` | Đã đăng nhập | Chỉ xem hồ sơ của chính mình; chưa có → 404 |
| `GET /seller/profile` | seller đã duyệt | Hồ sơ shop đã duyệt; chưa có quyền → 403 |
| `GET /admin/seller-applications` | admin | Danh sách phân trang, có filter status |
| `POST /admin/seller-applications/{id}/review` | admin | Duyệt, từ chối hoặc tạm ngưng |

Danh sách hỗ trợ `status`, `offset` (mặc định 0), `limit` (mặc định 20, tối đa 100).
Response gồm `items`, `total`, `offset`, `limit`.

### Tạo admin lần đầu

Tại thư mục `microshop`, sau khi container healthy, chạy:

```bash
docker compose exec auth-service python -m app.create_admin
```

Nhập username, email, password và xác nhận password. Mật khẩu không hiển thị
trên terminal, không truyền qua command-line argument và không có mật khẩu
admin mặc định. Dùng username/email mới: lệnh sẽ từ chối nếu đã tồn tại, không
tự nâng quyền hoặc ghi đè password tài khoản cũ. Không có API public tạo admin.

### Demo trên Swagger

1. Tạo admin bằng lệnh trên.
2. Đăng ký customer bằng `/auth/register`, đăng nhập bằng `/auth/login`.
3. Bấm **Authorize**, dùng access token customer.
4. Gửi `POST /seller/application`:

```json
{
  "shop_name": "Blue Tech Shop",
  "description": "Cửa hàng phụ kiện công nghệ dành cho sinh viên."
}
```

5. Ghi lại `id` hồ sơ, gọi `/seller/application` để thấy `pending`.
   Gọi `/seller/profile` lúc này trả 403.
6. Đăng nhập tài khoản admin, đổi token trong **Authorize** sang token admin.
7. Gọi `/admin/seller-applications?status=pending`.
8. Gửi `POST /admin/seller-applications/{id}/review`:

```json
{
  "action": "approve",
  "note": "Thông tin shop hợp lệ, cho phép bán hàng."
}
```

9. Chuyển lại token customer ban đầu. `/auth/me` trả role `seller` và
   `/seller/profile` trả HTTP 200.
10. Admin có thể gửi `action: "suspend"` kèm lý do; dùng lại token seller cũ
    để xác nhận `/seller/profile` trả 403 và `/auth/me` trả `customer`.

Các chuyển trạng thái hợp lệ:

```text
pending   --approve--> approved (seller)
pending   --reject---> rejected (customer)
rejected  --gửi lại--> pending  (customer)
approved  --suspend--> suspended (customer)
suspended --approve--> approved (seller)
```

Chuyển trạng thái khác trả 409. Request review phải có lý do (`note`). Client
không được truyền `user_id`, `status` hay `role` khi gửi hồ sơ; server lấy chủ
sở hữu từ token. Mỗi tài khoản có tối đa một hồ sơ.

### Dữ liệu và kiểm thử

- Bảng mới `seller_applications` tham chiếu bảng `users`; không thay đổi các
  cột hay xóa dữ liệu `users` hiện có.
- Bootstrap local tạo bảng mới khi Auth khởi động. Khi thay đổi cấu trúc bảng
  đã có, cần migration phiên bản hóa thay vì chỉ dựa vào `create_all`.
- Cập nhật status hồ sơ và role tài khoản nằm trong cùng transaction.
- MySQL dùng row lock để tuần tự hóa cập nhật cùng hồ sơ/tài khoản; test SQLite
  hiện kiểm tra luồng HTTP và phân quyền, chưa chứng minh hành vi đồng thời MySQL.
- Hồ sơ chỉ lưu lần review gần nhất (`reviewed_by`, `reviewed_at`, `review_note`),
  chưa phải lịch sử audit đầy đủ. Gửi lại hồ sơ rejected xóa kết quả review cũ.
- Bộ test có luồng approve/suspend/reactivate, reject/resubmit, phân quyền,
  ownership, pagination, chống tự gán role/status và tạo admin không ghi đè user.

## Marketplace: danh mục và quản lý sản phẩm

Product Service chạy cổng local `127.0.0.1:8002`, Swagger tại
**http://127.0.0.1:8002/docs**. Khi chạy `docker compose up -d --build --wait`,
service `product-db-setup` tạo `product_db` nếu chưa có và cấp quyền trên DB
này cho MySQL user đang dùng, **không xóa `auth_db` hay volume hiện có**. Local
hiện dùng chung tài khoản MySQL nhưng mỗi service chỉ kết nối DB thuộc quyền
sở hữu của mình; trước khi public production nên cấp riêng credentials/permissions.

| API | Quyền | Chức năng |
|---|---|---|
| `GET /products` | Công khai | Tìm `search`, lọc `category`, `seller_id`, phân trang `offset/limit`; chỉ active |
| `GET /products/{id}` | Công khai | Xem sản phẩm active; ẩn/khóa trả 404 |
| `GET /seller/products` | seller | Xem cả sản phẩm đã ẩn/khóa của bản thân |
| `POST /seller/products` | seller | Đăng sản phẩm mới |
| `PUT /seller/products/{id}` | seller sở hữu | Sửa sản phẩm; sản phẩm blocked trả 409 |
| `PATCH /seller/products/{id}/visibility` | seller sở hữu | Chuyển active/hidden; blocked trả 409 |
| `GET /admin/products` | admin | Xem mọi sản phẩm |
| `PATCH /admin/products/{id}/visibility` | admin | Khóa (`blocked`) / mở (`active`) |

Product Service không đọc bảng `users`/`seller_applications` trực tiếp và không
tin `seller_id` hay `role` từ client. Với request cần quyền, Product Service
gửi JWT đến Auth Service `/auth/me` để lấy id và role hiện tại; Auth không hoạt
động thì trả HTTP 503, không tự chấp nhận token. Seller mất quyền sau khi bị
tạm ngưng không thể sửa/đăng sản phẩm ngay cả khi JWT cũ còn hạn.

Hiện tại **sản phẩm đã active của seller bị tạm ngưng vẫn hiển thị trong catalog**.
Đây là giới hạn của milestone này; cần đồng bộ trạng thái seller hoặc kiểm tra
quyền người bán khi hiển thị catalog ở giai đoạn tiếp theo. Admin có thể khóa
sản phẩm thủ công trước đó. Seller không thể tự mở sản phẩm đã bị admin khóa.

### Thử trên web

1. Tạo tài khoản seller, nhờ admin duyệt (theo hướng dẫn ở trên).
2. Seller đăng nhập, mở **Kênh người bán → Quản lý sản phẩm**.
3. Nhập tên, mô tả, danh mục, giá (ví dụ `125000.00`), tồn kho và URL ảnh
   (tùy chọn). `image_url` chỉ nhận HTTP/HTTPS; chưa có upload file.
4. Mở **Sản phẩm** ở menu để thấy sản phẩm trong danh mục công khai.
5. Seller có thể sửa hoặc ẩn/hiện sản phẩm của mình; seller khác không được sửa.
6. Admin mở **Quản trị → Kiểm duyệt sản phẩm**, khóa sản phẩm và xác nhận
   sản phẩm biến mất khỏi catalog; seller không thể tự mở lại.

Giá lưu bằng `DECIMAL(12,2)`; client gửi dưới dạng chuỗi số thập phân, không
tính tiền bằng float. API trả giá dưới dạng chuỗi, frontend chỉ định dạng để
hiển thị. Khi có Order Service, giá tại thời điểm đặt hàng sẽ được snapshot.

### Kiểm thử Product Service không chạm MySQL local

```bash
docker compose run --rm --no-deps \
  -e DATABASE_URL=sqlite:// \
  -v "$PWD/services/product-service/tests:/tests:ro" \
  product-service python -m unittest discover -s /tests -v
```

Test dùng SQLite trong memory và identity giả lập để kiểm tra nghiệp vụ, role,
ownership, giá, tìm kiếm, ẩn/khóa và phân trang. Vì Auth Service được giả lập
ở các test này, cần thử thêm luồng seller trên web local với Auth Service thật
trước khi triển khai public. Truy cập Product Service không có token hoặc
token sai trả 401 từ Auth Service, không chấp nhận `seller_id` do client tự gửi.

### Giới hạn schema

`create_all` chỉ bootstrap bảng `products` trong DB mới, **không phải hệ thống
migration**. Thay đổi cấu trúc bảng đã có cần Alembic. Catalog hiện không có
order/cart, nên trường tồn kho chưa tự động giảm. Trang admin tải tối đa 100
sản phẩm, cần phân trang thực tế nếu dữ liệu nhiều hơn.
# microshop
