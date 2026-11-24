# Observability local gọn nhẹ

Overlay này chỉ dùng Prometheus `v3.16.0` và Grafana `13.3.0` một replica,
không dùng kube-prometheus-stack. Prometheus giữ dữ liệu trong `emptyDir` tối đa
512 MiB, retention 6 giờ; dừng hoặc tạo lại Pod sẽ mất metrics nhưng không ảnh
hưởng MySQL/PVC ứng dụng.

Prometheus scrape `/metrics` của `order-service` qua DNS nội bộ. Metrics HTTP
chỉ gắn `method`, route template và status code; không có user ID, order ID,
token hay URL động. Grafana datasource và dashboard được provision từ
ConfigMap, không cần chỉnh tay để dựng lại.

## Chuẩn bị Secret Grafana

Secret chỉ tồn tại trong namespace `observability`, không được commit. Lần đầu
tạo password ngẫu nhiên trong biến PowerShell; lệnh không in password:

```powershell
if (-not (kubectl --context minikube -n observability get secret grafana-admin --ignore-not-found)) {
  $bytes = New-Object byte[] 24
  [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
  $password = [Convert]::ToBase64String($bytes)
  kubectl --context minikube create namespace observability
  kubectl --context minikube -n observability create secret generic grafana-admin --from-literal=admin-password=$password
}
```

Khi Secret đã tồn tại, giữ nguyên password để các lần apply sau không thay đổi
credential. Không tạo Secret này trong Git.

## Apply và kiểm tra

```powershell
kubectl kustomize deploy/observability/local
kubectl --context minikube apply -k deploy/observability/local
kubectl --context minikube -n observability rollout status deployment/prometheus --timeout=180s
kubectl --context minikube -n observability rollout status deployment/grafana --timeout=180s
kubectl --context minikube -n observability get deploy,pods,svc
kubectl --context minikube -n observability port-forward service/prometheus 19090:9090
kubectl --context minikube -n observability port-forward service/grafana 13000:3000
```

Prometheus và Grafana chỉ là ClusterIP; không route qua frontend Nginx. Mở
`http://127.0.0.1:19090/targets` để xem target Order Service, và
`http://127.0.0.1:13000` để xem dashboard **MicroShop Order Service**. Dừng
mỗi port-forward bằng `Ctrl+C`.

Không cài metrics-server hay kube-state-metrics trên laptop hiện tại. Vì vậy
dashboard chứng minh request/latency/error/scrape health của Order Service,
nhưng chưa có số liệu pod readiness, restart hoặc CPU/RAM từ Kubernetes.
