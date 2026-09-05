from typing import Any, Callable, Coroutine, Dict, List
import asyncio
import os
from pathlib import Path
from pydantic import BaseModel, Field

# Import GraphRAG related modules
import app.graphrag.graphrag.api as api
from app.graphrag.graphrag.config.load_config import load_config
from app.graphrag.graphrag.callbacks.noop_query_callbacks import NoopQueryCallbacks
from app.graphrag.graphrag.utils.storage import load_table_from_storage
from app.graphrag.graphrag.storage.file_pipeline_storage import FilePipelineStorage

# Import configuration
from app.core.config import settings

# Define the input state type for GraphRAG query
class GraphRAGQueryInputState(BaseModel):
    task: str
    query: str
    steps: List[str]

# Define the output state type for GraphRAG query
class GraphRAGQueryOutputState(BaseModel):
    task: str
    query: str
    errors: List[str]
    records: Dict[str, Any]
    steps: List[str]

# # Define the GraphRAG API wrapper
class GraphRAGAPI:
    def __init__(
        self,
        project_dir: str | None = None,
        kb_id: str | None = None,
        query_type: str | None = None,
        response_type: str | None = None,
        community_level: int | None = None,
        dynamic_community_selection: bool | None = None,
    ):
        # project_dir: GraphRAG root directory, where settings.yaml is located
        self.project_dir = project_dir or settings.GRAPHRAG_PROJECT_DIR

        # kb_id: uploaded/indexed knowledge base UUID under data/output/<kb_id>
        self.kb_id = kb_id or settings.GRAPHRAG_KB_ID

        self.query_type = query_type or settings.GRAPHRAG_QUERY_TYPE
        self.response_type = response_type or settings.GRAPHRAG_RESPONSE_TYPE
        self.community_level = (
            community_level
            if community_level is not None
            else settings.GRAPHRAG_COMMUNITY_LEVEL
        )
        self.dynamic_community_selection = (
            dynamic_community_selection
            if dynamic_community_selection is not None
            else settings.GRAPHRAG_DYNAMIC_COMMUNITY
        )

        self.config = None
        self.storage = None
        self.entities = None
        self.text_units = None
        self.communities = None
        self.community_reports = None
        self.relationships = None
        self.covariates = None
        self.initialized = False

    async def initialize(self):
        """Initialize the GraphRAG API and load the selected uploaded index."""
        if self.initialized:
            return

        if not self.kb_id:
            raise ValueError("GRAPHRAG_KB_ID is required.")

        project_root = Path(self.project_dir)

        if not project_root.exists():
            raise FileNotFoundError(f"GraphRAG project dir not found: {project_root}")

        # Load settings.yaml from app/graphrag/
        self.config = load_config(project_root, None, None)

        # Load parquet files from app/graphrag/data/output/<kb_id>/
        output_dir = project_root / "data" / "output" / self.kb_id

        if not output_dir.exists():
            raise FileNotFoundError(f"GraphRAG index output dir not found: {output_dir}")

        self.storage = FilePipelineStorage(root_dir=str(output_dir))

        try:
            self.entities = await load_table_from_storage("entities", self.storage)
            self.text_units = await load_table_from_storage("text_units", self.storage)
            self.communities = await load_table_from_storage("communities", self.storage)
            self.community_reports = await load_table_from_storage(
                "community_reports", self.storage
            )
            self.relationships = await load_table_from_storage(
                "relationships", self.storage
            )

            try:
                self.covariates = await load_table_from_storage("covariates", self.storage)
            except Exception:
                self.covariates = None

            self.initialized = True

        except Exception as e:
            raise Exception(f"Error loading GraphRAG index files: {str(e)}")

    async def query_graphrag(self, query: str) -> Dict[str, Any]:
        """Execute the GraphRAG query."""
        await self.initialize()

        callbacks = []
        context_data = {}

        def on_context(context):
            nonlocal context_data
            context_data = context

        local_callbacks = NoopQueryCallbacks()
        local_callbacks.on_context = on_context
        callbacks.append(local_callbacks)

        try:
            query_type = self.query_type.lower()

            if query_type == "local":
                response, context = await api.local_search(
                    config=self.config,
                    entities=self.entities,
                    communities=self.communities,
                    community_reports=self.community_reports,
                    text_units=self.text_units,
                    relationships=self.relationships,
                    covariates=self.covariates,
                    community_level=self.community_level,
                    response_type=self.response_type,
                    query=query,
                    callbacks=callbacks,
                )

            elif query_type == "global":
                response, context = await api.global_search(
                    config=self.config,
                    entities=self.entities,
                    communities=self.communities,
                    community_reports=self.community_reports,
                    community_level=self.community_level,
                    dynamic_community_selection=self.dynamic_community_selection,
                    response_type=self.response_type,
                    query=query,
                    callbacks=callbacks,
                )

            elif query_type == "drift":
                response, context = await api.drift_search(
                    config=self.config,
                    entities=self.entities,
                    communities=self.communities,
                    community_reports=self.community_reports,
                    text_units=self.text_units,
                    relationships=self.relationships,
                    community_level=self.community_level,
                    response_type=self.response_type,
                    query=query,
                    callbacks=callbacks,
                )

            elif query_type == "basic":
                response, context = await api.basic_search(
                    config=self.config,
                    text_units=self.text_units,
                    query=query,
                    callbacks=callbacks,
                )

            else:
                raise ValueError(f"Unsupported query type: {self.query_type}")

            return {
                "response": response,
                "context": context_data or context,
                "kb_id": self.kb_id,
                "query_type": self.query_type,
            }

        except Exception as e:
            raise Exception(f"Error executing GraphRAG query: {str(e)}")

def create_graphrag_query_node(
) -> Callable[
    [GraphRAGQueryInputState],
    Coroutine[Any, Any, Dict[str, List[GraphRAGQueryOutputState] | List[str]]],
]:
    """
    Create the GraphRAG query node, used for LangGraph workflow.

    Returns
    -------
    Callable[[GraphRAGQueryInputState], Dict[str, List[GraphRAGQueryOutputState] | List[str]]]
        The LangGraph node named `graphrag_query`.
    """

    async def graphrag_query(
        state: Dict[str, Any],
    ) -> Dict[str, List[GraphRAGQueryOutputState] | List[str]]:
        """
        Execute the GraphRAG query and return the result.
        """
        errors = list()
        search_result = {}
        
        # Get the query text
        query = state.get("task", "")
        if not query:
            errors.append("No query text provided")
        else:
            try:
                # Use the configuration in the environment variables to create the GraphRAGAPI instance
                graphrag_api = GraphRAGAPI()
                # Call the GraphRAG API to get the data
                search_result = await graphrag_api.query_graphrag(query)
            except Exception as e:
                errors.append(f"GraphRAG query failed: {str(e)}")
  
            return {
                "cyphers": [
                    GraphRAGQueryOutputState(
                        **{
                            "task": state.get("task", ""),
                            "query": query,
                            "statement": "",
                            "parameters":"",
                            "errors": errors,
                            # "records": {"result": search_result["response"]},
                            "records": {
                                "result": (
                                    search_result.get("response")
                                    or search_result.get("answer")
                                    or search_result.get("result")
                                    or search_result.get("records")
                                    or search_result.get("data")
                                    or search_result
                                )
                            },
                            "steps": ["execute_graphrag_query"],
                        }
                    )
                ],
                "steps": ["execute_graphrag_query"],
            }
  
    return graphrag_query

