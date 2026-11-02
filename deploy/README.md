# Deployment

Thư mục này chứa manifest và lệnh triển khai ứng dụng theo môi trường.

```text
deploy/
├── compose/       # Compose override/profile cho local và CI
├── kubernetes/    # Kustomize base và overlays
└── scripts/       # Script kiểm tra/deploy không chứa secret
```

Trạng thái hiện tại:

- `docker-compose.yml` ở root là Compose baseline đang chạy.
- `deploy/compose/` mới là skeleton; Order Service chưa đủ runtime để thêm vào Compose.
- `deploy/kubernetes/` mới là Kustomize layout; chưa deploy cluster.
- AWS provisioning đặt ở `infrastructure/aws/terraform/`, không chạy tự động từ đây.

Xem [Deployment Architecture](../docs/DEPLOYMENT_ARCHITECTURE.md) trước khi thêm resource.
