# Compose Deployments

Root `docker-compose.yml` là local baseline. Thư mục này dành cho các file bổ sung, ví dụ:

```text
deploy/compose/
├── README.md
├── docker-compose.ci.yml       # dự kiến: test-only overrides
└── docker-compose.order.yml    # chỉ thêm sau khi Order Service có Dockerfile/runtime
```

Không tạo file override giả gọi tới service chưa tồn tại. Khi thêm Order:

```bash
docker compose -f docker-compose.yml -f deploy/compose/docker-compose.order.yml up -d --build --wait
```

Mọi override phải giữ network service discovery, healthcheck, volume ownership và không đưa secret vào file.
