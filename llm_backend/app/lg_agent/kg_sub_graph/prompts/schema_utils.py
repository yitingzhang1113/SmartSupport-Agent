"""
Utility functions for safely retrieving and processing the Neo4j database schema.
"""

import re
from typing import Any, Dict, Optional

from langchain_neo4j import Neo4jGraph


def safe_get_schema(graph: Optional[Neo4jGraph] = None) -> str:
    """
    Safely retrieve the schema from a Neo4j database while handling
    potential errors and template variable conflicts.

    Parameters
    ----------
    graph : Optional[Neo4jGraph]
        Neo4jGraph instance. Returns an empty string if None.

    Returns
    -------
    str
        Processed database schema.
    """
    if graph is None:
        return ""

    try:
        # Retrieve the raw schema
        schema: str = graph.get_schema

        # Remove internal schema information that is not relevant
        if "CypherQuery" in schema:
            schema = re.sub(
                r"^(- \*\*CypherQuery\*\*[\s\S]+?)(^Relationship properties|- \*)",
                r"\2",
                schema,
                flags=re.MULTILINE,
            )

        # Escape curly braces to avoid conflicts with prompt template variables
        # Example: {name} -> {{name}}
        schema = schema.replace("{", "{{").replace("}", "}}")

        return schema

    except Exception as e:
        print(f"Failed to retrieve the Neo4j schema: {e}")
        return ""


def create_guardrails_context(
    graph: Optional[Neo4jGraph] = None,
    scope_description: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create the context variables required by the guardrails prompt.

    Parameters
    ----------
    graph : Optional[Neo4jGraph]
        Neo4jGraph instance.
    scope_description : Optional[str]
        Optional description of the application scope.

    Returns
    -------
    Dict[str, Any]
        Dictionary containing the scope context and graph schema.
    """
    # Prepare the application scope description
    scope_context = ""
    if scope_description:
        scope_context = f"Use the following application scope as a reference:\n{scope_description}\n\n"

    # Prepare the graph schema
    graph_schema = ""
    if graph:
        schema = safe_get_schema(graph)

        if schema:
            graph_schema = f"Use the following graph schema as a reference:\n{schema}\n\n"

    return {"scope_context": scope_context,"graph_schema": graph_schema}