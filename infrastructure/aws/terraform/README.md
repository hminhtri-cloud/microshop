# AWS Terraform Placeholder

Đây là vị trí dành cho Terraform modules/workspaces sau này:

```text
terraform/
├── modules/
│   ├── network/
│   ├── ecr/
│   ├── rds/
│   └── eks/
└── environments/
    ├── staging/
    └── production/
```

Chưa có `.tf` resource nào để tránh tạo AWS ngoài ý muốn. Khi triển khai:

- Remote state dùng S3 + DynamoDB locking hoặc backend tương đương.
- Mỗi environment có state và account/role phù hợp.
- Secrets tham chiếu từ AWS Secrets Manager, không đặt plaintext trong `tfvars`.
- Chạy `terraform plan` và review trước `apply`.
