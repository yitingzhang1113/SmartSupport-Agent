from langchain_core.prompts import ChatPromptTemplate
from app.lg_agent.kg_sub_graph.prompts.kg_prompts import PLANNER_SYSTEM_PROMPT


def create_planner_prompt_template() -> ChatPromptTemplate:
    """
    Create the planner prompt template.

    Returns
    -------
    ChatPromptTemplate
        The planner prompt template.
    """
    message = """Rules:
    * Ensure that tasks do not return duplicate or similar information.
    * Ensure that tasks do not depend on information collected from other tasks.
    * Merge interdependent tasks into a single question.
    * Merge tasks that return the same information into a single question.

    Question: {question}
"""

    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                PLANNER_SYSTEM_PROMPT,
            ),
            (
                "human",
                message,
            ),
        ]
    )