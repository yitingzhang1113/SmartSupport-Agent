"""Tool definition file."""

SEARCH_TOOL = {
    "name": "search",
    "description": "Use Google Search to retrieve up-to-date information from the internet.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The question, topic, keywords, or other information to search for on the internet."
            }
        },
        "required": ["query"]
    }
}

# Additional tool definitions can be added here.
# WEATHER_TOOL = {
#     "name": "get_weather",
#     "description": "Retrieve weather information.",
#     "parameters": {
#         "type": "object",
#         "properties": {
#             "city": {
#                 "type": "string",
#                 "description": "The name of the city."
#             }
#         },
#         "required": ["city"]
#     }
# }

# Collection of tool definitions
TOOL_DEFINITIONS = {
    "search": SEARCH_TOOL,
    # "weather": WEATHER_TOOL
}