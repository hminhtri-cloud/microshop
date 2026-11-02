# Kubernetes Deployments

Kubernetes target dùng Kustomize:

```text
deploy/kubernetes/
├── base/
│   ├── kustomization.yaml
│   ├── namespace.yaml             # dự kiến
│   ├── frontend/                  # Deployment + Service
│   ├── auth-service/              # Deployment + Service
│   ├── product-service/           # Deployment + Service
│   ├── order-service/             # Deployment + Service
│   └── ingress.yaml               # ALB ingress dự kiến
└── overlays/
    ├── local/
    ├── staging/
    └── production/
```

Mỗi workload cần readiness/liveness probe, resource requests/limits, image tag theo git SHA và Secret reference. Database production chạy RDS, không chạy MySQL trong app pod. `/internal/*` không được đưa vào Ingress public.

Chưa apply manifest vì Order Service chưa runtime và chưa chốt cluster/account/namespace thật.
