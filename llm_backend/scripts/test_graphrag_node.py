import asyncio

from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.customer_tools.node import (
    create_graphrag_query_node,
)

async def main():
    node = create_graphrag_query_node()

    result = await node({
        "task": "What are the common complaints about smart locks?"
    })

    print(result)

if __name__ == "__main__":
    asyncio.run(main())