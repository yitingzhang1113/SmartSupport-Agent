"""
A tool_selection node must
* take a single task at a time
* retrieve a list of available tools
    * text2cypher
    * custom pre-written cypher executors
        * these can be numerous and may be retrieved in the same fashion as CypherQuery node contents
    * unstructured text search (sim search)
* decide the appropriate tool for the task
* generate and validate parameters for the selected tool
* send the validated parameters to the appropriate tool node
"""

from typing import Any, Callable, Coroutine, Dict, List, Literal, Set
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import PydanticToolsParser
from langchain_core.runnables.base import Runnable
from langgraph.types import Command, Send
from pydantic import BaseModel
from app.core.logger import get_logger

from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.state import ToolSelectionInputState
from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.tool_selection.prompts import create_tool_selection_prompt_template

# Get logger
logger = get_logger(service="select_tools")

# Define the prompt word for tool selection
tool_selection_prompt = create_tool_selection_prompt_template()

def create_tool_selection_node(
    llm: BaseChatModel,
    tool_schemas: List[type[BaseModel]],
    default_to_text2cypher: bool = True,
) -> Callable[[ToolSelectionInputState], Coroutine[Any, Any, Command[Any]]]:
    """
    Create a tool_selection node to be used in a LangGraph workflow.

    Parameters
    ----------
    llm : BaseChatModel
        The LLM used to process data.
    tool_schemas : Sequence[Union[Dict[str, Any], type, Callable, BaseTool]
        tools schemas that inform the LLM which tools are available.
    default_to_text2cypher : bool, optional
        Whether to attempt Text2Cypher if no tool calls are returned by the LLM, by default True

    Returns
    -------
    Callable[[ToolSelectionInputState], ToolSelectionOutputState]
        The LangGraph node.
    """

    # Build a tool selection chain, where the large model selects a tool from a predefined list of tools based on the Task passed over.
    tool_selection_chain: Runnable[Dict[str, Any], Any] = (
        tool_selection_prompt
        | llm.bind_tools(tools=tool_schemas)
        | PydanticToolsParser(tools=tool_schemas, first_tool_only=True)
    )

    # From the incoming list of tool_schemas, obtain the 'title' attribute of each tool and create a set of tool names. s
    predefined_cypher_tools: Set[str] = {
        t.model_json_schema().get("title", "") for t in tool_schemas
    }


    # async def tool_selection(
    #     state: ToolSelectionInputState,
    # ) -> Command[Literal["text2cypher", "predefined_cypher", "customer_tools"]]:
    async def tool_selection(
        state: ToolSelectionInputState,
    ) -> Command[Literal["cypher_query", "predefined_cypher", "customer_tools"]]:
        """
        Choose the appropriate tool for the given task.
        """
        # Call the tool selection chain to generate the names and parameters of the tools to be called for each task
        tool_selection_output: BaseModel = await tool_selection_chain.ainvoke(
            {"question": state.get("question", "")}
        )
        logger.info(f"Tool selection question: "f"{state.get('question', '')}")

        logger.info(f"Tool selection output: "f"{tool_selection_output}")

       # According to the route, direct to the corresponding tool node
        if tool_selection_output is not None:
            tool_name: str = tool_selection_output.model_json_schema().get("title", "")
            tool_args: Dict[str, Any] = tool_selection_output.model_dump() 
            logger.info(f"Selected tool name: {tool_name}")
            logger.info(f"Selected tool arguments: {tool_args}")
            if tool_name == "predefined_cypher":
                return Command(
                    goto=Send(
                        "predefined_cypher",
                        {
                            "task": state.get("question", ""),
                            "query_name": tool_name,
                            "query_parameters": tool_args,
                            "steps": ["tool_selection"],
                        },
                    )
                )
            elif tool_name == "cypher_query":
                return Command(
                    goto=Send(
                        "cypher_query",
                        {
                            "task": state.get("question", ""),
                            "query_name": tool_name,
                            "query_parameters": tool_args,
                            "steps": ["tool_selection"],
                        },
                    )
                )
            
            else:
                return Command(
                    goto=Send(
                        "customer_tools",
                        {
                            "task": state.get("question", ""),
                            "query_name": tool_name,
                            "query_parameters": tool_args,
                            "steps": ["tool_selection"],
                        },
                    )
                )
                
        elif default_to_text2cypher:
            return go_to_text2cypher
            # return default_to_text2cypher

        # handle instance where no tool is chosen
        else:
            return Command(
                goto=Send(
                    "error_tool_selection",
                    {
                        "task": state.get("question", ""),
                        "errors": [
                            f"Unable to assign tool to question: `{state.get('question', '')}`"
                        ],
                        "steps": ["tool_selection"],
                    },
                )
            )

        return go_to_text2cypher

    return tool_selection
