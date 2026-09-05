from typing import Any, Callable, Coroutine, Dict, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables.base import Runnable
from langchain_neo4j import Neo4jGraph


from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.guardrails.models import GuardrailsOutput
from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.guardrails.prompts import create_guardrails_prompt_template
from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.state import InputState
from app.core.logger import get_logger

logger = get_logger(service="guardrails_node")


def create_guardrails_node(
    llm: BaseChatModel,
    graph: Optional[Neo4jGraph] = None,
    scope_description: Optional[str] = None,
) -> Callable[[InputState], Coroutine[Any, Any, dict[str, Any]]]:
    """
    Create a guardrails node to be used in a LangGraph workflow.

    Parameters
    ----------
    llm : BaseChatModel
        The LLM used to process data.
    graph: Optional[Neo4jGraph], optional
        The `Neo4jGraph` object used to generated a schema definition, by default None
    scope_description : Optional[str], optional
        A description of the application scope, by default None

    Returns
    -------
    Callable[[InputState], OverallState]
        The LangGraph node.
    """

    # Obtain the complete prompt words for guardrails that include the chart structure and range description
    guardrails_prompt = create_guardrails_prompt_template(
        graph=graph, scope_description=scope_description
    )

   # Utilizing LLM for Structured Output
    guardrails_chain: Runnable[Dict[str, Any], Any] = (
        guardrails_prompt | llm.with_structured_output(GuardrailsOutput)
    )

    async def guardrails(state: InputState) -> Dict[str, Any]:
        """
        Decides if the question is in scope.
        """

        # Extracted from the input question
        question = state.get("question", "")

        # Utilizing LLM for Structured Output
        guardrails_output: GuardrailsOutput = await guardrails_chain.ainvoke(
            {"question": question}
        )
        
        summary = None

        if guardrails_output.decision == "end":
            summary = "Sorry, we don't have this type of product in our store at the moment. You can check it out at another store instead."

        decision_info = {
            "next_action": guardrails_output.decision,
            "summary": summary,
            "steps": ["guardrails"],
        }
        
        logger.info(f"Guardrails Decision Info: {decision_info}")

        return decision_info


    return guardrails
