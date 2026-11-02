# Deployment scripts

Đặt các script kiểm tra/deploy không chứa credential tại đây, ví dụ:

```text
deploy/scripts/
├── smoke-test.sh       # dự kiến: health, readiness và public /api
├── validate-manifests.sh
└── deploy-staging.sh
```

Script phải fail fast, nhận target/namespace/image tag qua biến hoặc argument, không hard-code secret, và in ra lệnh cần review trước các thao tác destructive.
