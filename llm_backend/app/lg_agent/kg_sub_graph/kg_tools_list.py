from typing import Any, Dict

from pydantic import BaseModel, Field


class cypher_query(BaseModel):
    """
    Use this tool for structured Neo4j graph queries when no single
    predefined Cypher query can fully answer the task.

    Suitable scenarios include:
    - multiple combined filters;
    - multiple node types or relationships;
    - new query structures;
    - comparisons;
    - dynamic aggregations;
    - sorting or grouping not covered by one predefined query;
    - any structured graph query requiring Text2Cypher generation.

    Example:
    Find Smart Plug products supplied by companies in Germany
    with fewer than 20 units in stock.
    """

    task: str = Field(
        ...,
        description=(
            "The complete structured graph query task. "
            "Preserve every condition, filter, entity, relationship, "
            "aggregation, sorting requirement, and threshold from the question."
        ),
    )


class predefined_cypher(BaseModel):
    """
    Use this tool only when one existing predefined Cypher query template
    can completely answer the task without changing its query structure.

    The query field must be an exact query ID from predefined_cypher_dict.

    Do not:
    - generate a new Cypher statement;
    - return a natural-language query name;
    - combine multiple predefined queries;
    - use this tool for customer review analysis;
    - use this tool when one template cannot cover all conditions.

    Examples:
    - Find all Smart Plug products.
      Use query ID: product_by_category

    - Find products with fewer than 20 units in stock.
      Use query ID: products_low_stock

    - List suppliers in Germany.
      Use query ID: supplier_by_country
    """

    query: str = Field(
        ...,
        description=(
            "The exact predefined query ID from predefined_cypher_dict, "
            "such as 'product_by_category', 'products_low_stock', "
            "'supplier_by_country', or 'order_details'. "
            "Never return Cypher code or natural-language text."
        ),
    )

    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Parameter values required by the selected predefined query. "
            "Use only parameter names defined by that query template."
        ),
    )


class microsoft_graphrag_query(BaseModel):
    """
    Use this tool for unstructured customer-review knowledge stored in
    Microsoft GraphRAG.

    Suitable scenarios include:
    - customer reviews;
    - customer complaints;
    - recurring product problems;
    - customer opinions and sentiment;
    - product strengths and weaknesses;
    - customer feedback summaries;
    - common product issues;
    - product experience analysis.

    Do not use this tool for exact structured product, inventory, supplier,
    order, employee, or customer-record queries stored in Neo4j.
    """

    query: str = Field(
        ...,
        description=(
            "The complete natural-language question used to search "
            "the Microsoft GraphRAG customer knowledge base."
        ),
    )


class real_time_network_query(BaseModel):
    """
    Use this tool only when current public information must be retrieved
    from the internet.
    """

    query: str = Field(
        ...,
        description="The complete query for real-time internet search.",
    )