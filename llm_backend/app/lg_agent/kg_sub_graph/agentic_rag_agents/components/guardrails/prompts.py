from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_neo4j import Neo4jGraph
from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.utils.utils import retrieve_and_parse_schema_from_graph_for_prompts
from app.lg_agent.kg_sub_graph.prompts.kg_prompts import GUARDRAILS_SYSTEM_PROMPT


def create_guardrails_prompt_template(
    graph: Optional[Neo4jGraph] = None, scope_description: Optional[str] = None
) -> ChatPromptTemplate:
    """
    Create a guardrails prompt template.

    Parameters
    ----------
    graph : Optional[Neo4jGraph], optional
        The `Neo4jGraph` object used to generated a schema definition, by default None
    scope_description : Optional[str], optional
        A description of the application scope, by default None

    Returns
    -------
    ChatPromptTemplate
        The prompt template.
    """
    scope_context = (
        f"Use the following scope description to make your decision:\n{scope_description}"
        if scope_description is not None
        else ""
    )

    # Dynamically retrieve the graph schema from the Neo4j graph database.
    graph_context = (
        f"\nUse the following graph schema for reference:\n"
        f"{retrieve_and_parse_schema_from_graph_for_prompts(graph)}"
        if graph is not None
        else ""
    )

    message = scope_context + graph_context + "\nQuestion: {question}"

    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                GUARDRAILS_SYSTEM_PROMPT,
            ),
            (
                "human",
                (message),
            ),
        ]
    )
