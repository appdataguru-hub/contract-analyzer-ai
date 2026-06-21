import os
import logging
import sys
from dotenv import load_dotenv

load_dotenv()


def setup_logging(level: str = "") -> None:
    log_level = level or os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("qdrant_client").setLevel(logging.WARNING)


GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS", "")
GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
GIGACHAT_VERIFY_SSL = os.getenv("GIGACHAT_VERIFY_SSL", "true").lower() == "true"

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
# When true, each upload drops and recreates the Qdrant collection. Set to
# false to append documents to multi-doc collections.
QDRANT_FORCE_RECREATE = os.getenv("QDRANT_FORCE_RECREATE", "true").lower() == "true"

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-large")

COLLECTION_NAME = os.getenv("COLLECTION_NAME", "contracts")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
TOP_K = int(os.getenv("TOP_K", "5"))

EVAL_MODEL = os.getenv("EVAL_MODEL", "gpt-4o")
# Evaluation backend: "auto" (try GigaChat, fallback DeepEval), "gigachat", "deepeval"
EVAL_BACKEND = os.getenv("EVAL_BACKEND", "auto")

API_KEY = os.getenv("API_KEY", "")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_MB", "20")) * 1024 * 1024

# CORS: comma-separated list of allowed origins.
# SECURITY: never use "*" with credentials — browsers reject it AND it signals
# permissive intent. Default includes common local dev frontends (Streamlit / React)
# so the service works out-of-the-box; production deployments must override this
# via the CORS_ORIGINS environment variable to a strict allow-list.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8501,http://localhost:3000,http://127.0.0.1:8501,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() == "true"


def check_qdrant_health() -> bool:
    """Check if Qdrant is reachable at startup."""
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=5)
        client.get_collections()
        return True
    except Exception:
        return False
