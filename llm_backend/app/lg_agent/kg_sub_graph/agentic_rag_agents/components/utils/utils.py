import regex as re
from langchain_neo4j import Neo4jGraph

from .regex_patterns import get_cypher_query_node_graph_schema


def retrieve_and_parse_schema_from_graph_for_prompts(graph: Neo4jGraph) -> str:
    """
    Retrieve and preprocess the Neo4j graph schema for prompt construction.

    The schema describes the structure of the Neo4j graph database, including:

    - Node labels (e.g., Product, Category, Supplier)
    - Node properties (e.g., ProductName, UnitPrice, CategoryName)
    - Relationship types (e.g., BELONGS_TO, SUPPLIED_BY, CONTAINS)
    - Relationship properties (if any)

    A typical schema looks like:

    Node properties:
        - **Product**: ProductID, ProductName, UnitPrice, UnitsInStock...
        - **Category**: CategoryID, CategoryName, Description...

    Relationship properties:
        - **BELONGS_TO**
        - **SUPPLIED_BY**

    Why is the schema needed?

    1. Adapt automatically to database schema changes.
       If new node labels, relationships, or properties are added,
       the workflow can immediately leverage them without requiring
       code modifications.

    2. Improve query generation accuracy.
       Providing the LLM with an up-to-date database schema
       significantly reduces the likelihood of generating
       invalid Cypher queries.

    3. Enable zero-shot Cypher generation.
       Even without domain-specific examples, the model can
       generate syntactically correct Cypher queries based on
       the provided schema.
    """

    schema: str = graph.get_schema

    # Remove internal graph structures that are irrelevant to user queries.
    if "CypherQuery" in schema:
        schema = re.sub(
            get_cypher_query_node_graph_schema(),
            r"\2",
            schema,
            flags=re.MULTILINE,
        )

    # Replace curly braces with square brackets to avoid conflicts
    # with ChatPromptTemplate placeholder variables.
    #
    # For example:
    #     {ProductName}
    #
    # may be interpreted as an input variable by ChatPromptTemplate.
    schema = schema.replace("{", "[").replace("}", "]")

    return schema