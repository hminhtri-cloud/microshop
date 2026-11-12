# created by Tri
.DEFAULT_GOAL := help

.PHONY: help compose-check up lint-frontend build-frontend test-e2e

help:
	@printf '%s\n' \
		'make compose-check    Kiểm tra cấu hình Compose' \
		'make up               Build và khởi động hệ thống' \
		'make lint-frontend    Kiểm tra code frontend' \
		'make build-frontend   Build frontend' \
		'make test-backend     Chạy test backend' \
		'make test-e2e         Chạy test giao diện'

compose-check:
	docker compose config --quiet

up:
	docker compose up -d --build --wait

lint-frontend:
	cd frontend && npm run lint

build-frontend:
	cd frontend && npm run build

test-e2e:
	cd frontend && npm run test:e2e
	
.PHONY: test-auth test-product test-order test-integration test-backend

test-auth:
	docker compose run --rm --no-deps \
		-e DATABASE_URL=sqlite:// \
		-v "$(CURDIR)/services/auth-service/tests:/tests:ro" \
		auth-service python -m unittest discover -s /tests -v

test-product:
	docker compose run --rm --no-deps \
		-e DATABASE_URL=sqlite:// \
		-v "$(CURDIR)/services/product-service/tests:/tests:ro" \
		product-service python -m unittest discover -s /tests -v

test-order:
	docker compose run --rm --no-deps \
		-e DATABASE_URL=sqlite:// \
		-v "$(CURDIR)/services/order-service/tests:/tests:ro" \
		order-service python -m unittest discover -s /tests -v

test-integration:
	docker compose run --rm --no-deps \
		-v "$(CURDIR):/workspace:ro" \
		-w /workspace \
		auth-service python -m unittest discover -s tests -v

test-backend: test-auth test-product test-order test-integration