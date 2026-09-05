import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.services.policy_service import PolicyRAGService


def main():
    service = PolicyRAGService()

    result = service.build_index(recreate=True)

    print("=" * 80)
    print("Policy Qdrant Local Index Built Successfully")
    print(result)
    print("=" * 80)


if __name__ == "__main__":
    main()