from typing import Any, Callable, Coroutine, Dict, List
import asyncio
import os
from pathlib import Path
from pydantic import BaseModel, Field

# Import GraphRAG related modules
import app.graphrag.graphrag.api as api
from app.graphrag.graphrag.config.load_config import load_config
from app.graphrag.graphrag.callbacks.noop_query_callbacks import NoopQueryCallbacks
from app.graphrag.graphrag.utils.storage import load_table_from_storage
from app.graphrag.graphrag.storage.file_pipeline_storage import FilePipelineStorage
from app.lg_agent.kg_sub_graph.kg_neo4j_conn import get_neo4j_graph
from app.core.logger import get_logger
from langchain_ollama import ChatOllama
# from langchain_deepseek import ChatDeepSeek
from langchain_openai import ChatOpenAI
from app.core.config import settings, ServiceType
from app.lg_agent.kg_sub_graph.agentic_rag_agents.retrievers.cypher_examples.northwind_retriever import NorthwindCypherRetriever
from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.cypher_tools.utils import create_text2cypher_generation_node, create_text2cypher_validation_node, create_text2cypher_execution_node

# Get logger
logger = get_logger(service="cypher_tools")

# Define GraphRAG query input state type
class CypherQueryInputState(BaseModel):
    task: str
    query: str
    steps: List[str]

# Define GraphRAG query output state type
class CypherQueryOutputState(BaseModel):
    task: str
    query: str
    errors: List[str]
    records: Dict[str, Any]
    steps: List[str]

# Define GraphRAG API wrapper

def create_cypher_query_node(
) -> Callable[
    [CypherQueryInputState],
    Coroutine[Any, Any, Dict[str, List[CypherQueryOutputState] | List[str]]],
]:
    """
    Create a Text2Cypher query node for LangGraph workflows.

    Returns
    -------
    Callable[[CypherQueryInputState], Dict[str, List[CypherQueryOutputState] | List[str]]]
        A LangGraph node named `cypher_query`.
    """

    async def cypher_query(
        state: Dict[str, Any],
    ) -> Dict[str, List[CypherQueryOutputState] | List[str]]:
        """
        Execute Text2Cypher query and return results.
        """
        errors = list()
        # Get query text
        query = state.get("task", "")
        if not query:
            errors.append("Query text not provided")
 
        # Use LLM to execute query / multi-hop / parallel query plan
        # 1. Select model service (DeepSeek or Ollama) based on AGENT_SERVICE in .env
        if settings.AGENT_SERVICE == ServiceType.OPENAI:
            model = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model_name=settings.OPENAI_MODEL, temperature=0.7, tags=["research_plan"])
        else:
            model = ChatOllama(model=settings.OLLAMA_AGENT_MODEL, base_url=settings.OLLAMA_BASE_URL, temperature=0.7, tags=["research_plan"])

        # 2. Get Neo4j graph database connection
        try:
            neo4j_graph = get_neo4j_graph()
            logger.info("success to get Neo4j graph database connection")
        except Exception as e:
            logger.error(f"failed to get Neo4j graph database connection: {e}")

        # Step 2. Create custom retriever instance; build Cypher examples from Graph Schema to guide LLM in generating correct Cypher queries
        cypher_retriever = NorthwindCypherRetriever()

        # Step 3. Use custom Cypher examples to guide LLM in generating a Cypher query for the current input question
        cypher_generation = create_text2cypher_generation_node(
            llm=model, graph=neo4j_graph, cypher_example_retriever=cypher_retriever
        )

        cypher_result = await cypher_generation(state)
        print("\n------------Generated Cypher---------------------")
        print(cypher_result)
        #  TODO: Method. Generate Cypher query directly with LLM
        """
        # Install dependencies
        # pip install neo4j-graphrag
        
        from neo4j_graphrag.retrievers import Text2CypherRetriever
        from neo4j_graphrag.llm import OpenAILLM
        import time
        import pandas as pd
        from neo4j import GraphDatabase

        NEO4J_URI="bolt://localhost"
        NEO4J_USERNAME="neo4j"
        NEO4J_PASSWORD="Anna123456"
        NEO4J_DATABASE="neo4j"

        driver = GraphDatabase.driver(
            NEO4J_URI, 
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
            )

        # client = OpenAILLM(api_key="sk-7afffd0249d031f34430", base_url="https://api.deepseek.com", model_name='deepseek-chat')
        client = OpenAILLM(api_key=settings.OPENAI_API_KEY,model_name=settings.OPENAI_MODEL)

        # Define user input:
        examples = [
            (
                "USER INPUT: 'Find all smart speaker products' "
                "QUERY: "
                "MATCH (p:Product)-[:BELONGS_TO]->(c:Category) "
                "WHERE c.CategoryName = 'Smart Speaker' "
                "RETURN p.ProductName, p.UnitPrice, p.UnitsInStock"
            ),
            (
                "USER INPUT: 'What products are included in order 1?' "
                "QUERY: "
                "MATCH (o:Order)-[r:CONTAINS]->(p:Product) "
                "WHERE o.orderId = '1' "
                "RETURN p.ProductName, r.Quantity, "
                "r.UnitPrice, r.Discount"
            ),
        ]

        # Initialize retriever
        retriever = Text2CypherRetriever(
            driver=driver,
            llm=client,
            neo4j_schema=neo4j_schema,  # Dynamic schema can be obtained via retrieve_and_parse_schema_from_graph_for_prompts
            examples=examples,
        )

        
        # Execute retrieval:
        query_text = "Find all smart speaker products."
        print(retriever.search(query_text=query_text))
        """

        # Step 4. Validate whether the generated Cypher query is correct
        validate_cypher = create_text2cypher_validation_node(
            llm=model,
            graph=neo4j_graph,
            llm_validation=True,
            cypher_statement=cypher_result
        )

        # Step 5. Get full information needed to execute the Cypher query
        execute_info = await validate_cypher(state=state)
        print("\n------------validated Cypher---------------------")
        print(execute_info["statement"])

        # Step 6. Execute the Cypher query
        execute_cypher = create_text2cypher_execution_node(
            graph=neo4j_graph, cypher=execute_info
        )

        final_result = await execute_cypher(state)

        # Wrap single subtask output and constrain format with Pydantic model
        return {
            "cyphers": [
                CypherQueryOutputState(
                        **{
                            "task": state.get("task", ""),
                            "query": query,
                            "statement": "",
                            "parameters":"",
                            "errors": errors,
                            "records": {"result": final_result["cyphers"][0]["records"]} if final_result.get("cyphers") and len(final_result["cyphers"]) > 0 else {"result": []},
                            "steps": ["execute_cypher_query"],
                        }
                    )
                ],
                "steps": ["execute_cypher_query"],
            }
  
    return cypher_query