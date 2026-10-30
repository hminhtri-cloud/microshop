Bạn đang làm việc trực tiếp trong repository của dự án **MicroShop** trên máy của tôi.

Đây là một dự án học tập xây dựng **website bán hàng theo kiến trúc Microservices**, chạy bằng Docker. Mục tiêu cuối cùng không chỉ là làm website hoạt động mà còn biến hệ thống thành một **End-to-End Security Monitoring / DevSecOps Lab** để tôi học Microservices, Docker, Networking, Logging, SIEM, IDS/IPS và security monitoring.

## VIỆC ĐẦU TIÊN BẠN PHẢI LÀM

Trước khi đề xuất, sửa hoặc tạo bất kỳ code nào:

**Hãy tự đọc và phân tích repository hiện tại.**

Không được giả định cấu trúc project dựa trên prompt này nếu có thể kiểm tra trực tiếp từ filesystem.

Hãy inspect ít nhất:

- cấu trúc thư mục toàn project
- `docker-compose.yml` / `compose.yml` nếu có
- `.env.example` hoặc các file config liên quan
- `.gitignore`
- các `Dockerfile`
- `requirements.txt`
- source code của từng service
- routes
- models
- schemas
- database configuration
- frontend nếu đã tồn tại
- gateway/nginx config nếu đã tồn tại
- README/documentation nếu có
- các service hiện có
- các health-check endpoint
- các file liên quan authentication/JWT nếu có

Có thể sử dụng các lệnh read-only phù hợp như:

```bash
pwd
find
tree
ls
cat
sed
grep
git status
git diff
docker compose config
docker compose ps
docker ps
docker logs
```

khi cần thiết.

Không chạy các lệnh phá hủy dữ liệu hoặc thay đổi hệ thống trước khi hiểu project.

Đặc biệt KHÔNG tự ý chạy các lệnh như:

```bash
rm -rf
docker system prune
docker volume prune
docker compose down -v
DROP DATABASE
DROP TABLE
git reset --hard
git clean -fd
```

Nếu cần thao tác có khả năng làm mất dữ liệu, hãy giải thích và hỏi tôi trước.

---

# MỤC TIÊU KIẾN TRÚC

MicroShop là một website e-commerce.

Kiến trúc dài hạn dự kiến:

```text
                         Browser
                            │
                            ▼
                        Frontend
                            │
                            ▼
                   Nginx / API Gateway
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
      Auth Service    Product Service   Order Service
            │               │               │
            ▼               ▼               ▼
         auth_db         product_db       order_db
```

Có thể mở rộng sau này:

```text
Payment Service
Notification Service
Redis
RabbitMQ
Centralized Logging
SIEM
Snort / Suricata
Monitoring
Alerting
```

Nhưng KHÔNG được thêm các thành phần này chỉ để làm project phức tạp.

Ưu tiên:

**simple → working → understandable → secure → scalable**

thay vì over-engineering.

---

# MICROSERVICES PRINCIPLES

Tôi muốn project thực sự giúp tôi hiểu Microservices.

Mỗi service nên dần có:

- trách nhiệm rõ ràng
- API riêng
- container riêng
- data ownership rõ ràng
- configuration riêng
- logs riêng
- khả năng phát triển/deploy tương đối độc lập

Ví dụ:

```text
Auth Service
    ↓
auth_db

Product Service
    ↓
product_db

Order Service
    ↓
order_db
```

Trong giai đoạn học có thể sử dụng **một MySQL container**, nhưng database/schema của từng service cần tách biệt về ownership.

Không để các service tùy tiện query trực tiếp bảng thuộc service khác.

Ví dụ nếu Order Service cần dữ liệu từ Auth/User Service, hãy cân nhắc service-to-service API hoặc cơ chế phù hợp thay vì trực tiếp truy cập bảng `users`.

Không biến hệ thống thành một **distributed monolith**.

---

# DOCKER

Project đang/được định hướng chạy bằng Docker Compose.

Các container giao tiếp với nhau thông qua Docker network và Docker DNS.

Ví dụ service trong Docker nên gọi:

```text
mysql:3306
auth-service:8000
product-service:8000
```

thay vì hard-code container IP.

Phân biệt rõ:

```text
HOST PORT
```

và:

```text
CONTAINER PORT
```

Ví dụ nếu MySQL được map:

```text
3307:3306
```

thì:

```text
Mac/host → localhost:3307
```

nhưng container khác vẫn truy cập:

```text
mysql:3306
```

Hãy kiểm tra Compose thực tế trước khi kết luận port hiện tại.

---

# BACKEND

Backend hiện đang được xây dựng chủ yếu bằng:

```text
Python
FastAPI
SQLAlchemy
Pydantic
MySQL
```

Authentication sử dụng hoặc dự kiến sử dụng:

```text
bcrypt
JWT
Bearer Token
```

Tuy nhiên hãy đọc `requirements.txt` và source code thực tế để xác nhận dependency/version hiện tại.

---

# TRẠNG THÁI GẦN NHẤT CỦA PROJECT

Ở thời điểm prompt này được viết, milestone gần nhất là **Auth Service**.

Đã từng có:

```text
GET  /health
POST /auth/register
```

và `/auth/register` đã từng hoạt động thành công với:

```text
HTTP 201 Created
```

Một user test từng được tạo:

```text
username: panda
email: panda@panda.com
```

Password phải được lưu dưới dạng hash, không lưu plaintext.

Tuy nhiên:

**KHÔNG được mặc định rằng trạng thái repository hiện tại vẫn giống mô tả trên.**

Filesystem/source code hiện tại là source of truth.

Hãy tự kiểm tra code để xác định chính xác project đang ở đâu.

---

# MỘT SỐ LỖI ĐÃ TỪNG GẶP

Thông tin này chỉ dùng để giúp debug nếu gặp lại, KHÔNG được mặc định rằng lỗi vẫn tồn tại.

### Docker daemon chưa chạy

Từng gặp:

```text
failed to connect to the docker API
docker.sock
```

do Docker Desktop chưa chạy.

### MySQL host port

Từng gặp:

```text
bind: address already in use
```

ở host port `3306`.

Sau đó từng sử dụng mapping:

```text
3307:3306
```

Nhưng hãy kiểm tra Compose hiện tại để xác nhận.

### SQLAlchemy

Từng import nhầm:

```python
from sqlalchemy import column
```

thay vì:

```python
from sqlalchemy import Column
```

gây:

```text
TypeError:
column() got an unexpected keyword argument 'primary_key'
```

### Passlib / bcrypt

Từng gặp lỗi tương thích:

```text
ValueError:
password cannot be longer than 72 bytes
```

trong quá trình:

```python
pwd_context.hash(...)
```

mặc dù password thực tế ngắn.

Tại thời điểm đó đã xử lý bằng cách pin dependency tương tự:

```text
passlib[bcrypt]==1.7.4
bcrypt==4.0.1
```

Hãy đọc `requirements.txt` hiện tại trước khi thay đổi dependency.

Không tự ý giải quyết bằng cách truncate password kiểu:

```python
password[:72]
```

---

# SECURITY

Project này sau cùng sẽ trở thành security lab.

Do đó ngay từ đầu hãy chú ý:

- không lưu plaintext password
- không log password
- không log JWT/secret một cách không cần thiết
- validate input
- authentication
- authorization
- role-based access
- secrets/config qua environment variables
- database ownership
- meaningful application logs
- HTTP status code hợp lý
- error handling
- audit/security events

Tuy nhiên đừng over-engineer security khi feature cơ bản còn chưa chạy.

---

# MỤC TIÊU SECURITY LAB SAU NÀY

Khi website hoàn chỉnh hơn, tôi muốn kiến trúc tiến tới:

```text
                    MicroShop
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   Nginx Logs     Service Logs    System Logs
        │              │              │
        └──────────────┼──────────────┘
                       ▼
                Log Collection
                       │
                       ▼
                      SIEM
                       │
              ┌────────┴────────┐
              ▼                 ▼
          Dashboard           Alerts
```

và:

```text
Network Traffic
      │
      ▼
Snort / Suricata
      │
      ▼
IDS Events
      │
      ▼
SIEM
```

Các scenario trong lab có thể gồm:

- repeated login failures
- unauthorized admin access
- HTTP 401/403 spikes
- abnormal request rate
- suspicious API activity
- account enumeration indicators
- IDS alerts
- application security events

Chỉ thực hiện security testing trong môi trường lab do tôi kiểm soát.

---

# ROADMAP TỔNG THỂ

Roadmap tham khảo:

```text
PHASE 1
Auth Service

Register
↓
Login
↓
JWT
↓
Current User (/me)
↓
Authorization
↓
Roles
```

Sau đó:

```text
PHASE 2
Product Service

Product model
↓
Product database
↓
List products
↓
Product detail
↓
Create
↓
Update
↓
Delete
↓
Admin authorization
```

Sau đó:

```text
PHASE 3
Order Service

Create order
↓
Order items
↓
User association
↓
Product communication
↓
Order history
↓
Order status
```

Sau đó:

```text
PHASE 4
API Gateway / Nginx
```

Sau đó:

```text
PHASE 5
Frontend
```

Sau đó:

```text
PHASE 6
Infrastructure improvements

.env
Secrets
Health checks
Migrations
Logging
Redis nếu cần
RabbitMQ nếu cần
```

Cuối cùng:

```text
PHASE 7
Security Monitoring

Centralized Logging
↓
SIEM
↓
Detection Rules
↓
Alerts
↓
Dashboards
↓
IDS/IPS integration
```

Roadmap này KHÔNG phải mệnh lệnh cứng.

Nếu repository thực tế cho thấy project đã đi xa hơn, hãy tiếp tục từ trạng thái thực tế.

---

# CÁCH TÔI MUỐN BẠN LÀM VIỆC

Đây là phần rất quan trọng.

Tôi đang học nên **đừng làm hết mọi thứ thay tôi trong một lần**.

Mỗi lần chỉ nên triển khai một milestone hợp lý.

Ví dụ:

```text
Login
```

xong thì để tôi test.

Sau đó:

```text
JWT
```

hoặc nếu Login + JWT gắn chặt với nhau thì có thể làm cùng một milestone, nhưng vẫn phải giải thích.

Tôi muốn hiểu:

- request đi đâu
- route làm gì
- schema làm gì
- model làm gì
- database session hoạt động ra sao
- service giao tiếp thế nào
- Docker network hoạt động thế nào
- authentication hoạt động thế nào
- authorization hoạt động thế nào
- log được sinh ở đâu

Khi sửa code, hãy nói ngắn gọn:

```text
File nào đang sửa
↓
Tại sao sửa
↓
Thay đổi gì
↓
Luồng sau khi sửa
↓
Cách test
```

---

# QUY TẮC DEBUG

Nếu có lỗi:

**Không đoán mò rồi sửa hàng loạt file.**

Ưu tiên:

```text
Reproduce
↓
Read error
↓
Read logs
↓
Locate failing layer
↓
Explain root cause
↓
Apply smallest reasonable fix
↓
Test
```

Ví dụ có thể kiểm tra:

```bash
docker compose ps
docker ps
docker logs --tail 100 <container>
curl ...
```

Nếu backend trả:

```text
500 Internal Server Error
```

hãy đọc traceback trước.

Nếu container restart:

```text
docker logs
```

trước khi thay đổi code.

Nếu database lỗi:

kiểm tra connection/config/schema trước khi reset database.

Không xóa volume/database chỉ vì migration/schema lỗi nếu chưa thực sự cần.

---

# GIT

Trước khi sửa project, hãy kiểm tra:

```bash
git status
```

Nếu repository đang có uncommitted changes của tôi:

- không overwrite bừa
- không revert code của tôi
- không `git reset --hard`
- không `git clean`
- không checkout đè file

Nếu cần sửa file mà tôi cũng đang sửa, hãy đọc diff trước.

---

# VIỆC BẠN CẦN LÀM NGAY BÂY GIỜ

Bắt đầu bằng việc **inspect repository hiện tại**.

Sau khi đọc project:

1. Tóm tắt ngắn gọn kiến trúc thực tế hiện tại.
2. Cho tôi biết những service nào đã tồn tại và trạng thái code của chúng.
3. Xác định milestone gần nhất đã hoàn thành.
4. Xác định bước tiếp theo hợp lý nhất.
5. Kiểm tra xem có bug/configuration issue rõ ràng nào cần xử lý trước không.
6. Không sửa code ngay nếu chưa cần.
7. Nếu project đúng là đang ở trạng thái Auth Register hoàn thành nhưng Login chưa làm, hãy tiếp tục từ **Auth Login + JWT**.
8. Nếu repository thực tế khác, hãy ưu tiên repository thực tế thay vì prompt này.

Sau khi inspect xong, hãy trình bày kế hoạch ngắn gọn cho **milestone tiếp theo**, rồi bắt đầu hướng dẫn/triển khai milestone đó.

Không tạo toàn bộ Product Service, Order Service, Gateway, Frontend và SIEM cùng lúc.

Mục tiêu là xây MicroShop **từng bước, hiểu từng bước và giữ kiến trúc đủ sạch để sau này biến nó thành một DevSecOps/Security Monitoring Lab hoàn chỉnh.**
