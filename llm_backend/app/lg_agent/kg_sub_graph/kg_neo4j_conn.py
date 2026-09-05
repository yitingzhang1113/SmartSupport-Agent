from langchain_neo4j import Neo4jGraph
from app.core.config import settings
from app.core.logger import get_logger
import logging

logger = get_logger(service="kg_builder")

# Suppress unnecessary Neo4j logs
logging.getLogger("neo4j").setLevel(logging.ERROR)
logging.getLogger("langchain_neo4j").setLevel(logging.ERROR)
logging.getLogger("neo4j.io").setLevel(logging.ERROR)
logging.getLogger("neo4j.bolt").setLevel(logging.ERROR)


def get_neo4j_graph() -> Neo4jGraph:
    """
    Initialize and return a configured Neo4jGraph instance.

    Returns:
        Neo4jGraph: Configured Neo4j graph connection.
    """
    logger.info(f"Initializing Neo4j connection: {settings.NEO4J_URL}")

    try:
        return Neo4jGraph(
            url=settings.NEO4J_URL,
            username=settings.NEO4J_USERNAME,
            password=settings.NEO4J_PASSWORD,
            database=settings.NEO4J_DATABASE,
        )
    except Exception:
        raise

# if __name__ == "__main__":
#     graph = get_neo4j_graph()

#     result = graph.query("""
#     MATCH (n)
#     RETURN count(n) AS total_nodes
#     """)

#     print(result)