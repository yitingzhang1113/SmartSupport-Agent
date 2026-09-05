from typing import List, Dict, AsyncGenerator, Callable, Optional
from openai import AsyncOpenAI
from app.core.config import settings
import json
from app.core.logger import get_logger
from app.core.database import AsyncSessionLocal
from app.models.conversation import Conversation, DialogueType
from app.models.message import Message
from app.services.redis_semantic_cache import RedisSemanticCache
import time
import asyncio

logger = get_logger(service="deepseek")

class DeepseekService:
    def __init__(self, model: str = "deepseek-chat"):
        logger.info("Initializing Deepseek Service")
        # self.client = AsyncOpenAI(
        #     api_key=settings.DEEPSEEK_API_KEY,
        #     base_url=settings.DEEPSEEK_BASE_URL
        # )
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY
        )
        # Prefer the DEEPSEEK_MODEL defined in the configuration; otherwise, use the provided model.
        self.model = settings.DEEPSEEK_MODEL or model
        self.cache = RedisSemanticCache(prefix="deepseek")

    async def _stream_cached_response(self, response: str, delay: float = 0.05) -> AsyncGenerator[str, None]:
        """Simulate streaming a cached response."""
        # Return 4 characters at a time.
        chunks = [response[i:i + 4] for i in range(0, len(response), 4)]
        for chunk in chunks:
            await asyncio.sleep(delay)  # 50 ms delay
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

    async def generate_stream(
        self,
        messages: List[Dict],
        user_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        on_complete: Optional[Callable[[int, int, List[Dict], str], None]] = None
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response."""
        try:
            # Create an independent cache instance for each user.
            cache = RedisSemanticCache(prefix="deepseek", user_id=user_id)

            start_time = time.time()

            # Check the cache.
            cached_response = await cache.lookup(messages)
            if cached_response:
                response_time = time.time() - start_time
                logger.info(f"Cache hit! Response time: {response_time:.4f} seconds")

                # Simulate streaming because returning the cached response is too fast.
                async for chunk in self._stream_cached_response(cached_response):
                    yield chunk

                if on_complete and user_id is not None and conversation_id is not None:
                    await on_complete(user_id, conversation_id, messages, cached_response)
                return

            # Cache miss. Call the API.
            full_response = []
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True
            )

            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    # Use ensure_ascii=False to preserve Unicode characters.
                    content = json.dumps(chunk.choices[0].delta.content, ensure_ascii=False)

                    full_response.append(content)
                    yield f"data: {content}\n\n"

            # Complete response.
            complete_response = "".join(full_response)

            # Update the cache.
            await cache.update(messages, complete_response)

            response_time = time.time() - start_time
            logger.info(f"Cache miss. Response time: {response_time:.4f} seconds")

            # Execute the callback if provided.
            if on_complete and user_id is not None and conversation_id is not None:
                await on_complete(user_id, conversation_id, messages, complete_response)

        except Exception as e:
            logger.error(f"Error in generate_stream: {str(e)}", exc_info=True)
            error_msg = json.dumps(f"Error generating response: {str(e)}", ensure_ascii=False)
            yield f"data: {error_msg}\n\n"

    async def generate(self, messages: List[Dict]) -> str:
        """Generate a non-streaming response."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Generation error: {str(e)}")
            raise