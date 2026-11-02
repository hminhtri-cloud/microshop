# Infrastructure

Thư mục này chứa các quyết định và cấu hình hạ tầng theo môi trường. Đây là skeleton ban đầu; không commit secret, state Terraform hoặc manifest chứa credential thật.

```text
infrastructure/
├── docker/       # Quy ước image/build và Compose local
└── aws/
    └── terraform/ # IaC AWS dự kiến: VPC, ECR, RDS, EKS, ALB
```

Các workload deployment nằm trong `deploy/`. Kiến trúc đầy đủ: [Deployment Architecture](../docs/DEPLOYMENT_ARCHITECTURE.md).
