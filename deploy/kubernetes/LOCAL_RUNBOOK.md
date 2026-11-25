# Runbook Kubernetes local

Tài liệu này phân biệt thao tác an toàn với Minikube local. Workload MicroShop nằm
trong namespace `microshop`; `mysql-data` là PVC chứa dữ liệu MySQL Kubernetes,
không liên quan Docker Compose volume `mysql_data`.

Mọi lệnh Kubernetes dùng tường minh `--context minikube`. Xác minh control plane
trước khi thao tác:

```powershell
kubectl config current-context
kubectl --context minikube get --raw='/readyz'
kubectl --context minikube -n microshop get deploy,pods,pvc,svc
```

## Dựng môi trường mới

Dùng `deploy/kubernetes/overlays/local/README.md` theo thứ tự: khởi động
Minikube Docker driver/containerd, build bốn image theo tag trong
`overlays/local/kustomization.yaml`, `minikube image load`, tạo Secret ngoài Git,
rồi render/apply overlay. `imagePullPolicy: IfNotPresent` trong các Deployment
yêu cầu image phải được load vào Minikube trước rollout.

Chỉ coi dựng xong khi PVC `mysql-data` `Bound`, Job `mysql-bootstrap`
`Complete`, và cả năm Deployment `1/1` available. Job có `CREATE DATABASE IF
NOT EXISTS` và `GRANT` idempotent. Nếu thay Job đã hoàn thành, chỉ xóa Job trước
apply lại; không xóa PVC.

## Mở lại môi trường có dữ liệu

```powershell
minikube start -p minikube
kubectl --context minikube -n microshop get secret auth-service-secrets
kubectl --context minikube -n microshop get pvc mysql-data
kubectl --context minikube -n microshop rollout status deployment/mysql --timeout=150s
kubectl --context minikube -n microshop rollout status deployment/auth-service --timeout=150s
```

Không thay Secret `auth-service-secrets` khi PVC đã có: credential mới sẽ không
khớp user MySQL đã khởi tạo. Không tạo lại namespace, cluster hay PVC trong quy
trình phục hồi.

## Cập nhật image và GitOps

1. Build image với tag bất biến (thường là SHA commit), rồi load tag đó vào
   Minikube.
2. Cập nhật riêng `images[].newTag` phù hợp trong
   `deploy/kubernetes/overlays/local/kustomization.yaml`.
3. Render (`kubectl kustomize ...`) và kiểm tra `git diff --check`, commit/push.
4. Argo Application `microshop-local` trỏ vào nhánh này sẽ sync. Xác minh
   revision, rollout, và image Pod; không `kubectl apply` trực tiếp cùng thay
   đổi mà Argo đang quản lý.

```powershell
kubectl --context minikube -n argocd get application microshop-local
kubectl --context minikube -n microshop get deployment order-service -o jsonpath='{.spec.template.spec.containers[0].image}'
kubectl --context minikube -n microshop rollout status deployment/order-service --timeout=150s
```

## Rollback an toàn

Rollback manifest qua Git: `git revert <commit-thay-tag>` rồi push nhánh GitOps,
và chờ Argo sync. Tag image cũ phải vẫn còn trong Minikube; nếu không, load lại
chính tag cũ. Không dùng `git reset`, prune, xóa Deployment, hoặc xóa PVC để
rollback.

## Chẩn đoán và logging

`startupProbe` cho phép app khởi động; `readinessProbe` chỉ đưa Pod sẵn sàng
vào Service; `livenessProbe` chỉ khởi động lại tiến trình treo. Init container
của Auth/Product/Order dùng truy vấn `SELECT 1` với đúng database nên không coi
TCP 3306 mở là đủ.

```powershell
kubectl --context minikube -n microshop get pods,events --sort-by=.lastTimestamp
kubectl --context minikube -n microshop logs deployment/order-service --tail=200
kubectl --context minikube -n microshop describe pod -l app.kubernetes.io/name=order-service
```

Nếu cần kiểm tra gateway, chỉ forward frontend. Dừng bằng `Ctrl+C` khi xong:

```powershell
kubectl --context minikube -n microshop port-forward service/frontend 18081:80
```

`/api/products` qua Product, `/api/orders` qua Order, API còn lại qua Auth.
`frontend/nginx.conf` trong source trả `404` cho `/api/internal/*`, `/metrics`
và `/api/metrics`. Overlay hiện vẫn dùng frontend image `2072f94`, được build
trước khi thêm hai rule metrics; cần build/load image frontend mới và cập nhật
tag qua GitOps trước khi xác nhận hai rule metrics có hiệu lực runtime.

Prometheus có thể triển khai trước Grafana để giảm RAM đỉnh; xem
`deploy/observability/local/README.md`. Sau khi áp dụng, kiểm tra target
`order-service` là `up` và query counter trước/sau khi tạo traffic. Chỉ coi
dashboard hoặc alert đã hoạt động sau khi kiểm tra kết quả runtime thực tế.

## Kiểm thử vận hành không xóa dữ liệu

Sau khi có headroom tài nguyên, có thể xóa **một Pod ứng dụng** (không phải
MySQL) và chờ Deployment tạo Pod thay thế; sau đó kiểm tra Service và gateway.
Với MySQL, chỉ restart Deployment có kiểm soát, rồi xác minh PVC vẫn `Bound` và
`/ready` của app trả 200. Checkout phải dùng dữ liệu test tách riêng và
Idempotency-Key mới; không suy luận UI checkout hoạt động vì nút frontend vẫn
bị khóa.

## Dừng và thao tác phá hủy

Dừng port-forward foreground trước, sau đó tiết kiệm tài nguyên nhưng giữ dữ liệu
bằng `minikube stop -p minikube`. Lệnh xóa namespace/PVC, recreate cluster hay
`docker compose down -v` là **phá hủy dữ liệu**, không nằm trong runbook thường
quy và không được tự chạy.
