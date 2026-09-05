from app.lg_agent.lg_states import AgentState, Router
from app.lg_agent.lg_prompts import (
    ROUTER_SYSTEM_PROMPT,
    GET_ADDITIONAL_SYSTEM_PROMPT,
    GENERAL_QUERY_SYSTEM_PROMPT,
    GET_IMAGE_SYSTEM_PROMPT,
    GUARDRAILS_SYSTEM_PROMPT,
    RAGSEARCH_SYSTEM_PROMPT,
    CHECK_HALLUCINATIONS,
    GENERATE_QUERIES_SYSTEM_PROMPT
)
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from app.core.config import settings, ServiceType
from app.core.logger import get_logger
from typing import cast, Literal, TypedDict, List, Dict, Any
from langchain_core.messages import BaseMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from app.lg_agent.lg_states import AgentState, InputState, Router, GradeHallucinations
from app.lg_agent.kg_sub_graph.agentic_rag_agents.retrievers.cypher_examples.northwind_retriever import NorthwindCypherRetriever
from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.planner.node import create_planner_node
from app.lg_agent.kg_sub_graph.agentic_rag_agents.workflows.multi_agent.multi_tool import create_multi_tool_workflow
from app.lg_agent.kg_sub_graph.kg_neo4j_conn import get_neo4j_graph
from app.services.graphrag_service import graphrag_service
from app.services.policy_service import PolicyRAGService
from pydantic import BaseModel
from typing import Dict, List
from langchain_core.messages import AIMessage
from langchain_core.runnables.base import Runnable
from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.utils.utils import retrieve_and_parse_schema_from_graph_for_prompts
from langchain_core.prompts import ChatPromptTemplate
import base64
import os
import aiohttp
import asyncio
import json
import time
from pathlib import Path


from typing import Literal
from pydantic import BaseModel, Field


class AdditionalGuardrailsOutput(BaseModel):
    """
    Structured output used to determine whether the user's question is related to the graph content.
    """
    decision: Literal["end", "continue"] = Field(
        description="Decision on whether the question is related to the graph contents."
    )

logger = get_logger(service="lg_builder")

async def analyze_and_route_query(
    state: AgentState, *, config: RunnableConfig
) -> dict[str, Router]:
    """Analyze the user's query and determine the appropriate routing.

    This function uses a language model to classify the user's query and decide how to route it
    within the conversation flow.

    Args:
        state (AgentState): The current state of the agent, including conversation history.
        config (RunnableConfig): Configuration with the model used for query analysis.

    Returns:
        dict[str, Router]: A dictionary containing the 'router' key with the classification result (classification type and logic).
    """
    if settings.AGENT_SERVICE == ServiceType.OPENAI:
        model = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model_name=settings.OPENAI_MODEL, temperature=0, tags=["router"])
        logger.info(f"Using OpenAI model: {settings.OPENAI_MODEL}")
    else:
        model = ChatOllama(model=settings.OLLAMA_AGENT_MODEL, base_url=settings.OLLAMA_BASE_URL, temperature=0.7, tags=["router"])
        logger.info(f"Using Ollama model: {settings.OLLAMA_AGENT_MODEL}")

    # Concatenate the prompt template with the user's real-time question, including conversation history.
    messages = [
        {"role": "system", "content": ROUTER_SYSTEM_PROMPT}
    ] + state.messages
    logger.info("-----Analyze user query type-----")
    logger.info(f"History messages: {state.messages}")
    
    # Use structured output to classify the query type.
    response = cast(
        Router, await model.with_structured_output(Router).ainvoke(messages)
    )

    # Fix malformed structured output:
    # Sometimes the model returns:
    # {"type": "object", "properties": {"type": "graphrag-query", ...}}
    if isinstance(response, dict) and response.get("type") == "object" and "properties" in response:
        props = response.get("properties", {})
        response = {
            "type": props.get("type", "general-query"),
            "logic": props.get("logic", ""),
            "question": props.get(
                "question",
                state.messages[-1].content if state.messages else ""
            ),
        }

    logger.info(f"Analyze user query type completed, result: {response}")
    return {"router": response}


def route_query(
    state: AgentState,
) -> Literal["respond_to_general_query","get_additional_info","create_research_plan","create_policy_query","create_image_query","create_file_query",]:
    _type = state.router["type"]
    
    # Check if there is a path for images in the configuration. If so, prioritize processing as an image query.
    if hasattr(state, "config") and state.config and state.config.get("configurable", {}).get("image_path"):
        logger.info("Detected image path. Proceeding with image query processing.")
        return "create_image_query"

    if _type == "general-query":
        return "respond_to_general_query"
    elif _type == "additional-query":
        return "get_additional_info"
    elif _type == "graphrag-query":
        return "create_research_plan"
    elif _type == "policy_query":
        return "create_policy_query"     
    elif _type == "image-query":
        return "create_image_query"
    elif _type == "file-query":
        return "create_file_query"
    else:
        logger.warning(f"Unknown router type {_type}, fallback to general-query")
        return "respond_to_general_query"
    
async def respond_to_general_query(
    state: AgentState, *, config: RunnableConfig
) -> Dict[str, List[BaseMessage]]:
    """Generate a response for a general query.

    This node relies entirely on the language model and does not invoke any
    external services such as custom tools or knowledge base retrieval.

    It is executed when the router classifies the user's request as a
    general-query.

    Args:
        state (AgentState): Current agent state, including conversation history
            and router information.
        config (RunnableConfig): Configuration used for response generation.

    Returns:
        Dict[str, List[BaseMessage]]:
            Generated assistant response.
    """
    logger.info("-----generate general-query response-----")
    
    # Generate the response using the language model.
    if settings.AGENT_SERVICE == ServiceType.OPENAI:
        model = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model_name=settings.OPENAI_MODEL, temperature=0.7, tags=["general_query"])
    else:
        model = ChatOllama(model=settings.OLLAMA_AGENT_MODEL, base_url=settings.OLLAMA_BASE_URL, temperature=0.7, tags=["general_query"])
    
    # system_prompt = GENERAL_QUERY_SYSTEM_PROMPT.format(
    #     logic=state.router["logic"]
    # )
    router_logic = state.router.get(
        "logic",
        "The user is asking a general question."
    )

    system_prompt = GENERAL_QUERY_SYSTEM_PROMPT.format(logic=router_logic)
    
    messages = [{"role": "system", "content": system_prompt}] + state.messages
    response = await model.ainvoke(messages)
    return {"messages": [response]}

async def get_additional_info(
    state: AgentState, *, config: RunnableConfig
) -> Dict[str, List[BaseMessage]]:
    """Ask the user to provide additional information.

    This node is executed when the router determines that the user's request
    does not contain sufficient information to complete the task.

    Args:
        state (AgentState): Current agent state, including conversation history
            and router information.
        config (RunnableConfig): Configuration used for response generation.

    Returns:
        Dict[str, List[BaseMessage]]:
            Assistant response requesting additional information.
    """
    logger.info("------continue to get additional info------")
    
    # Generate the response using the language model.
    if settings.AGENT_SERVICE == ServiceType.OPENAI:
        model = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model_name=settings.OPENAI_MODEL, temperature=0.7, tags=["additional_info"])
    else:
        model = ChatOllama(model=settings.OLLAMA_AGENT_MODEL, base_url=settings.OLLAMA_BASE_URL, temperature=0.7, tags=["additional_info"])

    # # If the user's question is related to e-commerce but falls outside the business scope of our platform, return an out-of-scope response.

    # # Connect to the Neo4j graph database.
    try:
        neo4j_graph = get_neo4j_graph()
        logger.info("success to get Neo4j graph database connection")
    except Exception as e:
        logger.error(f"failed to get Neo4j graph database connection: {e}")

    # # Define the business scope of the e-commerce platform.
    scope_description = """
    Business scope of this e-commerce store:
    Consumer electronics and smart home products, including but not limited to:

    - Smartphones and accessories
    - Laptops and tablets
    - Wireless earbuds and headphones
    - Smart watches and wearables
    - Power banks and chargers
    - Smart home devices
    - Computer accessories
    - Smart lighting
    - Smart security devices
    - Smart speakers
    - Smart kitchen appliances
    - Smart cleaning devices

    Not included:
    - Clothing
    - Shoes
    - Sports equipment
    - Cosmetics
    - Food and beverages
    - Jewelry

    Use this scope to determine whether the user's request is related to our store.
    """

    scope_context = (
    f"Use the following business scope to make your decision:\n{scope_description}"
    )

    # # Dynamically retrieve the graph schema from Neo4j.
    graph_context = (
    f"\nUse the following graph schema for reference:\n{retrieve_and_parse_schema_from_graph_for_prompts(neo4j_graph)}"
    )

    message = scope_context + graph_context + "\nQuestion: {question}"

    # # Build the complete prompt template.
    full_system_prompt = ChatPromptTemplate.from_messages(
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

    # Build a structured-output chain.Return "continue" if the request is in scope,otherwise return "end".
    # guardrails_chain = full_system_prompt | model.with_structured_output(AdditionalGuardrailsOutput)
    # guardrails_output = await guardrails_chain.ainvoke(
    #         {"question": state.messages[-1].content if state.messages else ""}
    #     )
    if settings.AGENT_SERVICE == ServiceType.OPENAI:
        guardrail_model = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model_name=settings.OPENAI_MODEL,
            temperature=0,
            tags=["guardrail"],
        )
    else:
        guardrail_model = ChatOllama(
            model=settings.OLLAMA_AGENT_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0,
            tags=["guardrail"],
        )

    guardrails_chain = full_system_prompt | guardrail_model.with_structured_output(
        AdditionalGuardrailsOutput
    )

    guardrails_output = await guardrails_chain.ainvoke(
            {"question": state.messages[-1].content if state.messages else ""}
        )

    logger.warning(f"[GUARDRAIL_OUTPUT] decision={guardrails_output.decision}")

    # Generate different responses based on the structured output.
    if guardrails_output.decision == "end":
        logger.info("-----Fail to pass guardrails check-----")
        return {"messages": [AIMessage(
            content="Sorry, we don't currently carry that type of product. Is there anything else I can help you with?"
        )]}
    else:
        logger.info("-----Pass guardrails check-----")
        # system_prompt = GET_ADDITIONAL_SYSTEM_PROMPT.format(
        #     logic=state.router["logic"]
        # )
        router_logic = state.router.get(
            "logic",
            "The user needs additional information before the request can be completed."
        )

        system_prompt = GET_ADDITIONAL_SYSTEM_PROMPT.format(
            logic=router_logic
        )
        messages = [{"role": "system", "content": system_prompt}] + state.messages
        response = await model.ainvoke(messages)
        return {"messages": [response]}

async def create_image_query(
    state: AgentState, *, config: RunnableConfig
) -> Dict[str, List[BaseMessage]]:
    """Process an image query and generate a response.

    Args:
        state (AgentState): Current agent state, including conversation history.
        config (RunnableConfig): Runtime configuration containing image path and
            thread-related information.

    Returns:
        Dict[str, List[BaseMessage]]:
            Generated assistant response.
    """
    logger.info("-----Found User Upload Image-----")    
    image_path = config.get("configurable", {}).get("image_path", None)

    if not image_path or not Path(image_path).exists():
        logger.warning(f"User Upload Image Not Found: {image_path}")
        return {"messages": [AIMessage(content="Sorry, I couldn't view this image. Please upload it again.")]}
    
    # # Retrieve the vision model configuration.
    api_key = settings.VISION_API_KEY
    base_url = settings.VISION_BASE_URL
    vision_model = settings.VISION_MODEL
    
    if not api_key or not base_url or not vision_model:
        logger.error("Vision Model Configuration Not Complete")
        return {"messages": [AIMessage(content="Sorry, I couldn't view this image. Please upload it again.")]}
    
    logger.info(f"Using Vision Model: {vision_model} to process image: {image_path}")
    
    try:
       # Import image processing libraries.
        from PIL import Image
        import io
        
        # Read and compress the image.
        with Image.open(image_path) as img:
            # Set the maximum image size.
            max_size = 1024
            # Calculate the resize ratio.
            width, height = img.size
            ratio = min(max_size / width, max_size / height)
            
            # Skip resizing if the image is already within the size limit.
            if width <= max_size and height <= max_size:
                resized_img = img
            else:
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                resized_img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Convert the image to JPEG format with adjusted quality.
            img_byte_arr = io.BytesIO()
            if resized_img.mode != 'RGB':
                resized_img = resized_img.convert('RGB')
            resized_img.save(img_byte_arr, format='JPEG', quality=85)
            img_byte_arr.seek(0)
            
            # Encode the image as Base64.
            image_data = base64.b64encode(img_byte_arr.read()).decode('utf-8')
            
            logger.info(f"Image Compressed, Original Size: {width}x{height}, New Size: {resized_img.width}x{resized_img.height}")
        
        # Build the API request.
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": vision_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a professional image analysis assistant. Analyze the image carefully, especially product details, brand, model, and visible issues."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4000,
            "temperature": 0.7
        }
        
        # Send the API request.
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    image_description = result["choices"][0]["message"]["content"]
                    logger.info(f"Successfully processed image and generated description")
                    # Generate the final response using the image description and the user's original question.
                    
                    # # Build the response generation request.
                    if settings.AGENT_SERVICE == ServiceType.OPENAI:
                        model = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model_name=settings.OPENAI_MODEL, temperature=0.7, tags=["image_query"])
                    else:
                        model = ChatOllama(model=settings.OLLAMA_AGENT_MODEL, base_url=settings.OLLAMA_BASE_URL, temperature=0.7, tags=["image_query"])
                    # Use the dedicated prompt template for image queries.
                    system_prompt = GET_IMAGE_SYSTEM_PROMPT.format(
                        image_description=image_description
                    )
                    messages = [{"role": "system", "content": system_prompt}] + state.messages
                    response = await model.ainvoke(messages)
                    return {"messages": [response]}    
        
                else:
                    error_text = await response.text()
                    logger.error(f"Vision API Request Failed: {response.status} - {error_text}")
                    return {"messages": [AIMessage(content=f"Sorry, I can't view this picture. Please upload it again.")]}

    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return {"messages": [AIMessage(content=f"Sorry, I can't view this picture. Please upload it again.")]}

async def create_file_query(
    state: AgentState, *, config: RunnableConfig
) -> Dict[str, List[BaseMessage]]:
    """Create a file query."""
    
    # TODO


_POLICY_SERVICE = None


def get_policy_service() -> PolicyRAGService:
    """Return the process-wide PolicyRAGService, creating it on first use.

    The service owns an embedded Qdrant client and an embedding model; opening a
    second embedded client on the same path fails, so it must be a singleton.
    """
    global _POLICY_SERVICE
    if _POLICY_SERVICE is None:
        _POLICY_SERVICE = PolicyRAGService()
    return _POLICY_SERVICE


async def create_policy_query(
    state: AgentState, *, config: RunnableConfig
) -> Dict[str, List[BaseMessage]]:
    """Query the enterprise policy knowledge base."""

    logger.info("------execute enterprise policy RAG query------")

    user_query = state.messages[-1].content if state.messages else ""

    if settings.AGENT_SERVICE == ServiceType.OPENAI:
        model = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model_name=settings.OPENAI_MODEL, temperature=0.7, tags=["policy_query"])
    else:
        model = ChatOllama(model=settings.OLLAMA_AGENT_MODEL, base_url=settings.OLLAMA_BASE_URL, temperature=0.7, tags=["policy_query"])

    answer = await get_policy_service().query_policy(query=user_query, model=model)

    return {"messages": [AIMessage(content=answer)]}


# async def create_review_query(
#     state: AgentState, *, config: RunnableConfig
# ) -> Dict[str, List[BaseMessage]]:
#     """Query the review knowledge base (review_data)."""

#     logger.info("------execute review GraphRAG query------")

#     user_query = state.messages[-1].content if state.messages else ""

#     answer = await graphrag_service.query_review(user_query)

#     return {"messages": [AIMessage(content=answer)]}

_KG_WORKFLOW = None


def _agent_model(tags: List[str]):
    """Build the chat model used by the knowledge-graph sub-workflow."""
    if settings.AGENT_SERVICE == ServiceType.OPENAI:
        return ChatOpenAI(api_key=settings.OPENAI_API_KEY, model_name=settings.OPENAI_MODEL, temperature=0.7, tags=tags)
    return ChatOllama(model=settings.OLLAMA_AGENT_MODEL, base_url=settings.OLLAMA_BASE_URL, temperature=0.7, tags=tags)


def get_kg_workflow():
    """Return the compiled multi-tool knowledge-graph workflow, building it on first use.

    The Neo4j connection, Cypher example retriever and the compiled LangGraph are
    process-wide resources. Building them once instead of on every request removes
    a Neo4j handshake plus a schema fetch and a graph compile from each query.
    """
    global _KG_WORKFLOW
    if _KG_WORKFLOW is not None:
        return _KG_WORKFLOW

    logger.info("Building knowledge-graph workflow (first use)")
    neo4j_graph = get_neo4j_graph()
    cypher_retriever = NorthwindCypherRetriever()

    from app.lg_agent.kg_sub_graph.kg_tools_list import cypher_query, predefined_cypher, microsoft_graphrag_query
    from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.predefined_cypher.cypher_dict import predefined_cypher_dict

    tool_schemas: List[type[BaseModel]] = [cypher_query, predefined_cypher, microsoft_graphrag_query]

    scope_description = """
    Business scope of this e-commerce platform:

    Products and Services:
    - Smartphones and accessories
    - Laptops and tablets
    - Wireless earbuds and headphones
    - Smart watches and wearables
    - Power banks and chargers
    - Smart home devices
    - Smart lighting
    - Smart security devices
    - Smart speakers
    - Smart kitchen appliances
    - Smart cleaning devices

    Customer Support Topics:
    - Return Policy
    - Refund Policy
    - Shipping Policy
    - Delivery Information
    - Invoice Policy
    - Warranty Policy
    - Membership Rules
    - Order Cancellation
    - Product Manuals
    - Troubleshooting Guides
    - Customer Service FAQ

    Questions related to any of the above topics should be considered relevant.

    Questions completely unrelated to the business should be rejected.

    Examples of relevant questions:
    - What is your return policy?
    - How long does refund take?
    - Can I cancel my order?
    - What is the warranty period?
    - Do you have Apple Home Smart Lock Max?
    - Which smart cameras are in stock?

    Examples of irrelevant questions:
    - NBA scores today
    - Bitcoin price prediction
    - Who won the World Cup
    """

    _KG_WORKFLOW = create_multi_tool_workflow(
        llm=_agent_model(["research_plan"]),
        graph=neo4j_graph,
        tool_schemas=tool_schemas,
        predefined_cypher_dict=predefined_cypher_dict,
        cypher_example_retriever=cypher_retriever,
        scope_description=scope_description,
        llm_cypher_validation=True,
    )
    return _KG_WORKFLOW


async def create_research_plan(
    state: AgentState, *, config: RunnableConfig
) -> Dict[str, List[str] | str]:
    """Answer the user's question against the Neo4j knowledge graph.

    Runs the (cached) multi-tool workflow: task decomposition, tool selection
    (Text2Cypher / predefined Cypher / GraphRAG), execution and answer synthesis.
    """
    logger.info("------execute local knowledge base query------")
    workflow = get_kg_workflow()
    last_message = state.messages[-1].content if state.messages else ""
    response = await workflow.ainvoke({"question": last_message, "data": [], "history": []})
    return {"messages": [AIMessage(content=response["answer"])]}


async def check_hallucinations(
    state: AgentState, *, config: RunnableConfig
) -> dict[str, Any]:
    """Analyze the user's query and checks if the response is supported by the set of facts based on the document retrieved,
    providing a binary score result.

    This function uses a language model to analyze the user's query and gives a binary score result.

    Args:
        state (AgentState): The current state of the agent, including conversation history.
        config (RunnableConfig): Configuration with the model used for query analysis.

    Returns:
        dict[str, Router]: A dictionary containing the 'router' key with the classification result (classification type and logic).
    """
    if settings.AGENT_SERVICE == ServiceType.OPENAI:
        model = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model_name=settings.OPENAI_MODEL, temperature=0.7, tags=["hallucinations"])
    else:
        model = ChatOllama(model=settings.OLLAMA_AGENT_MODEL, base_url=settings.OLLAMA_BASE_URL, temperature=0.7, tags=["hallucinations"])
    
    system_prompt = CHECK_HALLUCINATIONS.format(
        documents=state.documents,
        generation=state.messages[-1]
    )

    messages = [{"role": "system", "content": system_prompt}] + state.messages
    logger.info("---CHECK HALLUCINATIONS---")
    
    response = cast(GradeHallucinations, await model.with_structured_output(GradeHallucinations).ainvoke(messages))
    
    return {"hallucination": response} 


# checkpointer = InMemorySaver()
checkpointer = MemorySaver()

# Define the state diagram
builder = StateGraph(AgentState, input=InputState)
# Add node 
builder.add_node(analyze_and_route_query)
builder.add_node(respond_to_general_query)
builder.add_node(get_additional_info)
# builder.add_node("create_research_plan", create_research_plan)  
builder.add_node("create_research_plan", create_research_plan)
builder.add_node(create_policy_query)
builder.add_node(create_image_query)
builder.add_node(create_file_query)

# Add edge
builder.add_edge(START, "analyze_and_route_query")
builder.add_conditional_edges("analyze_and_route_query", route_query)


graph = builder.compile(checkpointer=checkpointer)

# from IPython.display import Image, display
# display(Image(graph.get_graph().draw_mermaid_png()))