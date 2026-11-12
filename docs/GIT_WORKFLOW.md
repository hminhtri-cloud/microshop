# Git workflow — MicroShop (nhóm 3 người)

## 1. Luồng chuẩn

```text
feature/<ten-viec> ── Pull Request + review + CI ──> develop
                                                       │
                                       kiểm thử bản tích hợp/staging
                                                       │
                                                       ▼
                                           Pull Request ──> main
                                                            │
                                                     phiên bản demo/release
```

- `main`: nhánh ổn định để demo/bàn giao. Không commit trực tiếp; chỉ nhận PR từ `develop` (hoặc `hotfix/*` nếu khẩn cấp).
- `develop`: nhánh tích hợp của cả nhóm. Feature branch mở PR vào đây; merge khi review xong và CI xanh.
- `feature/*`, `fix/*`, `docs/*`: nhánh làm việc ngắn hạn; mỗi nhánh một mục tiêu có thể kiểm tra được.
- `hotfix/*`: tạo từ `main` để sửa lỗi bản đã phát hành; sau khi merge vào `main`, mở PR mang cùng sửa đổi về `develop`.

**Hiện tại:** repo đã có `main` và `origin/main`. Nhánh `develop` được tạo **trên máy local**; chưa push lên GitHub cho tới khi nhóm quyết định công bố. CI và các file quy trình chỉ chạy trên GitHub sau khi được commit/push qua một PR hoặc commit hợp lệ.

## 2. Quy tắc dành cho cả ba thành viên

1. Mỗi người có quyền sở hữu công việc rõ ràng, nhưng review chéo; một PR cần **ít nhất một người khác** review.
2. Không push trực tiếp lên `main`/`develop`; mở Pull Request.
3. PR nhỏ, tập trung vào một feature hoặc một thay đổi hạ tầng. Nếu quá lớn, chia thành các mốc có thể test.
4. Không merge PR khi CI đỏ, chưa giải quyết comment quan trọng hoặc README/API contract chưa khớp.
5. Không commit `.env`, mật khẩu, JWT secret, AWS key, `terraform.tfstate`, `node_modules`, `dist` hay log chứa thông tin nhạy cảm.
6. Không tự ý xóa Docker volume hoặc DB khi kiểm thử. Backend test dùng SQLite riêng; Playwright mock thao tác ghi và chỉ đọc health/catalog thật.
7. Không sửa lịch sử nhánh đã chia sẻ bằng force-push. Nếu xung đột, trao đổi và merge cập nhật từ `develop` có kiểm soát.

## 3. Bắt đầu một task mới

Repo đã được clone và có `origin`:

```bash
git status
git fetch origin
git switch develop
git pull --ff-only origin develop
git switch -c feature/TASK-CUA-BAN
```

Thay `feature/TASK-CUA-BAN` theo task thật. Ví dụ:

```text
feature/order-create
feature/seller-orders
feature/docker-frontend
fix/product-validation
docs/architecture
```

Lần đầu, nếu GitHub chưa có nhánh `develop`, chủ repo cần publish nhánh local: `git push -u origin develop`. Việc publish được làm có chủ đích, không tự động trong tài liệu này.

Trong lúc làm:

```bash
git status
git diff
git add <duong-dan-file-lien-quan>
git diff --cached
git commit -m "feat(order): create customer order endpoint"
git push -u origin <your branh>
```

Chỉ stage đúng file thuộc task. Trước khi `git add`, kiểm tra `git status` để nhận ra file lạ do người khác hoặc công cụ tạo. Có thể xác nhận file nhạy cảm bị bỏ qua bằng `git check-ignore .env`.

### Commit message

Dùng dạng `type(scope): mô tả ngắn`:

| Type    | Khi nào dùng  | Ví dụ                                   |
| ------- | ------------- | --------------------------------------- |
| `feat`  | Tính năng mới | `feat(cart): persist cart per account`  |
| `fix`   | Sửa lỗi       | `fix(auth): reject expired token`       |
| `test`  | Thêm/sửa test | `test(product): cover seller ownership` |
| `docs`  | Tài liệu      | `docs: document local setup`            |
| `chore` | Việc hỗ trợ   | `chore: update dependencies`            |
| `ci`    | Pipeline      | `ci: verify pull requests`              |

Repo hiện có commit message cũ theo kiểu tự do; quy ước mới áp dụng từ các commit sắp tới, không sửa lịch sử đã chia sẻ.

## 4. Pull Request

Mở PR từ `feature/*` vào **`develop`** trên GitHub. PR mô tả:

- Vấn đề/issue, phạm vi và các file chính thay đổi.
- Cách chạy và kết quả test; nếu đổi UI, có ảnh/trình duyệt đã thử.
- Nếu đổi database: migration, ảnh hưởng dữ liệu cũ, cách xác minh.
- Nếu đổi hạ tầng/deployment: ảnh hưởng môi trường, cách rollback.
- Nếu thay đổi API: hợp đồng request/response và tác động frontend/backend.

Mẫu trong `.github/PULL_REQUEST_TEMPLATE.md` sẽ được GitHub điền vào phần mô tả khi tạo PR. Người review phải tự chạy lại hoặc kiểm tra bằng chứng của luồng trọng tâm, không chỉ đếm số commit.

### Trước khi mở PR

| Phạm vi       | Lệnh kiểm tra                                                                             |
| ------------- | ----------------------------------------------------------------------------------------- |
| Toàn bộ stack | `docker compose config --quiet` và `docker compose up -d --build --wait`                  |
| Auth          | Xem lệnh test SQLite ở `README.md`                                                        |
| Product       | Xem lệnh test SQLite ở `README.md`                                                        |
| Frontend      | Trong `frontend/`: `npm ci`, `npm run build`, `npm run test:e2e` (cần backend local chạy) |

CI GitHub chạy backend test + build frontend + Playwright cho PR/push tới `develop` và `main`. Đây là quality gate để phát hiện lỗi tích hợp; người viết code vẫn phải tự test trước khi push.

### Merge và kiểm tra sau merge

1. Reviewer góp ý/xác nhận; tác giả sửa lỗi và đẩy commit bổ sung vào feature branch.
2. Kiểm tra CI xanh trên **commit mới nhất**; merge PR vào `develop`.
3. Cập nhật `develop` local bằng `git pull --ff-only origin develop` trước task mới.
4. Khi đủ mốc demo: mở PR **`develop` → `main`**, chạy lại demo từ code trên `main` sau merge và ghi tag version nếu nhóm cần.

## 5. Xử lý xung đột, hotfix và rollback

- Nếu `develop` đã thay đổi khi feature đang làm: `git fetch origin`, rồi trên feature branch dùng `git merge origin/develop`. Giải quyết xung đột ở file liên quan, chạy lại test, commit phần merge và push bình thường.
- Nếu đang sửa cùng file, trao đổi với owner trước khi ghi đè; không dùng `git reset --hard`/`git clean -fd` để giải quyết xung đột.
- Với lỗi bản trên `main`: tạo `hotfix/<ten-loi>` từ `main`, PR vào `main`, rồi mang sửa đổi về `develop` qua PR riêng.
- Rollback một thay đổi đã merge: dùng PR với `git revert <commit>` hoặc revert PR trên GitHub; giữ lịch sử minh bạch, không force-push.

## 6. Branch protection cần bật trên GitHub

Sau khi publish `develop`, chủ repo vào **Settings → Rules → Rulesets** (hoặc Branch protection rules) đặt cho `main` và `develop`:

1. Bắt buộc Pull Request trước khi merge.
2. Ít nhất **1 approval** từ người khác; không tự approve PR của mình.
3. Bắt buộc status check **`verify`** của workflow `MicroShop CI` sau khi workflow đã chạy thành công ít nhất một lần.
4. Bật yêu cầu branch up-to-date trước merge nếu nhóm chấp nhận thời gian chờ CI tăng; nếu không, luôn kiểm tra conflict và CI trên commit sau cùng.
5. Chặn force-push và xóa nhánh bảo vệ.

Quy tắc này phải cấu hình trong GitHub; file Markdown/CI trong repo **không tự bật branch protection**. Tên check hiển thị trên GitHub có thể có tiền tố workflow; chọn check thực tế xuất hiện ở PR.

## 7. Ví dụ luồng 3 người

```text
A: feature/order-create    → PR develop → B review + CI
B: feature/checkout-ui     → PR develop → C review + CI
C: feature/order-compose   → PR develop → A review + CI

develop: ghép 3 PR, test luồng customer đặt đơn
main: PR release từ develop khi demo end-to-end thành công
```

Mỗi người đều phải đọc được pipeline và triển khai/kiểm chứng phần mình phụ trách. Theo dõi đóng góp bằng issue, PR, review, test và demo; không đánh giá chỉ theo số dòng code.
