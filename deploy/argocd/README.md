# Argo CD bootstrap

Thư mục này chứa tài nguyên bootstrap Argo CD cho môi trường local. Argo CD
Core được cài trực tiếp từ manifest chính thức đã pin phiên bản; không được đưa
manifest cài đặt của bên thứ ba, credential Git hoặc Secret ứng dụng vào đây.

`local/` chỉ chứa `AppProject` và `Application`. Sau khi bootstrap, Application
quản lý `deploy/kubernetes/overlays/local` trên cùng nhánh Git. Argo CD không
quản lý chính nó, không quản lý Secret `auth-service-secrets`, và không xóa PVC
`mysql-data`.
