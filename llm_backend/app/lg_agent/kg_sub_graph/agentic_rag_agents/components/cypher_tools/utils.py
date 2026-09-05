from typing import Any, Callable, Coroutine, Dict
import logging
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_neo4j import Neo4jGraph
from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.cypher_tools.prompts import create_text2cypher_generation_prompt_template, create_text2cypher_validation_prompt_template, create_text2cypher_correction_prompt_template
from app.lg_agent.kg_sub_graph.agentic_rag_agents.retrievers.cypher_examples.base import BaseCypherExampleRetriever
from typing_extensions import TypedDict
from typing import Annotated, Any, Dict, List, Optional, Callable, Coroutine,Awaitable
from operator import add
from pydantic import BaseModel, Field
from langchain_core.language_models import BaseChatModel
import regex as re
from langchain_core.runnables.base import Runnable
from langchain_neo4j.chains.graph_qa.cypher_utils import CypherQueryCorrector, Schema
from neo4j.exceptions import CypherSyntaxError

# Set Neo4j driver log level to ERROR to suppress WARNING messages
logging.getLogger("neo4j").setLevel(logging.ERROR)
# Disable langchain_neo4j related logs
logging.getLogger("langchain_neo4j").setLevel(logging.ERROR)
# Disable driver-related logs
logging.getLogger("neo4j.io").setLevel(logging.ERROR)
logging.getLogger("neo4j.bolt").setLevel(logging.ERROR)

class CypherInputState(TypedDict):
    task: Annotated[list, add]

class CypherState(TypedDict):
    task: Annotated[list, add]
    statement: str
    parameters: Optional[Dict[str, Any]]
    errors: List[str]
    records: List[Dict[str, Any]]
    next_action_cypher: str
    attempts: int
    steps: Annotated[List[str], add]

class CypherOutputState(TypedDict):
    task: Annotated[list, add]
    statement: str
    parameters: Optional[Dict[str, Any]]
    errors: List[str]
    records: List[Dict[str, Any]]
    steps: List[str]

class Property(BaseModel):
    """
    Represents a filter condition based on a specific node property in a graph in a Cypher statement.
    """

    node_label: str = Field(
        description="The label of the node to which this property belongs."
    )
    property_key: str = Field(description="The key of the property being filtered.")
    property_value: str = Field(
        description="The value that the property is being matched against.",
        coerce_numbers_to_str=True,
    )

class ValidateCypherOutput(BaseModel):
    """
    Represents the validation result of a Cypher query's output,
    including any errors and applied filters.
    """

    errors: Optional[List[str]] = Field(
        description="A list of syntax or semantical errors in the Cypher statement. Always explain the discrepancy between schema and Cypher statement"
    )
    filters: Optional[List[Property]] = Field(
        description="A list of property-based filters applied in the Cypher statement."
    )

# Define the text2cypher generation prompt
generation_prompt = create_text2cypher_generation_prompt_template()

# Define the text2cypher validation prompt
validation_prompt_template = create_text2cypher_validation_prompt_template()

# Define the text2cypher correction prompt
correction_cypher_prompt = create_text2cypher_correction_prompt_template()


def validate_cypher_query_syntax(graph: Neo4jGraph, cypher_statement: str) -> List[str]:
    """
    Validate the Cypher statement syntax by running an EXPLAIN query.

    Parameters
    ----------
    graph : Neo4jGraph
        The Neo4j graph wrapper.
    cypher_statement : str
        The Cypher statement to validate.

    Returns
    -------
    List[str]
        If the statement contains invalid syntax, return an error message in a list
    """
    errors = list()
    try:
        # Use EXPLAIN query to validate Cypher syntax without actually executing the query
        graph.query(f"EXPLAIN {cypher_statement}")
    except CypherSyntaxError as e:
        errors.append(str(e.message))
    return errors


def correct_cypher_query_relationship_direction(
    graph: Neo4jGraph, cypher_statement: str
) -> str:
    """
    Correct Relationship directions in the Cypher statement with LangChain's `CypherQueryCorrector`.

    Parameters
    ----------
    graph : Neo4jGraph
        The Neo4j graph wrapper.
    cypher_statement : str
        The Cypher statement to validate.

    Returns
    -------
    str
        The Cypher statement with corrected Relationship directions.
    """
    # Extract structural relationship information from the database
    corrector_schema = [
        Schema(el["start"], el["type"], el["end"])
        for el in graph.structured_schema.get("relationships", list())
    ]

    # Use langchain_neo4j's CypherQueryCorrector to validate/correct Cypher syntax
    # e.g.: MATCH (a:Person)-[r:FRIENDS_WITH]->(b:Person); if r:FRIENDS_WITH is reversed, it will be corrected to: MATCH (a:Person)-[r:FRIENDS_WITH]->(b:Person)
    cypher_query_corrector = CypherQueryCorrector(corrector_schema)

    corrected_cypher: str = cypher_query_corrector(cypher_statement)

    return corrected_cypher


def get_cypher_query_node_graph_schema() -> str:
    # 以 "- CypherQuery" 开始的整个段落，直到 "Relationship properties" 或 "- " 为止
    return r"^(- \*\*CypherQuery\*\*[\s\S]+?)(^Relationship properties|- \*)"

def retrieve_and_parse_schema_from_graph_for_prompts(graph: Neo4jGraph) -> str:
    
    """
    Key points:
    schema refers to the structural description of the Neo4j database, including:
    - Node types: e.g., Product, Category, Supplier, etc.
    - Node properties: e.g., ProductName, UnitPrice, CategoryName, etc.
    - Relationship types: e.g., BELONGS_TO, SUPPLIED_BY, CONTAINS, etc.
    - Relationship properties: possible properties on relationships (if any)

    The extracted schema looks roughly like this:
    Node properties:
        - **Product**: ProductID, ProductName, UnitPrice, UnitsInStock...
        - **Category**: CategoryID, CategoryName, Description...

    Relationship properties:
        - **BELONGS_TO**: 
        - **SUPPLIED_BY**: 

    Why it matters:
    1. Dynamic adaptation to database changes: if the database structure changes (new node types, relationships, or properties), the system can adapt without code changes
    2. Improved query accuracy: providing the LLM with accurate database structure greatly reduces the likelihood of generating incorrect queries
    3. Enables zero-shot learning: even without domain-specific examples, the model can generate syntactically valid queries based on the provided structural information
    """
    
    schema: str = graph.get_schema

    # Filter out internal structural information irrelevant to user queries
    if "CypherQuery" in schema:
        schema = re.sub(  
            get_cypher_query_node_graph_schema(), r"\2", schema, flags=re.MULTILINE
        )
    
    # Replace all curly braces with square brackets to avoid template variable conflicts
    # Because Schema contains { }, which conflicts with input_variables in ChatPromptTemplate
    schema = schema.replace("{", "[").replace("}", "]")
    
    return schema


async def validate_cypher_query_with_llm(
    validate_cypher_chain: Runnable[Dict[str, Any], Any],
    question: str,
    graph: Neo4jGraph,
    cypher_statement: str,
) -> Dict[str, List[str]]:
    """
    Validate the Cypher statement with an LLM.
    Use declared LLM to find Node and Property pairs to validate.
    Validate Node and Property pairs against the Neo4j graph.

    Parameters
    ----------
    validate_cypher_chain : RunnableSerializable
        The LangChain LLM to perform processing.
    question : str
        The question associated with the Cypher statement.
    graph : Neo4jGraph
        The Neo4j graph wrapper.
    cypher_statement : str
        The Cypher statement to validate.

    Returns
    -------
    Dict[str, List[str]]
        A Python dictionary with keys `errors` and `mapping_errors`, each with a list of found errors.
    """

    errors: List[str] = []
    mapping_errors: List[str] = []


    # Use the LLM to validate the generated Cypher query and obtain structured output via Pydantic.
    llm_output: ValidateCypherOutput = await validate_cypher_chain.ainvoke(
        {
            "question": question,
            "schema": retrieve_and_parse_schema_from_graph_for_prompts(graph),
            "cypher": cypher_statement,
        }
    )

    # If the structured output contains validation errors, append them to the errors list.
    if llm_output.errors:
        errors.extend(llm_output.errors)
    # If the structured output contains property filters, validate each filter against the database.
    if llm_output.filters:
        for filter in llm_output.filters:
            # Only perform value mapping validation for STRING properties.
            # Check the property type in the Neo4j structured schema before querying the database.
            if (
                not [
                    prop
                    for prop in graph.structured_schema["node_props"][filter.node_label]
                    if prop["property"] == filter.property_key
                ][0]["type"]
                == "STRING"
            ):
                continue

            # Construct a Cypher query to verify whether a node with the specified property value exists in the Neo4j database.
            mapping = graph.query(
                f"MATCH (n:{filter.node_label}) WHERE toLower(n.`{filter.property_key}`) = toLower($value) RETURN 'yes' LIMIT 1",
                {"value": filter.property_value},
            )
            if not mapping:
                mapping_error = f"Missing value mapping for {filter.node_label} on property {filter.property_key} with value {filter.property_value}"
                mapping_errors.append(mapping_error)
    return {"errors": errors, "mapping_errors": mapping_errors}


def validate_cypher_query_with_schema(
    graph: Neo4jGraph, cypher_statement: str
) -> List[str]:
    """
    Validate the provided Cypher statement using the schema retrieved from the graph.
    This will ensure the existance of names nodes, relationships and properties.
    This will validate property values with enums and number ranges, if available.
    This method does not use an LLM.

    Parameters
    ----------
    graph : Neo4jGraph
        The Neo4j graph wrapper.
    cypher_statement : str
        The Cypher to be validated.

    Returns
    -------
    List[str]
        A list of any found errors.
    """
    from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.text2cypher.validation.models import (
    CypherValidationTask,
    Neo4jStructuredSchema,
    Neo4jStructuredSchemaPropertyNumber,
)
    from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.text2cypher.validation.validators import (
    extract_entities_for_validation,
    update_task_list_with_property_type,
    _validate_node_property_names_with_enum,
    _validate_node_property_values_with_enum,
    _validate_node_property_values_with_range,
    _validate_relationship_property_names_with_enum,
    _validate_relationship_property_values_with_enum,
    _validate_relationship_property_values_with_range,
    )

    schema: Neo4jStructuredSchema = Neo4jStructuredSchema.model_validate(
        graph.get_structured_schema
    )
    nodes_and_rels = extract_entities_for_validation(cypher_statement=cypher_statement)

    node_tasks = update_task_list_with_property_type(
        nodes_and_rels.get("nodes", list()), schema, "node"
    )
    rel_tasks = update_task_list_with_property_type(
        nodes_and_rels.get("relationships", list()), schema, "rel"
    )

    errors: List[str] = list()

    node_prop_name_enum_tasks = node_tasks
    node_prop_val_enum_tasks = [n for n in node_tasks if n.property_type == "STRING"]
    node_prop_val_range_tasks = [
        n
        for n in node_tasks
        if (n.property_type == "INTEGER" or n.property_type == "FLOAT")
    ]

    rel_prop_name_enum_tasks = rel_tasks
    rel_prop_val_enum_tasks = [n for n in rel_tasks if n.property_type == "STRING"]
    rel_prop_val_range_tasks = [
        n
        for n in rel_tasks
        if (n.property_type == "INTEGER" or n.property_type == "FLOAT")
    ]

    errors.extend(
        _validate_node_property_names_with_enum(schema, node_prop_name_enum_tasks)
    )
    errors.extend(
        _validate_node_property_values_with_enum(schema, node_prop_val_enum_tasks)
    )
    errors.extend(
        _validate_node_property_values_with_range(schema, node_prop_val_range_tasks)
    )

    errors.extend(
        _validate_relationship_property_names_with_enum(
            schema, rel_prop_name_enum_tasks
        )
    )
    errors.extend(
        _validate_relationship_property_values_with_enum(
            schema, rel_prop_val_enum_tasks
        )
    )
    errors.extend(
        _validate_relationship_property_values_with_range(
            schema, rel_prop_val_range_tasks
        )
    )

    return errors


def validate_no_writes_in_cypher_query(cypher_statement: str) -> List[str]:
    """
    Validate whether the provided Cypher contains any write clauses.

    Parameters
    ----------
    cypher_statement : str
        The Cypher statement to validate.

    Returns
    -------
    List[str]
        A list of any found errors.
    """
    errors: List[str] = list()

    # Restriction: Writing operations are not allowed
    WRITE_CLAUSES = {
    "CREATE",
    "DELETE",
    "DETACH DELETE",
    "SET",
    "REMOVE",
    "FOREACH",
    "MERGE",
    }

    for wc in WRITE_CLAUSES:
        if wc in cypher_statement.upper():
            errors.append(f"Cypher contains write clause: {wc}")

    return errors


def create_text2cypher_generation_node(
    llm: BaseChatModel,
    graph: Neo4jGraph,
    cypher_example_retriever: BaseCypherExampleRetriever,
) -> Callable[[CypherInputState],Awaitable[str],]:
# ) -> str:
    
    text2cypher_chain = generation_prompt | llm | StrOutputParser()

    # async def generate_cypher(state: CypherInputState) -> Dict[str, Any]:
    async def generate_cypher(state: CypherInputState) -> str:
        """
        Generates a cypher statement based on the provided schema and user input
        """
        task = state.get("task", "")
        if not task:
            raise ValueError("No task was provided for ""Cypher generation.")
       # Obtain a Cypher example for the current task and select k items
        examples: str = cypher_example_retriever.get_examples(
            **{"query": task[0] if isinstance(task, list) else task, "k": 3}
        )
        # graph.schema may contain information similar to:
        # Node properties:
        # Product {
        #     productId,
        #     ProductName,
        #     UnitPrice,
        #     UnitsInStock
        # }
        #
        # Relationships:
        # (:Product)-[:BELONGS_TO]->(:Category)
        generated_cypher = await text2cypher_chain.ainvoke(
            {
                "question": state.get("task", ""),
                "fewshot_examples": examples,
                "schema": graph.schema,
            }
        )
        return generated_cypher

    return generate_cypher

def create_text2cypher_validation_node(
    graph: Neo4jGraph,
    llm: Optional[BaseChatModel] = None,
    llm_validation: bool = True,
    cypher_statement: str = None,
) -> Callable[[CypherState], Coroutine[Any, Any, dict[str, Any]]]:
    """
    Create a Text2Cypher query validation node for a LangGraph workflow.

    Parameters
    ----------
    graph : Neo4jGraph
        The Neo4j graph wrapper.
    llm : Optional[BaseChatModel], optional
        The LLM to use for processing if LLM validation is desired. By default None
    llm_validation : bool, optional
        Whether to perform LLM validation with the provided LLM, by default True
    Returns
    -------
    Callable[[CypherState], CypherState]
        The LangGraph node.
    """
    # If an LLM is provided and LLM validation is enabled, use the LLM to perform advanced Cypher validation.
    if llm is not None and llm_validation:
        validate_cypher_chain = validation_prompt_template | llm.with_structured_output(
            ValidateCypherOutput
        )

    async def validate_cypher(state: CypherState) -> Dict[str, Any]:
        """
        Validates the Cypher statements and maps any property values to the database.
        """

        errors = []
        mapping_errors = []

        # 1. Syntax validation:Check whether the Cypher query contains syntax errors,such as invalid keywords or malformed query structure.
        syntax_error = validate_cypher_query_syntax(
            graph=graph, cypher_statement=cypher_statement
        )
        errors.extend(syntax_error)

        # 2.Check whether the Cypher query contains write clauses.(e.g., CREATE, DELETE, SET) to prevent accidental database modifications.
        write_errors = validate_no_writes_in_cypher_query(cypher_statement=cypher_statement)
        errors.extend(write_errors)

        # 3.Neo4j relationships are directional.This step validates relationship directions and automatically,corrects them when possible.
        corrected_cypher = correct_cypher_query_relationship_direction(
            graph=graph, cypher_statement=cypher_statement
        )

        # 4.If LLM validation is enabled, use the language model to perform higher-level validation, such as semantic consistency with the user's question and property value mapping.
        if llm is not None and llm_validation:
            llm_errors = await validate_cypher_query_with_llm(
                validate_cypher_chain=validate_cypher_chain,
                question=state.get("task", ""),
                graph=graph,
                cypher_statement=cypher_statement,
            )
            errors.extend(llm_errors.get("errors", []))
            mapping_errors.extend(llm_errors.get("mapping_errors", []))

        # If LLM validation is disabled, perform deterministic schema-based validation to ensure that nodes, relationships, and property values conform to the database schema.
        if not llm_validation:
            cypher_errors = validate_cypher_query_with_schema(
                graph=graph, cypher_statement=cypher_statement
            )
            errors.extend(cypher_errors)

        # Distinguish between actual Cypher errors and missing data mappings.
        # Map：mapping_errors: ['Missing value mapping for Order on property orderId with value 1', 'Missing value mapping for Product on property ProductName with value smart lock']
        # Mapping errors indicate that the Cypher query itself is structurally correct, but one or more property values cannot be found in the database.
        if errors:
            correct_cypher_chain = correction_cypher_prompt | llm | StrOutputParser()
            corrected_cypher_update = await correct_cypher_chain.ainvoke(
                {
                    "question": state.get("task"),
                    "errors": errors, 
                    "cypher": cypher_statement,
                    "schema": graph.schema,
                }
            )
            corrected_cypher = corrected_cypher_update
            next_action = "execute_cypher" 

        elif mapping_errors:
            # TODO:
            # 1. Terminate the workflow and notify the user that the data does not exist.
            # 2. Ask the user to clarify or refine the query.
            # 3. Regenerate the Cypher query based on conversation history and retry.
            next_action = "execute_cypher"  # or "__end__" or "handle_mapping_error"
        else:
            next_action = "execute_cypher"

        # If errors are found and the maximum number of attempts has not been reached,
        # # route to the "correct_cypher" node to repair the query.
        # if (errors or mapping_errors) and GENERATION_ATTEMPT < max_attempts:
        #     next_action = "correct_cypher"

        # If the maximum number of attempts has not been reached,
        # # proceed to the "execute_cypher" node to execute the query.
        # elif GENERATION_ATTEMPT < max_attempts:
        #     next_action = "execute_cypher"

        # # If the maximum number of attempts has been reached,
        # # but execution on the final attempt is allowed,
        # # still proceed to execute the Cypher query.
        # elif (
        #     GENERATION_ATTEMPT == max_attempts
        #     and attempt_cypher_execution_on_final_attempt
        # ):
        #     next_action = "execute_cypher"

        # # Otherwise, terminate the workflow.
        # else:
        #     next_action = "__end__"

        return {
            "next_action_cypher": next_action,
            "statement": corrected_cypher,
            "errors": errors,
            # "mapping_errors": mapping_errors,
            "steps": ["validate_cypher"],
        }

    return validate_cypher

def create_text2cypher_execution_node(
    graph: Neo4jGraph,
    cypher: str
) -> Callable[
    [CypherState], Coroutine[Any, Any, Dict[str, List[CypherOutputState] | List[str]]]
]:
    """
    Create a Text2Cypher execution node for a LangGraph workflow.

    Parameters
    ----------
    graph : Neo4jGraph
        The Neo4j graph wrapper. 

    Returns
    -------
    Callable[[CypherState], Dict[str, List[CypherOutputState] | List[str]]]
        The LangGraph node.
    """

    async def execute_cypher(
        state: CypherState,
    ) -> Dict[str, List[CypherOutputState] | List[str]]:
        """
        Executes the given Cypher statement.
        """

        cypher_statement = cypher["statement"].replace("\n", " ").strip()
        records = graph.query(cypher_statement)
        steps = state.get("steps", list())
        steps.append("execute_cypher")
        
        NO_CYPHER_RESULTS = [{"error": "No relevant information could be found in the database."}]
        
        return {
            "cyphers": [
                CypherOutputState(
                    **{
                        "task": state.get("task", []),
                        "statement": cypher_statement,
                        "parameters": None,
                        "errors": cypher["errors"],
                        "records": records if records !=[] else NO_CYPHER_RESULTS, 
                        "steps": steps,
                    }
                )
            ],
            "steps": ["text2cypher"],
        }

    return execute_cypher
