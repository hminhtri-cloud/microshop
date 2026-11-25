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

## 2026-11-25 — Milestone 3: Argo CD Core GitOps

- Installed the official, pinned Argo CD Core `v3.6.1` into a separate
  `argocd` namespace.  Core provides the GitOps controllers and CRDs without
  an always-on API/UI/notification server.  Its four workloads are bounded to
  a combined 512 MiB of requested memory and 1 GiB of memory limits.
- Bootstrap is deliberately separate from the application source.  The Git
  tracked `AppProject` permits only the public MicroShop repository and the
  in-cluster `microshop` destination.  The `Application` tracks
  `feature/k8s-local-auth:deploy/kubernetes/overlays/local`, enables
  self-healing but not prune, and does not include the external Secret.
- Verified anonymous read access to the public branch before bootstrap.  The
  initial automated sync reached `Synced` and `Healthy` at commit `6841b6c`.
  Argo CD recreated only the idempotent bootstrap Job; `mysql-data` remained
  Bound and all application Deployments remained available.
- GitOps change proof: commit `8b3641f` changed the harmless frontend metadata
  marker from `1` to `2`.  After a requested Application refresh, Argo fetched
  that exact revision and applied only the Frontend Deployment metadata.  The
  frontend Pod UID stayed `ea09c7a3-48aa-4419-bd9d-71f4a53ff8b0`.
- GitOps rollback proof: `git revert` produced `a8a5880`; Argo synced that
  exact revision, restored the marker to `1`, and retained the same Pod UID.
  No reset, prune, PVC deletion, Secret update, or direct workload apply was
  used for either proof.
- Next: assess metrics already exposed by the services and remaining laptop
  capacity.  Do not add a heavyweight monitoring stack if it would exceed the
  local resource budget.

## 2026-11-25 — Milestones 4–7: bounded observability and operations preparation

- Added Order Service Prometheus instrumentation in the prior observability
  commit. It records only method, template route, and HTTP status; the
  repository's isolated Order test suite passed 28 tests (15 optional MySQL
  tests skipped by its existing design). Nginx configuration blocks `/metrics`
  and `/api/metrics` from the public gateway.
- Added Prometheus rules for an unavailable Order scrape target and a sustained
  Order 5xx ratio, plus dashboard/configuration documentation. There is no
  Alertmanager or external notification integration in the local overlay.
- Current runtime capacity is deliberately below the safe monitoring budget:
  the host had 0.64 GiB RAM free while Minikube used 2.34 GiB of its 4 GiB
  allocation. Prometheus and Grafana need 384 MiB of requests before runtime
  overhead. Therefore the observability overlay was rendered but was not
  applied, no Grafana Secret/namespace was created, and no scrape/dashboard or
  alert result is claimed.
- Added `LOCAL_RUNBOOK.md` for safe build/open/update/rollback/diagnosis/stop
  operations, and `docs/CI_GITOPS_HANDOFF.md` for the CI/registry/GitOps
  boundary. The CI review found that Trivy uploads reports but `exit-code: 0`
  does not gate HIGH/CRITICAL findings; it also has no registry push or GitOps
  manifest update.
- Live baseline recheck: the existing Minikube node was Ready, `mysql-data`
  Bound, five application Deployments were 1/1 available, and a temporary
  frontend-only forward returned 200 for `/` and `/api/products`, 401 for
  `/api/orders` without credentials, and 404 for `/api/internal/...`.
- Next: once host RAM headroom permits, load the already built Order/frontend
  observability images, update only their local image tags through GitOps, then
  apply the observability overlay and perform the documented controlled alert
  and recovery checks.

## 2026-11-25 — Runtime continuation: Order and Prometheus

- Restarted the existing Minikube profile. Node became Ready, `/readyz` was
  `ok`, and the existing `mysql-data` PVC stayed Bound. Initially frontend
  Nginx could not resolve `product-service` while cluster DNS was starting;
  it recovered automatically. All five Deployments became available.
- Built and loaded `microshop-order-service:e655fb9`; commit `a5b43a9` changed
  only the Order image tag. Argo synced that revision and the new Order Pod
  rolled out. A request through `order-service:8000` returned HTTP 200 for
  `/health` and `/metrics`; the metrics response contained Order counters.
- Applied Prometheus and its rules separately in `observability`. The Pod was
  Ready with zero restarts, its Order target was `up`, and the Prometheus API
  showed the `/health` counter rising from 15 to 28 after ten explicit health
  requests and normal probes. This is cluster runtime evidence, not SQLite.
- Host RAM fell to about 1.05 GiB free, with `vmmemWSL` using roughly 6 GiB;
  C: had 7.39 GiB free. Grafana, controlled alert firing/recovery, fault tests,
  and checkout were deferred until the machine has enough headroom. No Grafana
  Secret was created. No alert firing or dashboard result is claimed.
- Next: verify capacity after restarting; load and roll out the frontend image
  containing the gateway metrics blocks, then deploy Grafana if feasible. Test
  both alert transitions and the remaining operational scenarios separately.
