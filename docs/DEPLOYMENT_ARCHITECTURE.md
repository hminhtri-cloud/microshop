# Deployment Architecture — Docker Compose, Kubernetes và AWS

Tài liệu này chốt kiến trúc triển khai theo từng môi trường. **Docker Compose là môi trường local đang dùng. Kubernetes/AWS là kiến trúc mục tiêu, chưa được triển khai trong repo.** Không dùng sơ đồ mục tiêu để nói rằng EKS, RDS hay production gateway đã chạy.

## 1. Quyết định kiến trúc

| Môi trường | Quyết định | Phạm vi |
|---|---|---|
| Local/dev | Docker Compose | Chạy backend và MySQL trên một máy; frontend chạy Vite ngoài Compose |
| CI | Docker build + test | Build image/service, backend tests, frontend build/E2E theo workflow |
| Production target | Kubernetes trên AWS EKS | Chạy stateless frontend/backend; dùng AWS managed services cho image, DB, secret và load balancer |
| Production database | Amazon RDS for MySQL | Một RDS instance với database logic riêng cho MVP; tách instance khi yêu cầu tải/tuân thủ tăng |
| Public entrypoint | AWS ALB + Ingress | Cùng public contract `/api/*` như gateway routing; không expose service port riêng |

Lý do chọn: Compose đủ đơn giản cho học tập/demo; EKS đáp ứng mục tiêu Kubernetes nhưng không đưa database vào pod. RDS, ECR, Secrets Manager và ALB giảm phần vận hành tự xây. Nếu milestone chỉ yêu cầu local/demo, **không cần tạo EKS**; hoàn thành Compose và tài liệu là đủ.

## 2. Kiến trúc local hiện tại

```text
Browser :5173
   │
   └── Vite proxy /api
          ├── Auth Service :8001 → auth logic DB
          └── Product Service :8002 → product_db

Docker Compose network: microshop-network
   ├── mysql :3306 (host bind 127.0.0.1:3307)
   ├── auth-service :8000 (host 127.0.0.1:8001)
   ├── product-db-setup (one-shot init product_db)
   └── product-service :8000 (host 127.0.0.1:8002)
```

### Trạng thái Compose

- `mysql:8.4` là một container dùng volume `mysql_data`; hiện giữ nhiều database logic theo cấu hình local.
- `auth-service` chờ MySQL healthy, có `/health`/`/ready`, build từ `services/auth-service/Dockerfile`.
- `product-db-setup` chạy script khởi tạo `product_db` trước Product Service.
- `product-service` gọi Auth qua `http://auth-service:8000`, không gọi host port.
- Healthcheck và `depends_on` dùng để kiểm tra thứ tự khởi động, không thay thế migration/backup/monitoring.
- Frontend chưa có container trong Compose; chạy bằng `npm run dev` ở host trên port `5173`.
- Order Service chưa có trong Compose vì chưa có `main.py`, Dockerfile, router, migration/runtime và `order_db` local.

Lệnh local chuẩn:

```bash
cp .env.example .env
docker compose up -d --build --wait
cd frontend
npm ci
npm run dev
```

Các port bind chỉ trên `127.0.0.1`; không mở Auth/Product trực tiếp ra mạng LAN. Không commit `.env`, JWT secret, database password hoặc volume data.

## 3. Compose target sau khi có Order

```text
microshop-mysql :3306
   ├── auth-service :8000       → auth_db
   ├── product-service :8000    → product_db
   └── order-service :8000      → order_db

Frontend/Vite :5173
   ├── /api/auth*       → auth-service
   ├── /api/products*   → product-service
   └── /api/orders*     → order-service
```

Order gọi Auth/Product qua tên service trong network Compose:

```text
ORDER_AUTH_URL=http://auth-service:8000
ORDER_PRODUCT_URL=http://product-service:8000
```

Stock reservation và seller eligibility là service-to-service; không publish `/internal/*` ra host/gateway. Mỗi service phải có health/readiness riêng. Khi thêm Order, cần issue #4 trước rồi mới bật proxy `ORDER_API_TARGET` và checkout frontend.

## 4. Kubernetes target

### Namespace và workload

```text
Namespace: microshop
   ├── frontend Deployment + Service
   ├── auth-service Deployment + Service
   ├── product-service Deployment + Service
   └── order-service Deployment + Service

Ingress / AWS ALB
   ├── /              → frontend Service
   └── /api/*         → backend service theo path
```

Mỗi stateless app có:

- `Deployment` với image tag bất biến, không dùng `latest`.
- `Service` dạng `ClusterIP`; không dùng `NodePort` cho public traffic.
- `readinessProbe` để chỉ nhận traffic sau khi app sẵn sàng; `livenessProbe` để restart process lỗi.
- Resource `requests`/`limits` tối thiểu; HPA chỉ thêm sau khi có metric và load test.
- `PodDisruptionBudget` cho service cần chạy nhiều replica khi production thật.
- `NetworkPolicy` chỉ cho frontend/gateway gọi public backend và chỉ cho Order gọi internal Auth/Product theo cần thiết.

### Database trên Kubernetes

Không chạy MySQL production trong Deployment/StatefulSet của app cluster cho MVP. Database dùng RDS; các pod chỉ nhận hostname, database name và credential từ Secret. Migration chạy trong Job/CI release step có lock và backup trước khi thay đổi schema.

Nếu chạy Kubernetes hoàn toàn local bằng kind/minikube cho học tập, có thể dùng MySQL StatefulSet riêng, nhưng đó **không** phải thiết kế production và không được dùng chung volume với Compose.

### Ingress routing

```text
https://shop.example.com/       → frontend
https://shop.example.com/api/auth/*
https://shop.example.com/api/seller/application
https://shop.example.com/api/admin/seller-applications*
                                  → auth-service
https://shop.example.com/api/products*
https://shop.example.com/api/seller/products*
https://shop.example.com/api/admin/products*
                                  → product-service
https://shop.example.com/api/orders*
https://shop.example.com/api/seller/orders*
https://shop.example.com/api/admin/orders*
                                  → order-service
```

Ingress giữ nguyên prefix `/api` public và rewrite bỏ prefix trước khi service nhận request. Không route `/internal/*` qua Ingress. Chi tiết header/error giữ theo [Gateway routing](GATEWAY_ROUTING.md).

## 5. AWS target

```text
Route 53 DNS
    ↓
ACM TLS certificate
    ↓
Public ALB / AWS Load Balancer Controller
    ↓
EKS cluster (private worker subnets)
    ├── frontend pods
    ├── auth/product/order pods
    └── ClusterIP services

ECR                  RDS MySQL
container images     auth_db/product_db/order_db

Secrets Manager      CloudWatch / Prometheus
JWT/DB/service creds  logs, metrics, alerts
```

### Thành phần AWS đã chọn

| Thành phần | Dùng cho | Quyết định |
|---|---|---|
| EKS | Kubernetes control plane/workloads | Production target; không cần cho local milestone |
| ECR | Lưu image Auth/Product/Order/frontend | Tag bằng git SHA, scan image, không dùng `latest` |
| RDS MySQL | Database managed, backup, patching | Multi-AZ/backup theo môi trường; MVP có thể một instance và 3 logical DB |
| ALB + AWS Load Balancer Controller | HTTPS/public routing | Terminate TLS tại ALB; route `/` và `/api/*` |
| Route 53 | DNS | `shop.example.com` trỏ ALB |
| ACM | TLS certificate | Tự renew certificate |
| Secrets Manager | JWT secret, DB/service credentials | Đồng bộ vào Kubernetes Secret qua External Secrets hoặc release mechanism tương đương |
| CloudWatch | Log/metric/alarm | Không log token, password, payment data |
| S3/CloudFront (tùy chọn) | Static frontend assets | Chỉ dùng nếu frontend build tách khỏi frontend pod; không bắt buộc MVP |
| NAT Gateway/VPC endpoints | EKS private subnet egress | Chốt theo ngân sách; NAT có chi phí cố định đáng kể |

### Network

- VPC tối thiểu có public subnet cho ALB và private subnet cho EKS nodes/RDS.
- RDS security group chỉ cho phép traffic từ EKS node/pod security group tới port MySQL.
- Không mở MySQL tới `0.0.0.0/0`; không public IP cho RDS.
- EKS pod không truy cập DB qua public address; dùng private DNS/endpoint.
- ALB chỉ mở `443` public; redirect `80` sang `443` nếu cần.
- Service-to-service dùng Kubernetes DNS và credential riêng; JWT của customer không thay thế credential nội bộ.

## 6. Environment configuration

| Config | Compose local | Kubernetes/AWS |
|---|---|---|
| Service discovery | `auth-service`, `product-service`, `mysql` | ClusterIP DNS, RDS private endpoint |
| JWT secret | `.env` local, không commit | Secrets Manager → K8s Secret |
| DB password | `.env` local | Secrets Manager/rotation |
| Image | Docker build tại máy | ECR image tag theo commit SHA |
| Public URL | `127.0.0.1:5173` | HTTPS domain qua ALB |
| Frontend API | Vite proxy | Same-origin `/api` qua Ingress |
| Logs | Docker logs | CloudWatch/central logging |
| Data backup | Local volume, demo only | RDS automated backup/PITR và restore test |

Không dùng cùng JWT secret/database password giữa dev, staging và production. `.env.example` chỉ chứa tên biến và placeholder không có credential thật.

## 7. CI/CD target

```text
Pull Request
  → backend tests + frontend build + E2E
  → Docker build/scan

Merge develop/main
  → push immutable images to ECR
  → run migration approval step
  → deploy Helm/Kustomize to staging
  → smoke test health/readiness and /api
  → manual approval for production
  → rolling deployment
```

- Migration là bước release có kiểm soát, không chạy ngầm trong mỗi pod startup.
- Deploy từng service độc lập nhưng contract/API client phải cùng PR khi breaking change.
- Rollback image về git SHA trước đó; database migration phải backward-compatible hoặc có kế hoạch rollback riêng.
- Smoke test tối thiểu: frontend tải được, `/api/health`/`/ready`, Auth login, Product catalog, Order health sau khi Order hoàn thành.

## 8. Observability và vận hành

- Mỗi service expose liveness/readiness; readiness phải kiểm tra dependency cần thiết, không chỉ process sống.
- Log JSON gồm service, environment, level, timestamp, route, status, duration và request ID.
- Không log `Authorization`, password, JWT, database URL, payment secret hoặc toàn bộ shipping PII.
- Alert cho pod crash loop, readiness fail, 5xx tăng, DB connection exhausted, latency và disk/CPU.
- Order reservation cần metric cho reserve/release/expire/reconciliation; đây là metric nghiệp vụ quan trọng hơn chỉ CPU.
- RDS backup/restore phải được kiểm tra định kỳ; volume Compose chỉ phục vụ local demo.

## 9. Security baseline

- Image chạy non-root, base image tối giản, scan dependency/image trong CI.
- Pin version image/dependency; không dùng `latest` production.
- Secret chỉ inject runtime; không commit vào Git, Docker image layer hoặc frontend bundle.
- TLS public bằng ACM; service nội bộ không public IP.
- RBAC Kubernetes tối thiểu; namespace tách environment nếu dùng chung cluster.
- NetworkPolicy và security group theo least privilege.
- Rate limit login/order tại gateway; giới hạn body/request timeout.
- Backend vẫn kiểm tra role/ownership; gateway và React route guard không phải authorization.

## 10. Phạm vi triển khai theo milestone

### Hiện tại

- Hoàn thiện Compose cho MySQL/Auth/Product và chạy frontend Vite ngoài Compose.
- Giữ public frontend contract `/api` qua Vite proxy.
- Không triển khai Kubernetes/AWS chỉ để chứng minh sơ đồ.

### Milestone tiếp theo

1. Hoàn thiện Order Service runtime, Dockerfile, order_db và Compose service.
2. Thêm reservation/idempotency và smoke/integration test trong Compose.
3. Tạo Docker images immutable và CI build/scan.
4. Tạo Kubernetes manifests/Helm hoặc Kustomize cho staging local/cloud.
5. Provision AWS VPC/ECR/RDS/EKS/ALB bằng Terraform hoặc công cụ IaC được nhóm chốt.
6. Deploy staging, test restore/rollback/health, rồi mới cân nhắc production.

## 11. Definition of Done

- Có thể dựng local bằng một lệnh Compose sau khi tạo `.env`.
- Mỗi container có healthcheck/readiness và không dùng hard-coded host port để gọi service nội bộ.
- Order không được coi là hoàn thành cho tới khi có trong Compose và smoke test.
- Kubernetes workload có Deployment, ClusterIP Service, probes, resource policy và Secret reference.
- AWS có private DB/network, TLS, image registry, logging và backup/restore plan.
- Public routing `/api` nhất quán giữa local, staging và production.
- Tài liệu ghi rõ thành phần nào đã chạy và thành phần nào chỉ là target architecture.

## 12. Tài liệu liên quan

- [Gateway routing](GATEWAY_ROUTING.md)
- [Frontend routes](FRONTEND_ROUTES.md)
- [API contract](API_CONTRACT.md)
- [Git workflow/CI](GIT_WORKFLOW.md)
- `docker-compose.yml`
