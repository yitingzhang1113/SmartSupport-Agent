
from langchain_core.prompts import ChatPromptTemplate


def create_text2cypher_generation_prompt_template() -> ChatPromptTemplate:

    """
    Create a Text2Cypher generation prompt template.

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
                    "Based on the input question, convert it into a Cypher query statement. Do not add any preamble. "
                    "Do not include backticks or other markers in the response. Note: return only the Cypher statement!"
                ),
            ),
            (
                "human",
                (
                    """ou are a Neo4j expert. Based on the input question, create a syntactically correct Cypher query statement.
                        Do not include backticks or other markers in the response. Start the query only with MATCH or WITH clauses. Return only the Cypher statement!

                        Below is the database schema information:
                        {schema}

                        Below are some examples of questions and their corresponding Cypher queries:

                        {fewshot_examples}

                        User input: {question}
                        Cypher query:"""
                ),
            ),
        ]
    )


def create_text2cypher_validation_prompt_template() -> ChatPromptTemplate:
    """
    Create a prompt template for validating Text-to-Cypher queries.

    Returns
    -------
    ChatPromptTemplate
        The prompt template.
    """

    validate_cypher_system = """
    You are a Cypher expert reviewing a statement written by a junior developer.
    """

    validate_cypher_user = """You must check the following:
    * Are there any syntax errors in the Cypher statement?
    * Are there any missing or undefined variables in the Cypher statement?
    * Does the Cypher statement contain enough information to answer the question?
    * Ensure that all nodes, relationships, and properties exist in the provided schema.

    Examples of good error messages:
    * The label (:Foo) does not exist. Did you mean (:Bar)?
    * The property bar does not exist for the label Foo. Did you mean baz?
    * The relationship FOO does not exist. Did you mean FOO_BAR?

    Schema:
    {schema}

    Question:
    {question}

    Cypher statement:
    {cypher}

    Make sure you do not make any mistakes!"""

    return ChatPromptTemplate.from_messages(
        [
            ("system",validate_cypher_system),
            ("human",validate_cypher_user),
        ]
    )


def create_text2cypher_correction_prompt_template() -> ChatPromptTemplate:
    """
    Create a prompt template for correcting Text-to-Cypher queries.

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
                    "You are a Cypher expert reviewing a query written by a junior developer. "
                    "Your task is to correct the Cypher statement based on the provided errors. "
                    "Do not include any introduction or explanation. "
                    "Do not include backticks or any other markup in your response. "
                    "Return only the corrected Cypher statement."
                ),
            ),
            (
                "human",
                (
                    """Review the following Cypher statement for syntax and semantic errors,and return the corrected Cypher query.
    Schema:
    {schema}

    Important:
    - Do not include any explanation or apology in your response.
    - Do not include backticks or any other markup.
    - Return only the corrected Cypher statement.
    - Do not answer any request other than correcting the Cypher query.

    Question:
    {question}

    Cypher statement:
    {cypher}

    Validation errors:
    {errors}

    Corrected Cypher statement:"""
                ),
            ),
        ]
    )