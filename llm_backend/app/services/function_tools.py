from typing import List, Dict, Any, Callable
import json
from dataclasses import dataclass

@dataclass
class FunctionTool:
    """Definition of a function tool."""
    name: str
    description: str
    parameters: Dict
    handler: Callable

class ToolRegistry:
    """Registry for function tools."""

    def __init__(self):
        self._tools: Dict[str, FunctionTool] = {}

    def register(self, tool: FunctionTool):
        """Register a tool."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> FunctionTool:
        """Retrieve a tool by name."""
        return self._tools.get(name)

    def get_tools_definition(self) -> List[Dict]:
        """Return the list of tool definitions for API calls."""
        return [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
        } for tool in self._tools.values()]

    async def execute_tool(self, name: str, arguments: str) -> Any:
        """Execute a tool."""
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool {name} not found")

        args = json.loads(arguments)
        return await tool.handler(**args)