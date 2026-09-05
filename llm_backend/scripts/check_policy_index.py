import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from qdrant_client import QdrantClient
from app.core.config import settings


client = QdrantClient(
    path=str(settings.QDRANT_LOCAL_DIR)
)

collections = client.get_collections()

print(collections)