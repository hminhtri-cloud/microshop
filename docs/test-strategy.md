# MicroShop — Test Strategy

## 1. Mục tiêu

Kiểm tra nghiệp vụ quan trọng và bảo đảm phiên bản đóng gói có thể chạy
đúng trước khi triển khai.

Ưu tiên:
- Đúng quyền truy cập và quyền sở hữu dữ liệu.
- Đúng giá, tổng tiền và tồn kho.
- Retry không tạo đơn hoặc trừ/hoàn kho nhiều lần.
- Các service phối hợp đúng khi thành công, timeout hoặc lỗi.
- Website và API hoạt động qua điểm truy cập của môi trường triển khai.

## 2. Các nhóm kiểm thử

| Nhóm | Phạm vi | Trạng thái |
|---|---|---|
| Backend từng service | Auth, Product, Order; nghiệp vụ, validation, phân quyền | Đã có |
| Phối hợp service | HTTP thật giữa Auth/Product/Order với DB tạm | Đã có |
| MySQL đồng thời | Tranh mua món cuối, trùng key, hủy/thanh toán đồng thời | Đã có test và cấu hình CI; cần xác nhận kết quả chạy |
| Giao diện | Form, điều hướng, giỏ hàng, xử lý lỗi bằng Playwright | Đã có; phần lớn giả lập API |
| Bản đóng gói | Frontend Docker/Nginx và backend chạy cùng nhau | Chưa có bộ kiểm thử tự động |
| Vận hành | Update/rollback, backup/restore và tải hệ thống | Chưa triển khai |

SQLite hỗ trợ kiểm tra nghiệp vụ nhưng không thay thế kiểm thử khóa và
transaction đồng thời trên MySQL.

## 3. Tình huống bắt buộc

- Token sai/hết hạn bị từ chối; quyền hiện tại được kiểm tra.
- Buyer/seller không xem hoặc sửa dữ liệu thuộc người khác.
- Seller bị tạm ngưng không được nhận đơn mua mới qua checkout.
- Đơn nhiều seller được chia đúng; giá lấy từ Product và lưu snapshot.
- Một món không hợp lệ thì không giữ kho một phần của giỏ.
- Hai khách mua món cuối: chỉ một yêu cầu thành công, kho không âm.
- Cùng buyer/key/body: cùng đơn; cùng key nhưng body khác: trả 409.
- Hủy, thanh toán thất bại hoặc hết hạn: hoàn kho đúng một lần.
- Timeout/lỗi giữa các bước: có thể tiếp tục bằng key cũ.
- Seller chỉ xử lý phần đơn của mình sau khi thanh toán thành công.

## 4. Lịch chạy

### Khi mở Pull Request
- Kiểm tra Compose và build image.
- Chạy test backend, phối hợp service và MySQL đồng thời.
- Typecheck/build frontend và chạy Playwright.

### Trước khi phát hành
- Chạy chính các image sẽ được triển khai.
- Kiểm tra website, refresh trang con và API qua Nginx.
- Kiểm tra đường dẫn nội bộ không truy cập được qua website.

### Sau khi triển khai
- Kiểm tra health/readiness, trang chủ và API chính.
- Xác nhận phiên bản đang chạy.
- Khi có môi trường triển khai: kiểm tra update và rollback.

Các bước chưa có tự động hóa phải được ghi rõ, không coi là đã hoàn thành.

## 5. Dữ liệu và môi trường

- Chỉ dùng database tạm hoặc database dành riêng cho test.
- Không chạy test tạo/xóa bảng trên dữ liệu đang sử dụng.
- Test phải tự chuẩn bị dữ liệu và không phụ thuộc thứ tự chạy.
- Không dùng tài khoản, token hoặc secret production.
- Môi trường triển khai local hiện tại là Docker Compose; bổ sung kiểm tra
  Kubernetes khi có cluster.

## 6. Điều kiện chấp nhận và xử lý lỗi

- Các nhóm kiểm tra bắt buộc phải pass trước khi merge/phát hành.
- Test bị skip không được tính là đã kiểm tra thành công.
- Không tắt test lỗi hoặc dùng retry để che lỗi chưa rõ nguyên nhân.
- Khi lỗi, lưu kết quả test, log service và trace Playwright;
  không ghi secret hoặc thông tin cá nhân nhạy cảm.
- Kiểm tra sau deploy thất bại: dừng phát hành, điều tra và rollback
  khi phù hợp với thay đổi dữ liệu.

## 7. Ưu tiên tiếp theo

1. Xác nhận pipeline hiện tại chạy xanh, gồm các bài test MySQL.
2. Hoàn tất frontend Docker/Nginx.
3. Thêm kiểm thử Compose qua Nginx vào CI.
4. Bổ sung thu thập log backend khi CI thất bại.
5. Khi có deployment: thêm kiểm tra rollback và backup/restore.
