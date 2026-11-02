# Docker Infrastructure

Docker Compose hiện tại ở `../../docker-compose.yml` chạy MySQL, Auth Service và Product Service. Frontend chạy Vite ngoài Compose.

Khi Order Service hoàn thành, bổ sung service vào Compose theo các nguyên tắc:

- Dùng DNS service, không gọi `127.0.0.1` giữa container.
- Có `healthcheck`, `depends_on` chỉ để điều phối startup, không thay migration.
- Không publish database hoặc service port ra ngoài localhost nếu không cần.
- Dùng `.env` local, không commit credential.
- Giữ `/api` public contract qua Vite proxy.

Các file Compose bổ sung sẽ đặt trong `deploy/compose/` để phân biệt cấu hình chạy với tài liệu image/build tại đây.
