# Handoff CI, registry và GitOps

Tài liệu này ghi nhận ranh giới giữa pipeline do A phụ trách, registry/AWS do B
phụ trách, và manifest GitOps local do C phụ trách.

## Hiện trạng đã kiểm tra

`.github/workflows/image-security.yml` build bốn image (Auth, Product, Order,
frontend) và scan Trivy `HIGH,CRITICAL` trên pull request và push vào
`develop`/`main`. Image có tag `${{ github.sha }}` trong job, nhưng chỉ là
artifact tạm của runner: workflow không đăng nhập hay push registry.

`exit-code: "0"` khiến report Trivy được upload 14 ngày nhưng lỗ hổng
HIGH/CRITICAL không làm job fail. Vì vậy status xanh không chứng minh image
không có lỗ hổng. Workflow cũng không chạy khi push thuần vào feature branch;
pull request hướng `develop`/`main` mới kích hoạt.

## Phần local hoàn thành

`deploy/kubernetes/overlays/local/kustomization.yaml` ghim tag image local,
và Argo Application theo dõi chính nhánh feature. `minikube image load` chỉ
chứng minh image có trong node local; nó không phải delivery pipeline hoàn
chỉnh, không có registry hay provenance từ CI.

## Cần A xác nhận/cung cấp

1. Chính sách trigger cho feature branch/PR và ngưỡng severity nào phải fail.
2. Quy tắc tag bất biến (commit SHA/digest), SBOM, signing và policy review
   report Trivy trước khi promote.
3. Quyền/secrets CI tối thiểu để login registry, push image và cập nhật
   manifest qua PR; không đưa credential vào repository.

## Cần B xác nhận/cung cấp

1. Registry/ECR repository, region, lifecycle policy và IAM role/OIDC cho CI.
2. Chuẩn image URL theo môi trường và quy trình promote digest từ local/dev
   sang AWS.
3. Terraform ownership cho registry, IAM và hạ tầng runtime; C không tạo AWS
   resource trong phạm vi local.

Khi A/B cung cấp các quyết định trên, C có thể thay tag local bằng image digest
đã promote trong overlay môi trường phù hợp, qua PR GitOps thay vì apply trực
tiếp.
