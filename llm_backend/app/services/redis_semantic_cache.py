from typing import Dict, List, Optional
import redis
import hashlib
import numpy as np
import json
import time
import aiohttp
from app.core.config import settings
from app.core.logger import get_logger
import asyncio
from datetime import datetime

logger = get_logger(service="redis_cache")


class RedisSemanticCache:
    """Semantic-based Redis cache implementation."""
    
    def __init__(
        self,
        redis_url: str = None,
        model_name: str = None,
        score_threshold: float = None,
        prefix: str = "cache",
        user_id: Optional[int] = None,  # Add user ID
        max_cache_size: int = 1000,  # Maximum number of cached items per user
        cleanup_interval: int = 3600  # Cleanup interval in seconds
    ):
        self.redis = redis.from_url(redis_url or settings.REDIS_URL)
        self.model_name = model_name or settings.OLLAMA_EMBEDDING_MODEL
        self.score_threshold = score_threshold or settings.REDIS_CACHE_THRESHOLD
        self.prefix = f"{prefix}:{user_id}" if user_id else prefix
        self.max_cache_size = max_cache_size
        self.cleanup_interval = cleanup_interval
        
        # Start the automatic cleanup task
        asyncio.create_task(self._auto_cleanup())
        
    async def _get_ollama_embedding(self, text: str) -> List[float]:
        """Generate a text embedding using Ollama."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{settings.OLLAMA_BASE_URL}/api/embed",
                    json={
                        "model": self.model_name,
                        "input": text  # Use input instead of prompt
                    }
                ) as response:
                    result = await response.json()
                    # The Ollama embed API returns data in the format {"embeddings": [[...], ...]}
                    return result["embeddings"][0]  # Return the first embedding
        except Exception as e:
            logger.error(f"Error getting Ollama embedding: {str(e)}", exc_info=True)
            raise

    async def _get_embedding(self, text: str) -> List[float]:
        """Get the text embedding."""
        try:
            # Directly use Ollama's embedding endpoint
            embedding = await self._get_ollama_embedding(text)
            if not embedding:
                raise ValueError("Failed to get embedding")
            return embedding
        except Exception as e:
            logger.error(f"Error in get_embedding: {str(e)}", exc_info=True)
            raise
        
    def _get_vector_key(self, message: str) -> str:
        """Generate the key used to store the vector."""
        message_hash = hashlib.md5(message.encode()).hexdigest()
        return f"{self.prefix}:vec:{message_hash}"
        
    def _get_response_key(self, message: str) -> str:
        """Generate the key used to store the response."""
        message_hash = hashlib.md5(message.encode()).hexdigest()
        return f"{self.prefix}:resp:{message_hash}"
        
    def _get_metadata_key(self, message: str) -> str:
        """Generate the key used to store metadata."""
        message_hash = hashlib.md5(message.encode()).hexdigest()
        return f"{self.prefix}:meta:{message_hash}"

    def _get_last_user_message(self, messages: List[Dict]) -> str:
        """Get the most recent user message."""
        for msg in reversed(messages):
            if msg["role"] == "user":
                return msg["content"]
        return ""

    async def _auto_cleanup(self):
        """Automatically remove expired and excess cache entries."""
        while True:
            try:
                # Retrieve all cache keys for the current user
                pattern = f"{self.prefix}:meta:*"
                all_keys = [key.decode('utf-8') for key in self.redis.keys(pattern)]  # Decode keys
                
                if len(all_keys) > self.max_cache_size:
                    # Sort cache entries by access time
                    cache_items = []
                    for key in all_keys:
                        metadata = json.loads(self.redis.get(key.encode('utf-8')).decode('utf-8'))  # Encode the key before retrieving it
                        cache_items.append((key, metadata.get("last_access", 0)))
                    
                    # Sort by the most recent access time
                    cache_items.sort(key=lambda x: x[1])
                    
                    # Remove the oldest entries until the limit is reached
                    items_to_remove = len(all_keys) - self.max_cache_size
                    for key, _ in cache_items[:items_to_remove]:
                        hash_id = key.split(":")[-1]
                        await self._remove_cache_item(hash_id)
                        
                logger.info(f"Cache cleanup completed for prefix {self.prefix}")
                
            except Exception as e:
                logger.error(f"Error in cache cleanup: {str(e)}", exc_info=True)
                
            await asyncio.sleep(self.cleanup_interval)

    async def _remove_cache_item(self, hash_id: str):
        """Delete all keys associated with a cache entry."""
        try:
            # All keys must be encoded
            self.redis.delete(
                f"{self.prefix}:vec:{hash_id}".encode('utf-8'),
                f"{self.prefix}:resp:{hash_id}".encode('utf-8'),
                f"{self.prefix}:meta:{hash_id}".encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Error removing cache item: {str(e)}", exc_info=True)

    async def _update_metadata(self, message: str):
        """Update the metadata of a cache entry."""
        try:
            meta_key = self._get_metadata_key(message)
            # Redis returns bytes, so they must be decoded
            current_meta = self.redis.get(meta_key)
            if current_meta:
                current_meta = json.loads(current_meta.decode('utf-8'))
            else:
                current_meta = {"access_count": 0}
                
            metadata = {
                "last_access": datetime.now().timestamp(),
                "access_count": current_meta["access_count"] + 1
            }
            self.redis.set(meta_key, json.dumps(metadata), ex=settings.REDIS_CACHE_EXPIRE)
        except Exception as e:
            logger.error(f"Error updating metadata: {str(e)}", exc_info=True)

    async def lookup(self, messages: List[Dict]) -> Optional[str]:
        """Look up a cached response."""
        try:
            user_message = self._get_last_user_message(messages)
            if not user_message:
                return None

            current_vector = await self._get_embedding(user_message)
            
            # Retrieve all cached vectors for the current user
            pattern = f"{self.prefix}:vec:*"
            all_vectors = [key.decode('utf-8') for key in self.redis.keys(pattern)]  # Decode keys
            max_similarity = 0
            most_similar_key = None
            
            for vec_key in all_vectors:
                cached_vector = json.loads(self.redis.get(vec_key.encode('utf-8')).decode('utf-8'))  # Encode the key before retrieving it
                similarity = np.dot(current_vector, cached_vector) / (
                    np.linalg.norm(current_vector) * np.linalg.norm(cached_vector)
                )
                
                if similarity > max_similarity:
                    max_similarity = similarity
                    most_similar_key = vec_key
            
            if max_similarity >= self.score_threshold and most_similar_key:
                hash_id = most_similar_key.split(":")[-1]
                resp_key = f"{self.prefix}:resp:{hash_id}"
                cached_response = self.redis.get(resp_key.encode('utf-8'))  # Encode the key
                
                if cached_response:
                    # Update access metadata
                    await self._update_metadata(user_message)
                    logger.info(f"Cache hit with similarity: {max_similarity:.4f}")
                    return cached_response.decode('utf-8')
                    
            return None
            
        except Exception as e:
            logger.error(f"Error in lookup: {str(e)}", exc_info=True)
            return None

    async def update(self, messages: List[Dict], response: str, expire: int = None):
        """Update the cache."""
        try:
            user_message = self._get_last_user_message(messages)
            if not user_message:
                return

            vector = await self._get_embedding(user_message)
            
            vec_key = self._get_vector_key(user_message)
            resp_key = self._get_response_key(user_message)
            meta_key = self._get_metadata_key(user_message)
            
            expire = expire or settings.REDIS_CACHE_EXPIRE
            
            # Store the vector, response, and metadata as strings
            self.redis.set(vec_key, json.dumps(vector), ex=expire)
            self.redis.set(resp_key, response.encode('utf-8'), ex=expire)  # Encode as bytes
            
            metadata = {
                "created_at": datetime.now().timestamp(),
                "last_access": datetime.now().timestamp(),
                "access_count": 1
            }
            self.redis.set(meta_key, json.dumps(metadata), ex=expire)
            
            logger.info(f"Cache updated for message: {user_message[:50]}...")
            
        except Exception as e:
            logger.error(f"Error in update: {str(e)}", exc_info=True)