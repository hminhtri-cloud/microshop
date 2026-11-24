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

## Logging local

Order Service ghi log ra standard output của Pod. `services/order-service/app/main.py`
chỉ ghi request ID và loại lỗi trong các nhánh phục hồi; không ghi JWT,
mật khẩu, `INTERNAL_SERVICE_TOKEN` hay request body. Xem log theo service thay
vì triển khai collector nặng trên laptop:

```powershell
kubectl --context minikube -n microshop logs deployment/order-service --tail=200
kubectl --context minikube -n microshop logs deployment/order-service --since=15m
kubectl --context minikube -n microshop get events --sort-by=.lastTimestamp
```

Uvicorn có thể ghi method, public path và status. Không copy log có dữ
liệu người dùng ra ngoài môi trường local. Loki/ELK không được cài cho
overlay này vì chưa có headroom RAM đủ an toàn.

## Cảnh báo local

`prometheus-rules.yaml` có hai rule: `MicroShopOrderServiceUnavailable`
(target scrape `up == 0` trong 1 phút) và `MicroShopOrderHigh5xxRate` (trên
5% trong 2 phút). Chúng xuất hiện trong Prometheus qua `/alerts` hoặc
`/api/v1/alerts`; overlay cố ý không cấu hình Alertmanager nên không gửi
email/chat ra ngoài.

Sau khi Prometheus đã rollout, kiểm tra rule và alert state:

```powershell
kubectl --context minikube -n observability port-forward service/prometheus 19090:9090
Invoke-RestMethod http://127.0.0.1:19090/api/v1/rules
Invoke-RestMethod http://127.0.0.1:19090/api/v1/alerts
```

Thử alert `Unavailable` phải thực hiện qua một commit Git tạm thời
đổi `replicas` của `order-service` thành `0`, đợi hơn 1 phút, kiểm tra
alert, rồi `git revert` commit đó và chờ alert hết. Không dùng
`kubectl scale` vì Argo CD self-heal sẽ đảo drift quá nhanh. Rule 5xx chỉ
được chấp nhận runtime sau khi có request checkout hợp lệ, dữ liệu test
riêng và một lỗi 503 có kiểm soát từ dependency; không được dùng request
chứa token thật hay thay Secret/PVC để tạo lỗi.
