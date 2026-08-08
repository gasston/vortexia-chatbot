"""structlog JSON logging + Prometheus metrics (spec 4.11)."""
import logging

import structlog
from prometheus_client import Counter, Histogram


def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )


log = structlog.get_logger()

CHAT_REQUESTS = Counter(
    "vortexia_chat_requests_total", "Chat requests", ["tenant", "status"]
)
CHAT_LATENCY = Histogram(
    "vortexia_chat_latency_seconds", "Chat end-to-end latency (s)", ["tenant"]
)
# ponytail: llm_tokens & ingest_pages metrics deferred — streaming usage + in-process
# ingest (admin POST /ingest) needed; CLI ingest runs in a separate, un-scraped process.
