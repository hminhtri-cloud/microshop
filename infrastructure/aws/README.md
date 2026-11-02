# AWS Infrastructure

AWS là target architecture, chưa được provision. Thành phần dự kiến:

- VPC: public subnet cho ALB, private subnet cho EKS/RDS.
- ECR: lưu image bất biến theo git SHA.
- RDS MySQL: database managed, backup và restore test.
- EKS: chạy frontend/Auth/Product/Order stateless workloads.
- ALB + ACM + Route 53: HTTPS và `/api` routing.
- Secrets Manager: JWT, database và service credentials.
- CloudWatch: logs, metrics và alerts.

Terraform state, backend, account ID, private key và secret không được commit. IaC chỉ được thêm sau khi chốt AWS account, region, CIDR, budget và approval flow.
