# scripts/test_cypher_query_node.py

import asyncio
import json
import sys
from pathlib import Path
# Add the llm_backend project root to Python's module search path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.cypher_tools.node import (
    create_cypher_query_node,
)

async def main() -> None:
    """
    Test the Text-to-Cypher query node independently.
    """

    cypher_query = create_cypher_query_node()

    state = {
        "task": "Find all Quantum Refrigerator products.",#What products are included in order 1?
        "query": "Find all Quantum Refrigerator products.",
        "steps": [],
    }

    try:
        result = await cypher_query(state)
        serializable_result = {
            "cyphers": [
                item.model_dump()
                if hasattr(item, "model_dump")
                else item
                for item in result.get("cyphers", [])
            ],
            "steps": result.get("steps", []),
        }

        print("\n========== Text-to-Cypher Result ==========")
        print(json.dumps(serializable_result,indent=2,ensure_ascii=False))

    except Exception as exc:
        print("\n========== Text-to-Cypher Test Failed ==========")
        print(f"{type(exc).__name__}: {exc}")
        raise

if __name__ == "__main__":
    asyncio.run(main())