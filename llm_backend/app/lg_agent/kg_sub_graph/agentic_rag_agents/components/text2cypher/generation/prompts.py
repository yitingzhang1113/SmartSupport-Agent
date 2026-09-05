from langchain_core.prompts import ChatPromptTemplate


def create_text2cypher_generation_prompt_template() -> ChatPromptTemplate:
    """
    Create a Text-to-Cypher generation prompt template.

    Returns
    -------
    ChatPromptTemplate
        The prompt template.
    """
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "Convert the user's question into a valid Cypher query. "
                    "Do not include any introduction, explanation, markdown formatting, "
                    "backticks, or additional text. "
                    "Return only the Cypher query."
                ),
            ),
            (
                "human",
                (
                    """You are an expert in Neo4j and Cypher query generation.

                    Generate a syntactically correct Cypher query based on the user's question.

                    Requirements:
                    - Return only the Cypher query.
                    - Do not include any explanations, markdown, backticks, or additional formatting.
                    - The query must start with either a MATCH clause or a WITH clause.
                    - Use the provided database schema when generating the query.

                    Database Schema:
                    {schema}

                    Below are example questions and their corresponding Cypher queries:

                    {fewshot_examples}

                    User Question:
                    {question}

                    Cypher Query:"""
                ),
            ),
        ]
    )