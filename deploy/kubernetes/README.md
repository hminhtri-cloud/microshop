# Kubernetes deployments

Thư mục này dùng Kustomize để mô tả các workload MicroShop.

```text
deploy/kubernetes/
├── base/
│   ├── namespace.yaml
│   ├── auth-service/
│   ├── product-service/
│   ├── order-service/
│   └── frontend/
└── overlays/
    └── local/
        ├── auth-config.yaml
        ├── mysql.yaml
        └── kustomization.yaml
```

`base` chứa Deployment và Service chung. Mỗi Service là `ClusterIP`, tức chỉ
nhận traffic bên trong cluster. `frontend` chạy Nginx với cấu hình
`frontend/nginx.conf`: nó định tuyến `/api/products` đến Product,
`/api/orders` đến Order, API còn lại đến Auth, và trả `404` cho
`/api/internal`.

Overlay `local` cung cấp ConfigMap, MySQL/PVC và Job bootstrap database. Đây
chỉ là môi trường Minikube; production phải dùng database được quản lý thay vì
MySQL Deployment này.

Xem [hướng dẫn local](overlays/local/README.md) trước khi apply. Secret không
được đưa vào Git.
