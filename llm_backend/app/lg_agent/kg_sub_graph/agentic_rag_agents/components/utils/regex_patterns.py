def get_cypher_query_node_graph_schema() -> str:
    # The entire paragraph starting with "- CypherQuery" until "Relationship properties" or "- "
    return r"^(- \*\*CypherQuery\*\*[\s\S]+?)(^Relationship properties|- \*)"
