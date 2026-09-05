from typing import List, Dict, AsyncGenerator, Optional, Callable
import json
import asyncio
from app.tools.search import SearchTool
from openai import AsyncOpenAI
from app.core.config import settings
from app.core.logger import get_logger
from app.tools.definitions import SEARCH_TOOL, TOOL_DEFINITIONS
from app.services.function_tools import ToolRegistry, FunctionTool
from app.prompts.search_prompts import SEARCH_SYSTEM_PROMPT, SEARCH_SUMMARY_PROMPT, format_search_context
from datetime import datetime

logger = get_logger(service="search")

class SearchService:
    def __init__(self):
        logger.info("Initializing SearchService...")
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            # base_url=settings.OPENAI_BASE_URL
        )
        self.model = settings.OPENAI_MODEL
        self.search_tool = SearchTool()
        
        # Initialize the tool registry
        self.tool_registry = ToolRegistry()
        
        # Register the search tool using the predefined tool description
        self.tool_registry.register(FunctionTool(
            **SEARCH_TOOL,  # Unpack the tool definition
            handler=self._handle_search
        ))
        
        # Generate the tool description prompt
        self.tools_description = self._generate_tools_description()

    def _generate_tools_description(self) -> str:
        """Generate the tool description prompt from the registered tool definitions."""
        tool_descriptions = []
        
        for tool_def in self.tool_registry.get_tools_definition():
            func = tool_def["function"]
            name = func["name"]
            desc = func["description"]
            params = []
            
            # Retrieve required parameters and their descriptions
            for param_name, param_info in func["parameters"]["properties"].items():
                if param_name in func["parameters"].get("required", []):
                    params.append(f"{param_name}, used for: {param_info['description']}")
            
            tool_desc = (
                f"{name}, {desc}"
                f"{', required parameters: ' if params else ''}"
                f"{', '.join(params)}"
            )
            tool_descriptions.append(tool_desc)
        
        return (
            "The following tools are currently available:\n\n" +
            "\n".join(tool_descriptions)
        )

    async def _handle_search(self, query: str) -> List[Dict]:
        """Handle a search request."""
        return await asyncio.to_thread(self.search_tool.search, query)

    async def _call_with_tool(self, query: str) -> Dict:
        """Call the model and retrieve the tool call result."""
        try:
            logger.info("Calling model with query: {}", query)
            logger.info("Messages: {}", query)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=query,
                tools=self.tool_registry.get_tools_definition(),
                tool_choice="auto"  # Allow the model to decide whether to use a tool
            )
            
            logger.info(f"Model response: {response.choices[0]}")
            return response.choices[0]
            
        except Exception as e:
            # logger.error(f"Error in _call_with_tool: {str(e)}", exc_info=True)
            logger.error("Error in _call_with_tool: {}", repr(e))
            raise

    async def generate_stream(
        self,
        query: str,
        user_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        on_complete: Optional[Callable] = None
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response with search capabilities."""
        try:
            logger.info(f"Starting search generation for query: {query}")
            
            # Use the formatted system prompt
            messages = [
                {
                    "role": "system",
                    "content": SEARCH_SYSTEM_PROMPT.format(
                        tools_description=self.tools_description
                    )
                },
                {
                    "role": "user",
                    "content": query
                }
            ]

            # Step 1: Retrieve the tool call
            choice = await self._call_with_tool(messages)
            logger.info(f"Tool call response: {choice}")
            
            # Determine how to proceed based on finish_reason
            if choice.finish_reason == "tool_calls":
                # Search is required
                tool_calls = choice.message.tool_calls
                if tool_calls:
                    tool_call = tool_calls[0]
                    logger.info(f"Processing tool call: {tool_call}")
                    
                    try:
                        # Execute the tool call
                        search_results = await self.tool_registry.execute_tool(
                            tool_call.function.name,
                            tool_call.function.arguments
                        )
                        logger.info(f"Got {len(search_results)} search results")
                        
                        if search_results:
                            # Build the search context
                            context = []
                            for result in search_results:
                                context.append(
                                    f"Source: {result['title']}\n"
                                    f"URL: {result['url']}\n"
                                    f"Content: {result['snippet']}\n"
                                )
                            
                            # Build a prompt containing the search context
                            context_prompt = SEARCH_SUMMARY_PROMPT.format(
                                context="\n---\n".join(context),
                                query=query,
                                cur_date=datetime.now().strftime("%Y-%m-%d")
                            )
                            
                            # First return a type identifier to notify the frontend that search results are being generated
                            yield f"data: {json.dumps({'type': 'search_start'}, ensure_ascii=False)}\n\n"
                            
                            # Return the search results
                            search_data = {
                                "type": "search_results",  # Preserve the existing type identifier
                                "total": len(search_results),
                                "query": json.loads(tool_call.function.arguments)["query"],
                                "results": [
                                    {
                                        "title": result["title"],
                                        "url": result["url"],
                                        "snippet": result["snippet"]
                                    }
                                    for result in search_results
                                ]
                            }
                            yield f"data: {json.dumps(search_data, ensure_ascii=False)}\n\n"
                            
                            stream_response = await self.client.chat.completions.create(
                                model=self.model,
                                messages=[
                                    {"role": "system", "content": context_prompt}
                                ],
                                stream=True
                            )

                            async for chunk in stream_response:
                                if chunk.choices[0].delta.content:
                                    content = json.dumps(chunk.choices[0].delta.content, ensure_ascii=False)
                                    yield f"data: {content}\n\n"
             
                    except Exception as e:
                        logger.exception("Search tool execution failed")
                        yield f"data: {json.dumps({'type': 'error', 'content': 'Search tool invocation failed. Please check the backend logs.'}, ensure_ascii=False)}\n\n"
                        # pass
                
            elif choice.finish_reason == "stop":
                # The model chose to answer directly using a streaming response
                logger.info("Model chose to answer directly, streaming response...")
                
                # First return a type identifier to notify the frontend that this is a direct answer
                yield f"data: {json.dumps({'type': 'direct_answer'}, ensure_ascii=False)}\n\n"
                
                # Generate the answer again using the streaming API
                stream_response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=True
                )
                
                full_response = []
                async for chunk in stream_response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response.append(content)

                        # Wrap the direct answer content
                        direct_payload = json.dumps(
                            {'type': 'direct_content', 'content': content},
                            ensure_ascii=False,
                        )
                        yield f"data: {direct_payload}\n\n"
                
                # Save the conversation if required
                if on_complete and user_id is not None and conversation_id is not None:
                    complete_response = "".join(full_response)
                    await on_complete(user_id, conversation_id, [{"role": "user", "content": query}], complete_response)
                
        # except Exception as e:
            # logger.error(f"Error in generate_stream: {str(e)}", exc_info=True)
        except Exception:
            logger.exception("Error in generate_stream")
            yield f"data: {json.dumps({'type': 'error', 'content': 'An error occurred in the search service. Please check the backend logs.'}, ensure_ascii=False)}\n\n"