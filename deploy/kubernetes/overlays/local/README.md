# Local Minikube với containerd

Overlay này triển khai Auth, Product, Order, frontend/Nginx và một MySQL riêng
trong namespace `microshop`. PVC `mysql-data` là dữ liệu MySQL của Kubernetes;
nó không dùng volume `mysql_data` của Compose.

## Chuẩn bị

Docker Desktop phải chạy Linux engine và ổ C nên còn đủ dung lượng cho image
và volume. Tạo hoặc mở lại cluster bằng Docker driver với container runtime
`containerd`:

```powershell
minikube start --driver=docker --container-runtime=containerd --cpus=2 --memory=4096
kubectl config use-context minikube
kubectl get nodes
kubectl get --raw='/readyz'
```

Node phải là `Ready` và `/readyz` phải trả `ok` trước khi tiếp tục.

## Lần dựng mới

Tag image phải trùng `images[].newTag` trong `kustomization.yaml`. Với các tag
hiện tại, Order dùng source có instrumentation ở `e655fb9`; ba image còn lại
dùng source tương ứng `2072f94`. Build từng image từ đúng phiên bản source đó
trong checkout phù hợp, không gắn tag cũ cho source đã thay đổi:

```powershell
docker build -t microshop-auth-service:2072f94 services/auth-service
docker build -t microshop-product-service:2072f94 services/product-service
docker build -t microshop-order-service:e655fb9 services/order-service
docker build -t microshop-frontend:2072f94 frontend

minikube image load microshop-auth-service:2072f94 -p minikube
minikube image load microshop-product-service:2072f94 -p minikube
minikube image load microshop-order-service:e655fb9 -p minikube
minikube image load microshop-frontend:2072f94 -p minikube
```

`imagePullPolicy: IfNotPresent` trong các Deployment yêu cầu Kubernetes dùng
image đã nạp vào Minikube thay vì tải từ registry.

Tạo Secret ngoài Git từ `.env`. Script dưới đây chỉ đưa bốn key bí mật vào
Kubernetes và không in giá trị:

```powershell
$keys = 'MYSQL_ROOT_PASSWORD','MYSQL_PASSWORD','JWT_SECRET','INTERNAL_SERVICE_TOKEN'
$values = @{}
Get-Content .env | ForEach-Object {
  if ($_ -notmatch '^\s*#' -and $_ -match '=') {
    $pair = $_ -split '=', 2
    $values[$pair[0].Trim()] = $pair[1]
  }
}
$secretArgs = @('--context','minikube','-n','microshop','create','secret','generic','auth-service-secrets')
$keys | ForEach-Object { $secretArgs += "--from-literal=$_=$($values[$_])" }
kubectl --context minikube create namespace microshop
kubectl @secretArgs
```

Render, apply và đợi database:

```powershell
kubectl kustomize deploy/kubernetes/overlays/local
kubectl --context minikube apply -k deploy/kubernetes/overlays/local
kubectl --context minikube -n microshop rollout status deployment/mysql --timeout=150s
kubectl --context minikube -n microshop wait --for=condition=complete job/mysql-bootstrap --timeout=150s
kubectl --context minikube -n microshop rollout status deployment/auth-service --timeout=150s
kubectl --context minikube -n microshop rollout status deployment/product-service --timeout=150s
kubectl --context minikube -n microshop rollout status deployment/order-service --timeout=150s
kubectl --context minikube -n microshop rollout status deployment/frontend --timeout=150s
```

`mysql-bootstrap` tạo `product_db` và `order_db`, sau đó cấp quyền cho user
MySQL. Các lệnh `CREATE DATABASE IF NOT EXISTS` và `GRANT` là idempotent, tức
chạy lại không xóa database, table hay dữ liệu đang có.

## Mở lại cluster đã có PVC

Khi `mysql-data` đã Bound, **không thay Secret bằng credential mới**: MySQL đã
khởi tạo user bằng credential của lần dựng đầu. Chỉ mở cluster và kiểm tra
Secret/PVC hiện có:

```powershell
minikube start -p minikube
kubectl --context minikube -n microshop get secret auth-service-secrets
kubectl --context minikube -n microshop get pvc mysql-data
kubectl --context minikube apply -k deploy/kubernetes/overlays/local
```

Nếu cần chạy lại bootstrap quyền/database sau khi thay đổi manifest, chỉ xóa
Job (không xóa PVC), rồi apply lại:

```powershell
kubectl --context minikube -n microshop delete job mysql-bootstrap --ignore-not-found
kubectl --context minikube apply -k deploy/kubernetes/overlays/local
kubectl --context minikube -n microshop wait --for=condition=complete job/mysql-bootstrap --timeout=150s
```

## Kiểm tra và mở giao diện

### Đường truy cập local

Overlay local chủ động **không** cài Ingress controller hoặc NodePort. Nginx
trong `frontend` vẫn là gateway duy nhất: nó giữ contract `/api/*` và chặn
`/api/internal/*`. Chỉ Service `frontend` được chuyển tiếp tạm thời từ laptop;
Auth, Product, Order và MySQL đều giữ `ClusterIP` nên không có cổng host riêng.
Điều này tránh thêm một lớp routing trùng với Nginx và phù hợp tài nguyên của
Minikube local. Ingress/ALB là phương án mục tiêu của môi trường AWS, không
phải điều kiện cho demo local này.

```powershell
kubectl --context minikube -n microshop get pvc,deploy,pods,svc
kubectl --context minikube -n microshop port-forward service/frontend 18080:80
```

Mở `http://127.0.0.1:18080`. Lệnh chạy ở foreground; dừng nó bằng `Ctrl+C`.
Không cần `minikube tunnel`. Dừng cluster sau khi review bằng `minikube stop -p
minikube`.
