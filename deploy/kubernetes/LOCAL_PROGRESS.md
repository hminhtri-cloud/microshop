# Local Kubernetes progress

## 2026-11-25 — Milestone 0: verification and preservation

- Fast-forwarded `feature/k8s-local-auth` from `2072f94` to `25c9c5d`, which
  includes the merged Trivy reporting workflow from `develop`.  The upstream
  change only adds `.github/workflows/image-security.yml`; it does not overlap
  the local Kubernetes work.
- Kept the existing modifications to `services/order-service/init-order-db.sh`
  and `services/product-service/init-product-db.sh` outside this work.  Both
  files are LF in the index and working tree, and `git diff --ignore-space-at-eol`
  finds no content difference.
- Host capacity at verification time: C: had 12.16 GiB free, D: had 63.39 GiB
  free, and 6.85 GiB RAM was free.  Docker Desktop was stopped, therefore the
  saved Minikube context could not reach its API server.  Runtime work is
  deferred until the Kubernetes baseline has passed static review.
- Next: finish the baseline review, correct configuration drift in the MySQL
  bootstrap Job, then start only the existing project Minikube profile and
  verify the stack without recreating the namespace or PVC.

## 2026-11-25 — Milestone 1: Kubernetes baseline

- Reviewed all base and local-overlay resources.  Deployments use matching
  `app.kubernetes.io/name` selectors and ClusterIP Services use the named HTTP
  target port.  Configuration and cross-service URLs are in local ConfigMaps;
  the four secret keys are referenced but never stored in Git.
- Added startup probes to MySQL and the four application Deployments.  This
  prevents liveness checks from restarting a process while its own readiness
  dependency is still starting.
- The Auth, Product and Order init containers wait by authenticating to their
  configured database and running `SELECT 1`, not merely by opening TCP 3306.
  The local bootstrap Job now derives Product and Order database names from
  their service ConfigMaps, validates MySQL identifiers, and remains
  idempotent.  Updating an existing Job requires deleting only that completed
  Job before apply; the documented procedure never deletes the MySQL PVC.
- `kubectl kustomize` and `git diff --check` passed.  Runtime validation used
  the existing Docker-driver/containerd Minikube profile: node `Ready`,
  `/readyz` returned `ok`, `mysql-data` remained Bound, `mysql-bootstrap`
  completed, and all five Deployments reached `1/1` available with fresh Pods.
- From the Order Pod, `auth-service`, `product-service`, and `order-service`
  each returned HTTP 200 from `/ready`.  A temporary frontend port-forward
  verified gateway responses: `/`, `/api/products`, and `/api/health` returned
  200; `/api/internal/sellers/eligibility` returned 404.
- Next: commit this reviewed baseline, then assess whether a local Ingress adds
  value beyond the frontend Nginx gateway without exposing backend services.

## 2026-11-25 — Milestone 2: local access

- Reviewed the repository deployment architecture.  It defines Ingress/ALB as
  the AWS target while the local overlay already uses a frontend ClusterIP plus
  port-forward.  The Minikube `ingress` addon is disabled.
- Chose not to install ingress-nginx: host free RAM was 1.32 GiB while Compose
  and the local cluster were running, and an extra controller would duplicate
  frontend Nginx routing without improving the local demo.
- Documented the supported local entrypoint: `kubectl port-forward` only to
  `service/frontend`.  Auth, Product, Order and MySQL remain non-public
  ClusterIP Services.  No Minikube tunnel or NodePort is required.
- Runtime evidence remains the temporary frontend forward: host requests to
  `/`, `/api/products`, and `/api/health` returned 200; the frontend Nginx
  returned 404 for `/api/internal/sellers/eligibility`.
- Next: bootstrap a resource-bounded Argo CD installation after checking the
  remaining local capacity.  GitOps will manage application manifests only;
  the externally created Secret and MySQL PVC remain outside Git ownership.
