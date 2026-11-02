# MicroShop — Architecture Diagrams

Các diagram dưới đây mô tả kiến trúc tổng thể theo hai trạng thái:

- **Hiện tại:** frontend Vite gọi Auth/Product qua Vite proxy; Order chưa chạy.
- **Mục tiêu:** public gateway/ALB route `/api` tới Auth/Product/Order; service nội bộ phối hợp với database riêng logic.

Các đường nét đứt hoặc node có nhãn `DỰ KIẾN` chưa phải resource đang chạy. Chi tiết triển khai: [Deployment Architecture](DEPLOYMENT_ARCHITECTURE.md). Chi tiết URL gateway: [Gateway Routing](GATEWAY_ROUTING.md).

## 1. System context

```mermaid
flowchart LR
    Customer([Customer / Seller])
    Admin([Admin])
    Browser["Web Browser\nReact + Vite"]
    Gateway["Public Gateway\n/api/*"]
    Auth["Auth Service\nidentity + roles"]
    Product["Product Service\ncatalog + inventory"]
    Order["Order Service\norders + checkout"]
    AuthDB[("Auth DB")]
    ProductDB[("Product DB")]
    OrderDB[("Order DB")]

    Customer --> Browser
    Admin --> Browser
    Browser --> Gateway
    Gateway --> Auth
    Gateway --> Product
    Gateway -. "DỰ KIẾN" .-> Order
    Auth --> AuthDB
    Product --> ProductDB
    Order -. "DỰ KIẾN" .-> OrderDB
    Order -. "seller eligibility / identity" .-> Auth
    Order -. "price / stock reservation" .-> Product

    classDef current fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20;
    classDef planned fill:#fff8e1,stroke:#f57f17,color:#6d4c00,stroke-dasharray: 5 5;
    class Browser,Gateway,Auth,Product,AuthDB,ProductDB current;
    class Order,OrderDB planned;
```

**Ownership:** Auth owns users/roles/seller application; Product owns products and stock; Order owns orders, seller orders and item snapshots. No service reads another service's database directly.

## 2. Local runtime hiện tại

```mermaid
flowchart TB
    subgraph Host["Developer machine"]
        Browser["Browser :5173"]
        Vite["Vite dev/preview proxy\n/api"]
        Compose["Docker Compose network\nmicroshop-network"]
    end

    subgraph Services["Compose services"]
        Auth["auth-service :8000\nhost :8001"]
        Product["product-service :8000\nhost :8002"]
        Setup["product-db-setup\none-shot"]
        MySQL[("mysql:8.4\nhost :3307\nvolume: mysql_data")]
    end

    Browser --> Vite
    Vite -->|"/api/auth/*\n/api/seller/application\n/api/admin/seller-*"| Auth
    Vite -->|"/api/products*\n/api/seller/products*\n/api/admin/products*"| Product
    Auth --> MySQL
    Setup -->|"init product_db"| MySQL
    Product --> MySQL
    Product -->|"AUTH_SERVICE_URL\nhttp://auth-service:8000"| Auth
    Auth -. "health /ready" .-> Vite
    Product -. "health /ready" .-> Vite

    Missing["Order Service\nCHƯA CÓ TRONG COMPOSE"]
    Vite -. "DỰ KIẾN /api/orders*" .-> Missing
```

Hiện frontend chạy ngoài Compose; chỉ Auth/Product/MySQL đang có container. `product-db-setup` chỉ khởi tạo database, không phải service xử lý request.

## 3. Public request flow mục tiêu

```mermaid
sequenceDiagram
    participant B as Browser
    participant G as Gateway / ALB
    participant A as Auth Service
    participant P as Product Service
    participant O as Order Service
    participant DBa as Auth DB
    participant DBp as Product DB
    participant DBo as Order DB

    B->>G: POST /api/orders + JWT + Idempotency-Key
    G->>O: POST /orders
    O->>A: Verify buyer / seller eligibility (internal auth)
    A->>DBa: Read current user/role/status
    A-->>O: Authorized identity
    O->>P: Reserve batch stock (internal, idempotent)
    P->>DBp: Lock products and reserve atomically
    P-->>O: Product/seller/price snapshots
    O->>DBo: Save order + seller_orders + items
    O-->>G: 201 OrderDetail
    G-->>B: 201 OrderDetail

    Note over B,DBo: Browser never calls internal Auth/Product reservation endpoints.
```

Nếu bước ghi Order DB thất bại sau khi reserve, Order release/reconcile **cùng reservation key**. Không tạo reservation mới khi timeout chưa rõ kết quả.

## 4. Kubernetes/AWS target

```mermaid
flowchart TB
    User([User]) --> DNS["Route 53\nshop.example.com"]
    DNS --> TLS["ACM TLS"]
    TLS --> ALB["AWS ALB / Ingress\nHTTPS + /api routing"]

    subgraph EKS["AWS EKS - private workloads"]
        Frontend["Frontend Deployment\nService: ClusterIP"]
        AuthSvc["Auth Deployment\nService: ClusterIP"]
        ProductSvc["Product Deployment\nService: ClusterIP"]
        OrderSvc["Order Deployment\nService: ClusterIP"]
        InternalNet["NetworkPolicy\nservice-to-service only"]
    end

    ALB -->|"/"| Frontend
    ALB -->|"/api/auth/*\n/api/seller/application\n/api/admin/seller-*"| AuthSvc
    ALB -->|"/api/products*\n/api/seller/products*\n/api/admin/products*"| ProductSvc
    ALB -->|"/api/orders*\n/api/seller/orders*\n/api/admin/orders*"| OrderSvc
    OrderSvc -->|"internal only"| AuthSvc
    OrderSvc -->|"internal only"| ProductSvc
    AuthSvc --> RDS[("Amazon RDS MySQL\nauth_db")]
    ProductSvc --> RDS2[("Amazon RDS MySQL\nproduct_db")]
    OrderSvc --> RDS3[("Amazon RDS MySQL\norder_db")]
    ECR["Amazon ECR\nimmutable image tags"] --> EKS
    Secrets["Secrets Manager\nJWT + DB + service creds"] --> EKS
    EKS --> Logs["CloudWatch\nlogs + metrics + alarms"]

    classDef aws fill:#e3f2fd,stroke:#1565c0,color:#0d47a1;
    classDef data fill:#f3e5f5,stroke:#6a1b9a,color:#4a148c;
    classDef security fill:#fff3e0,stroke:#ef6c00,color:#e65100;
    class DNS,TLS,ALB,EKS,Frontend,AuthSvc,ProductSvc,OrderSvc,InternalNet,ECR,Logs aws;
    class RDS,RDS2,RDS3 data;
    class Secrets security;
```

### Target deployment boundaries

- ALB là public entrypoint duy nhất; service dùng `ClusterIP`, không public NodePort.
- RDS nằm ngoài EKS workload; pod không chạy MySQL production.
- ECR chứa image theo git SHA; không dùng `latest` production.
- Secrets Manager cấp secret runtime; không đưa secret vào image, Git hoặc frontend bundle.
- `/internal/*` không có Ingress route; chỉ Order gọi Auth/Product bằng service credential.
- Frontend giữ cùng URL `/api` ở local, staging và production; chỉ thay proxy/gateway target.

## 5. CI/CD flow

```mermaid
flowchart LR
    PR["Pull Request"] --> Tests["Backend tests\nFrontend build/E2E"]
    Tests --> Build["Build + scan images"]
    Build --> ECR["Push ECR\ngit SHA tag"]
    ECR --> Staging["Deploy staging\nKubernetes overlay"]
    Staging --> Smoke["Smoke test\nhealth/readiness + /api"]
    Smoke --> Approval{ "Manual approval" }
    Approval -->|"approved"| Prod["Deploy production\nrolling update"]
    Approval -->|"rejected"| Stop["Stop / fix"]
    Prod --> Monitor["CloudWatch\nalerts + rollback"]
```

Migration database là release step có kiểm soát, không chạy ngầm trong mỗi pod startup. Rollback image dùng git SHA trước đó; schema migration phải backward-compatible.

## 6. Diagram legend

| Ký hiệu | Ý nghĩa |
|---|---|
| Mũi tên liền | Luồng đang có hoặc luồng runtime chính |
| Mũi tên nét đứt | Luồng dự kiến/internal cần triển khai |
| Node vàng | Thành phần chưa chạy hoặc cần chốt thêm |
| Node xanh | Thành phần hiện có/đã chốt trong kiến trúc |
| Gateway/ALB | Public routing, không thay thế authorization |
| Database | Chỉ service sở hữu được đọc/ghi trực tiếp |

## 7. Review checklist

- [ ] Diagram local khớp `docker-compose.yml` và `frontend/vite.config.ts`.
- [ ] Order chỉ được chuyển từ nét đứt sang runtime sau khi issue #4/#5 và dependencies hoàn thành.
- [ ] Public route giữ `/api`; internal reservation không xuất hiện trong gateway.
- [ ] Mỗi service có database ownership rõ ràng, không dùng cross-database foreign key.
- [ ] Kubernetes dùng readiness/liveness, resource limits, Secret reference và ClusterIP.
- [ ] AWS dùng private RDS, ECR immutable tags, ALB TLS và logging.
- [ ] Cập nhật diagram trong cùng PR khi thêm service, route hoặc thay đổi deployment boundary.

## 8. Tài liệu liên quan

- [Deployment Architecture](DEPLOYMENT_ARCHITECTURE.md)
- [Gateway Routing](GATEWAY_ROUTING.md)
- [API Contract](API_CONTRACT.md)
- [Frontend Routes](FRONTEND_ROUTES.md)
- [Infrastructure structure](../infrastructure/README.md)
- [Deployment structure](../deploy/README.md)
