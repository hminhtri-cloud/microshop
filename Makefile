# created by Tri
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