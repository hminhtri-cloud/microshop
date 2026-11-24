# Argo CD Core trên Minikube

Argo CD Core là GitOps engine không có API server, RBAC riêng hoặc notification
controller. Nó phù hợp laptop ít tài nguyên; `Application` được kiểm tra bằng
Kubernetes API thay vì giao diện Argo CD. Bản local này pin Argo CD `v3.6.1`.

## Ranh giới quản lý

- Bootstrap Core (namespace `argocd` và manifest chính thức) chạy bằng
  `kubectl`, không do Application MicroShop quản lý.
- `microshop-local` chỉ đồng bộ path
  `deploy/kubernetes/overlays/local` từ nhánh `feature/k8s-local-auth` vào
  namespace `microshop` trong cùng cluster.
- `auth-service-secrets` được tạo ngoài Git và không nằm trong source của
  Application.
- Application không bật prune. Overlay gắn `Delete=false` cho `mysql-data` và
  `Delete=confirm` cho Namespace. Chỉ Job `mysql-bootstrap` có
  `Force=true,Replace=true`: khi chính Job thay đổi, Argo CD có thể tạo lại Job
  idempotent này nhưng không xóa PVC hay database.

## Bootstrap

Trước khi chạy, kiểm tra `kubectl config current-context` là `minikube` và
Secret/PVC MicroShop đang có. Với repository public, không cần Git credential:

```powershell
kubectl --context minikube create namespace argocd
kubectl --context minikube apply -n argocd --server-side --force-conflicts `
  -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.6.1/manifests/core-install.yaml
kubectl --context minikube -n argocd rollout status deployment/argocd-repo-server --timeout=300s
kubectl --context minikube -n argocd rollout status statefulset/argocd-application-controller --timeout=300s
kubectl --context minikube apply -f deploy/argocd/local/project.yaml
kubectl --context minikube apply -f deploy/argocd/local/application.yaml
```

## Kiểm tra và thử GitOps

```powershell
kubectl --context minikube -n argocd get applications.argoproj.io microshop-local
kubectl --context minikube -n microshop get deploy,pods,pvc
kubectl --context minikube -n microshop get deployment frontend `
  -o jsonpath='{.metadata.annotations.microshop\.io/gitops-revision}'
```

`gitops-marker.yaml` chứa marker metadata không ảnh hưởng Pod template. Thay
đổi marker từ Git, commit/push rồi đợi Application `Synced`/`Healthy` là cách
thử sync vô hại. Dùng `git revert <commit>` và push để rollback marker; không
dùng reset hoặc xóa tài nguyên cluster.

Khi hoàn tất demo, dừng riêng cluster bằng `minikube stop -p minikube`. Không
xóa Application, namespace `microshop`, PVC hoặc Secret nếu còn cần dữ liệu.
