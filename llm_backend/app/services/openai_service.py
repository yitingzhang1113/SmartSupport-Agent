from typing import List, Dict, AsyncGenerator, Callable, Optional
from openai import AsyncOpenAI
from app.core.config import settings
import json
from app.core.logger import get_logger
from app.services.redis_semantic_cache import RedisSemanticCache
import time
import asyncio

logger = get_logger(service="openai")


class OpenAIService:
    def __init__(self, model: Optional[str] = None):
        logger.info("Initializing OpenAI Service")

        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=60.0,
            max_retries=2,
        )

        # Prefer the provided model; otherwise, use the OPENAI_MODEL defined in the configuration.
        self.model = model or settings.OPENAI_MODEL

        # Initialize the default semantic cache.
        self.cache = RedisSemanticCache(prefix="openai")

    async def _stream_cached_response(
        self,
        response: str,
        delay: float = 0.05
    ) -> AsyncGenerator[str, None]:
        """
        Stream a cached response.
        """
        chunks = [response[i:i + 4] for i in range(0, len(response), 4)]

        for chunk in chunks:
            await asyncio.sleep(delay)
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

    async def generate_stream(
        self,
        messages: List[Dict],
        user_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        on_complete: Optional[Callable[[int, int, List[Dict], str], None]] = None,
        save_messages: Optional[List[Dict]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response.
        """
        try:
            start_time = time.time()

            # Create an independent semantic cache for each user.
            cache = RedisSemanticCache(prefix="openai", user_id=user_id)

            # 1. Check the semantic cache.
            cached_response = await cache.lookup(messages)

            if cached_response:
                response_time = time.time() - start_time
                logger.info(f"OpenAI cache hit! Response time: {response_time:.4f} seconds")

                async for chunk in self._stream_cached_response(cached_response):
                    yield chunk

                if on_complete and user_id is not None and conversation_id is not None:
                    await on_complete(user_id, conversation_id, save_messages or messages, cached_response)

                return

            # 2. Cache miss. Call the OpenAI API.
            logger.info(f"Using OpenAI model: {self.model}")

            full_response: List[str] = []

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                temperature=0.3,
            )

            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    raw_content = chunk.choices[0].delta.content

                    # Store the complete raw response.
                    full_response.append(raw_content)

                    # Serialize the response for SSE output.
                    content_json = json.dumps(raw_content, ensure_ascii=False)
                    yield f"data: {content_json}\n\n"

            # async for event in response:
            #     if event.type == "response.output_text.delta":
            #         delta = event.delta
            #         full_response.append(delta)
            #         yield f"data: {json.dumps(delta, ensure_ascii=False)}\n\n"

            # 3. Assemble the complete response.
            complete_response = "".join(full_response)

            # 4. Update the semantic cache.
            if complete_response:
                await cache.update(messages, complete_response)

            response_time = time.time() - start_time
            logger.info(f"OpenAI cache miss. Response time: {response_time:.4f} seconds")

            # 5. Save the conversation history to MySQL.
            if on_complete and user_id is not None and conversation_id is not None:
                await on_complete(user_id, conversation_id, save_messages or messages, complete_response)

        except Exception as e:
            logger.error(f"Error in OpenAI generate_stream: {str(e)}", exc_info=True)
            error_msg = json.dumps(f"Error generating response: {str(e)}", ensure_ascii=False)
            yield f"data: {error_msg}\n\n"

    async def generate(self, messages: List[Dict]) -> str:
        """
        Generate a non-streaming response.
        """
        try:
            logger.info(f"Using OpenAI model: {self.model}")

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False,
                temperature=0.3,
            )

            return response.choices[0].message.content
            # return response.output_text

        except Exception as e:
            logger.error(f"OpenAI generation error: {str(e)}", exc_info=True)
            raise