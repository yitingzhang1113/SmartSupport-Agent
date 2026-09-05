from pydantic_settings import BaseSettings
from enum import Enum
from pathlib import Path

# Get the project root directory
ROOT_DIR = Path(__file__).parent.parent.parent
ENV_FILE = ROOT_DIR / ".env"

class ServiceType(str, Enum):
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"

class Settings(BaseSettings):
    # OpenAI settings
    OPENAI_API_KEY: str
    OPENAI_MODEL: str

    # Deepseek settings
    DEEPSEEK_API_KEY: str
    DEEPSEEK_BASE_URL: str
    DEEPSEEK_MODEL: str
    
    # Vision Model settings
    VISION_API_KEY: str
    VISION_BASE_URL: str
    VISION_MODEL: str
    
    # Ollama settings
    OLLAMA_BASE_URL: str
    OLLAMA_CHAT_MODEL: str
    OLLAMA_REASON_MODEL: str
    OLLAMA_EMBEDDING_MODEL: str
    OLLAMA_AGENT_MODEL: str
    # Service selection
    # CHAT_SERVICE: ServiceType = ServiceType.OPENAI
    # REASON_SERVICE: ServiceType = ServiceType.OLLAMA
    # AGENT_SERVICE: ServiceType = ServiceType.DEEPSEEK

    CHAT_SERVICE: ServiceType = ServiceType.OPENAI
    REASON_SERVICE: ServiceType = ServiceType.OPENAI
    AGENT_SERVICE: ServiceType = ServiceType.OPENAI
    
    # Search settings
    SERPAPI_KEY: str
    SEARCH_RESULT_COUNT: int = 3
    
    # Database settings
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    
    # Neo4j settings
    NEO4J_URL: str
    NEO4J_USERNAME: str 
    NEO4J_PASSWORD: str
    NEO4J_DATABASE: str
    
    # Redis settings
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_CACHE_EXPIRE: int = 3600
    REDIS_CACHE_THRESHOLD: float = 0.8
    
    # Embedding settings 
    EMBEDDING_TYPE: str = "ollama"  # ollama or sentence_transformer
    EMBEDDING_MODEL: str = "bge-m3"  # ollama embedding model
    EMBEDDING_THRESHOLD: float = 0.90
    
    # GraphRAG settings
    GRAPHRAG_PROJECT_DIR: str = "llm_backend/app/graphrag"
    GRAPHRAG_DATA_DIR: str = "data"
    GRAPHRAG_QUERY_TYPE: str = "local"
    GRAPHRAG_RESPONSE_TYPE: str = "text"
    GRAPHRAG_COMMUNITY_LEVEL: int = 3
    GRAPHRAG_DYNAMIC_COMMUNITY: bool = False
    GRAPHRAG_KB_ID: str = ""

    # Policy RAG settings
    POLICY_DATA_PATH: str = "data/docs/policy_data"
    POLICY_COLLECTION_NAME: str = "smart_support_policy"
    POLICY_RETRIEVAL_TOP_K: int = 12
    POLICY_RERANK_TOP_N: int = 5

    # Qdrant local embedded settings
    QDRANT_LOCAL_PATH: str = "data/vector_store/qdrant"
    QDRANT_MODE: str = "local"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def REDIS_URL(self) -> str:
        """构建Redis URL"""
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    @property
    def NEO4J_CONN_URL(self) -> str:
        return f"{self.NEO4J_URL}"
    
    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"
        case_sensitive = True

    @property
    def POLICY_DATA_DIR(self) -> Path:
        return ROOT_DIR / self.POLICY_DATA_PATH

    @property
    def QDRANT_LOCAL_DIR(self) -> Path:
        return ROOT_DIR / self.QDRANT_LOCAL_PATH

settings = Settings() 