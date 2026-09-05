import asyncio
from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.customer_tools.node import GraphRAGAPI

async def main():
    api = GraphRAGAPI(
        project_dir="martSupport_agent/llm_backend/app/graphrag",
        kb_id="adf3796a-f736-572d-a593-33a9a7f89e46",
        query_type="local",
        response_type="Multiple Paragraphs",
        community_level=2,
    )

    result = await api.query_graphrag(
        "What are the common complaints about smart locks?"
    )

    print(result["response"])

asyncio.run(main())

