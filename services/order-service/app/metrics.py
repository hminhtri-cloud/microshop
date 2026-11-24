"""Low-cardinality Prometheus metrics for Order Service HTTP traffic."""

from prometheus_client import Counter, Histogram


HTTP_REQUESTS = Counter(
    "microshop_order_http_requests",
    "Number of HTTP requests handled by Order Service.",
    ("method", "route", "status_code"),
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "microshop_order_http_request_duration_seconds",
    "HTTP request duration handled by Order Service.",
    ("method", "route", "status_code"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)
