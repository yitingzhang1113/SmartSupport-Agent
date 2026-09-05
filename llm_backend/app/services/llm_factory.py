from typing import Union
from app.core.config import settings, ServiceType
from app.services.openai_service import OpenAIService
from app.services.ollama_service import OllamaService
from app.services.search_service import SearchService
class LLMFactory:
    @staticmethod
    def create_chat_service():
        if settings.CHAT_SERVICE == ServiceType.OPENAI:
            return OpenAIService()
        else:
            return OllamaService()

    @staticmethod
    def create_reasoner_service():
        if settings.REASON_SERVICE == ServiceType.OPENAI:
            return OpenAIService()
        else:
            return OllamaService()
    
    @staticmethod
    def create_search_service():
        return SearchService()