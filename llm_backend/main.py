from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import uuid
import os
import json
import aiofiles
from app.services.llm_factory import LLMFactory
from app.services.indexing_service import IndexingService
from app.services.conversation_service import ConversationService

from app.core.logger import get_logger, log_structured
from app.core.middleware import LoggingMiddleware

from app.lg_agent.lg_states import InputState
from app.lg_agent.utils import new_uuid
from app.lg_agent.lg_builder import graph
from langgraph.types import Command
from langchain_core.runnables import RunnableConfig

logger = get_logger(service="main")


BASE_DIR = Path(__file__).resolve().parent

IMAGE_UPLOAD_DIR = BASE_DIR / "data" / "uploads" / "images"
IMAGE_UPLOAD_DIR.mkdir(parents=True,exist_ok=True)

# UPLOAD_DIR = Path("uploads")
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

ALLOWED_IMAGE_SUFFIXES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

MAX_IMAGE_SIZE = 10 * 1024 * 1024

async def save_uploaded_image(image: UploadFile) -> str:
    """
    Validate and save an uploaded image.
    Args:
        image: Image file received from the client.
    Returns:
        Absolute path of the saved image.
    Raises:
        HTTPException: Raised when the image type or image size is invalid.
    """
    if image.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported image type. Only JPEG, PNG, and WEBP images are supported.",
        )

    original_filename = image.filename or "uploaded_image"
    suffix = Path(original_filename).suffix.lower()

    if suffix not in ALLOWED_IMAGE_SUFFIXES:
        if image.content_type == "image/png":
            suffix = ".png"
        elif image.content_type == "image/webp":
            suffix = ".webp"
        else:
            suffix = ".jpg"

    saved_filename = f"{uuid.uuid4().hex}{suffix}"
    saved_path = IMAGE_UPLOAD_DIR / saved_filename

    total_size = 0
    chunk_size = 1024 * 1024

    try:
        async with aiofiles.open(saved_path, "wb") as output_file:
            while True:
                chunk = await image.read(chunk_size)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_IMAGE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="The uploaded image exceeds the 10 MB limit.",
                    )

                await output_file.write(chunk)
    except HTTPException:
        if saved_path.exists():
            saved_path.unlink()
        raise

    except Exception as e:
        if saved_path.exists():
            saved_path.unlink()
        logger.error(f"Failed to save uploaded image: {e}", exc_info=True)
        raise HTTPException(status_code=500,detail="Failed to save the uploaded image.")

    finally:
        await image.close()
    resolved_path = saved_path.resolve()

    logger.info(
        "Uploaded image saved successfully: "
        f"original_filename={original_filename}, "
        f"content_type={image.content_type}, "
        f"size={total_size}, "
        f"path={resolved_path}"
    )
    return str(resolved_path)

app = FastAPI(
    title="Smart Support Agent API",
    description="Backend for AI customer service agent",
    version="1.0.0",
)

app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://192.168.5.X:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    messages: List[Dict[str, str]]
    user_id: Optional[int] = 1
    conversation_id: Optional[int] = 1

class ReasonRequest(BaseModel):
    messages: List[Dict[str, str]]
    user_id: Optional[int] = 1

class RAGChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    index_id: str
    user_id: Optional[int] = 1

class CreateConversationRequest(BaseModel):
    user_id: Optional[int] = 1

class UpdateConversationNameRequest(BaseModel):
    name: str

class LangGraphRequest(BaseModel):
    query: str
    user_id: int
    conversation_id: Optional[str] = None
    image: Optional[UploadFile] = None

class LangGraphResumeRequest(BaseModel):
    query: str
    user_id: Optional[int] = 1
    conversation_id: str

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Smart-Support-agent"}

@app.get("/api/users/me")
async def get_current_user_info():
    return {
        "id": 10,
        "username": "Anna",
        "email": "demo@example.com",
        "is_active": True,
        "last_login": None
    }

# ---------------- 商城商品接口(直接读 Business_data,不走 LLM)----------------
import csv as _csv
from functools import lru_cache

BUSINESS_DATA_DIR = BASE_DIR.parent / "Business_data"
PRODUCT_IMAGE_DIR = BUSINESS_DATA_DIR / "products_image"

# 把用户的商品图片目录挂到 /product-images(文件名=商品名.png/jpg/webp)
if PRODUCT_IMAGE_DIR.exists():
    app.mount("/product-images", StaticFiles(directory=str(PRODUCT_IMAGE_DIR)), name="product-images")
else:
    logger.warning(f"Product image directory not found: {PRODUCT_IMAGE_DIR}")


@lru_cache(maxsize=1)
def _load_products():
    """从 Business_data 加载商品(含分类名、供应商名),结果缓存。"""
    data_dir = BUSINESS_DATA_DIR

    def read(name):
        path = data_dir / name
        if not path.exists():
            return []
        with open(path, newline="", encoding="utf-8-sig") as f:
            return list(_csv.DictReader(f))

    categories = {r["CategoryID"]: r["CategoryName"] for r in read("Categories.csv")}
    suppliers = {r["SupplierID"]: r["CompanyName"] for r in read("Suppliers.csv")}

    products = []
    seen = set()
    for r in read("Products.csv"):
        pid = r.get("ProductID")
        if pid in seen:
            continue
        seen.add(pid)
        try:
            price = float(r.get("UnitPrice") or 0)
        except ValueError:
            price = 0.0
        try:
            stock = int(r.get("UnitsInStock") or 0)
        except ValueError:
            stock = 0
        products.append(
            {
                "id": pid,
                "name": r.get("ProductName", ""),
                "price": price,
                "stock": stock,
                "category": categories.get(r.get("CategoryID"), ""),
                "supplier": suppliers.get(r.get("SupplierID"), ""),
                "quantityPerUnit": r.get("QuantityPerUnit", ""),
            }
        )
    return products


def _image_index():
    """扫描 products_image 目录,返回 {商品名小写: /product-images/文件名}。
    每次调用实时扫描(文件不多),用户新增图片无需重启。"""
    idx = {}
    if not PRODUCT_IMAGE_DIR.exists():
        return idx
    exts = {".png", ".jpg", ".jpeg", ".webp"}
    for p in PRODUCT_IMAGE_DIR.iterdir():
        if p.suffix.lower() in exts:
            from urllib.parse import quote
            idx[p.stem.strip().lower()] = "/product-images/" + quote(p.name)
    return idx


def _attach_images(items):
    idx = _image_index()
    out = []
    for p in items:
        q = dict(p)
        q["image"] = idx.get(p["name"].strip().lower())
        out.append(q)
    return out


@app.get("/api/products")
async def list_products(
    category: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 50,
):
    """商品列表:可按分类(category)或关键词(q)筛选。直接读 Business_data,秒回。"""
    items = _load_products()
    if category:
        c = category.strip().lower()
        items = [p for p in items if p["category"].lower() == c]
    if q:
        kw = q.strip().lower()
        items = [
            p for p in items
            if kw in p["name"].lower() or kw in p["category"].lower()
        ]
    total = len(items)
    items = items[: max(1, min(limit, 200))]
    return {"total": total, "items": _attach_images(items)}


@app.get("/api/products/detail")
async def product_detail(name: str):
    """按名称取单个商品详情(精确优先,否则模糊)。"""
    items = _load_products()
    n = name.strip().lower()
    exact = next((p for p in items if p["name"].lower() == n), None)
    fuzzy = exact or next((p for p in items if n in p["name"].lower()), None)
    if fuzzy:
        return _attach_images([fuzzy])[0]
    raise HTTPException(status_code=404, detail="Product not found")


@app.get("/api/categories")
async def list_categories():
    """所有分类及其商品数量。"""
    items = _load_products()
    counts = {}
    for p in items:
        counts[p["category"]] = counts.get(p["category"], 0) + 1
    cats = [{"name": k, "count": v} for k, v in counts.items() if k]
    cats.sort(key=lambda x: x["name"])
    return {"items": cats}


@app.post("/api/chat")
async def chat_endpoint(request: ChatMessage):
    try:
        logger.info(
            f"Processing chat request, user_id={request.user_id}, "
            f"conversation_id={request.conversation_id}"
        )

        chat_service = LLMFactory.create_chat_service()

        history_messages = []

        if request.conversation_id:
            db_messages = await ConversationService.get_conversation_messages(
                conversation_id=request.conversation_id,
                user_id=request.user_id
            )

            for msg in db_messages:
                if msg["sender"] == "user":
                    history_messages.append({
                        "role": "user",
                        "content": msg["content"]
                    })
                elif msg["sender"] == "assistant":
                    history_messages.append({
                        "role": "assistant",
                        "content": msg["content"]
                    })

        full_messages = history_messages + request.messages

        return StreamingResponse(
            chat_service.generate_stream(
                messages=full_messages,
                save_messages=request.messages,  
                user_id=request.user_id,
                conversation_id=request.conversation_id,
                on_complete=ConversationService.save_message,
            ),
            media_type="text/event-stream",
        )

    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Inference model interface
@app.post("/api/reason")
async def reason_endpoint(request: ReasonRequest):
    """
     Reasoning model interface.
     Suitable for OpenAI reasoning models, DeepSeek-R1, etc.
     Returns the full response instead of streaming.
    """
    try:
        logger.info(f"Processing reasoning request, user_id={request.user_id}")

        reasoner = LLMFactory.create_reasoner_service()

        log_structured("reason_request", {
            "user_id": request.user_id,
            "message_count": len(request.messages),
            "last_message": request.messages[-1]["content"][:100]
            if request.messages else "",
        })

        return StreamingResponse(
            reasoner.generate_stream(request.messages),
            media_type="text/event-stream",
        )

    except Exception as e:
        logger.error(f"Reasoning error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/api/search")
async def search_endpoint(request: ChatMessage):
    """
    Search-enhanced chat interface.
    Used in scenarios where enhanced search services are needed to provide more informative responses.
    """
    try:
        logger.info(
            f"Processing search request, user_id={request.user_id}, "
            f"conversation_id={request.conversation_id}"
        )

        search_service = LLMFactory.create_search_service()

        query = request.messages[-1]["content"] if request.messages else ""

        return StreamingResponse(
            search_service.generate_stream(
                query=query,
                user_id=request.user_id,
                conversation_id=request.conversation_id,
            ),
            media_type="text/event-stream",
        )

    except Exception as e:
        logger.error(f"Search error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# File upload + RAG indexing interface
@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    user_id: int = Form(1),
):
    """
    Upload the file and build the RAG index.
    No login is required. The default user_id is 1.
    """
    try:
        logger.info(f"Uploading file for user_id={user_id}: {file.filename}")

        user_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"user_{user_id}"))
        first_level_dir = UPLOAD_DIR / user_uuid

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        second_level_dir = first_level_dir / timestamp
        second_level_dir.mkdir(parents=True, exist_ok=True)

        original_name, ext = os.path.splitext(file.filename)
        new_filename = f"{original_name}_{timestamp}{ext}"
        file_path = second_level_dir / new_filename

        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        file_info = {
            "filename": new_filename,
            "original_name": file.filename,
            "size": len(content),
            "type": file.content_type,
            "path": str(file_path).replace("\\", "/"),
            "user_id": user_id,
            "user_uuid": user_uuid,
            "upload_time": timestamp,
            "directory": str(second_level_dir),
        }

        indexing_service = IndexingService()
        index_result = await indexing_service.process_file(file_info)

        return {
            **file_info,
            "index_result": index_result,
        }

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/conversations")
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation"""
    try:
        conversation_id = await ConversationService.create_conversation(request.user_id)
        return {"conversation_id": conversation_id}
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations/user/{user_id}")
async def get_user_conversations(user_id: int):
    """Retrieve all conversations of the user"""
    try:
        conversations = await ConversationService.get_user_conversations(user_id)
        return conversations
    except Exception as e:
        logger.error(f"Error getting conversations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: int, user_id: int):
    """Retrieve all messages of a conversation"""
    try:
        messages = await ConversationService.get_conversation_messages(conversation_id, user_id)
        return messages
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting messages: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int):
    """Delete the conversation and all its messages"""
    try:
        conversation_service = ConversationService()
        await conversation_service.delete_conversation(conversation_id)
        return {"message": "The conversation has been deleted."}
    except Exception as e:
        logger.error(f"Session deletion failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/conversations/{conversation_id}/name")
async def update_conversation_name(
    conversation_id: int,
    request: UpdateConversationNameRequest
):
    """Modify the name of the conversation"""
    try:
        conversation_service = ConversationService()
        await conversation_service.update_conversation_name(conversation_id, request.name)
        return {"message": "Session name has been updated"}
    except Exception as e:
        logger.error(f"Failed to update the conversation name: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/langgraph/query")
async def langgraph_query(
    query: str = Form(...),
    user_id: int = Form(11),
    conversation_id: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
):
    """
    The core interface of the LangGraph customer service agent.

    Current version:
    - No login required
    - No permissions
    - Supports text-based customer service inquiries
    - Supports optional image upload
    - Supports SSE streaming responses
    """
    image_path: Optional[str] = None

    try:
        logger.info(
            f"Processing LangGraph query, user_id={user_id}, "
            f"conversation_id={conversation_id}, "
            f"has_image={image is not None}"
        )

        thread_id = conversation_id if conversation_id else new_uuid()

        if image is not None:
            image_path = await save_uploaded_image(image)

        configurable = {
            "thread_id": thread_id,
            "user_id": user_id,
        }

        if image_path:
            configurable["image_path"] = image_path

        thread_config: RunnableConfig = {"configurable": configurable}

        logger.info(
            f"[LANGGRAPH_CONFIG] thread_id={thread_id}, "
            f"user_id={user_id}, "
            f"image_path={image_path}"
        )

        try:
            state_snapshot = graph.get_state(thread_config)

            if state_snapshot and getattr(state_snapshot, "values", None):
                logger.info(f"Found existing state for thread_id={thread_id}")

        except Exception as e:
            logger.warning(f"Could not retrieve graph state: {e}")

        async def process_stream():
            try:
                graph_input = InputState(messages=query)
                async for c, metadata in graph.astream(graph_input,stream_mode="messages",config=thread_config):
                    logger.info(f"LangGraph metadata: {metadata}")
                    logger.info(f"LangGraph content: {c.content}")

                    node_name = metadata.get("langgraph_node")
                    tags = metadata.get("tags", [])

                    if node_name == "analyze_and_route_query" or "router" in tags:
                        logger.warning(f"[ROUTER_SKIPPED] content={repr(c.content)}")
                        logger.warning(f"[ROUTER_SKIPPED] kwargs={c.additional_kwargs}")
                        continue

                    if c.content and not c.additional_kwargs.get("tool_calls"):
                        content = str(c.content).strip()

                        if "guardrail" in tags:
                            logger.warning(f"[FILTER_GUARDRAIL_TAG] content={repr(content)}")
                            continue

                        if content in ["continue", "end"]:
                            logger.warning(f"[FILTER_GUARDRAIL_DECISION] content={repr(content)}")
                            continue

                        if '"decision"' in content or "'decision'" in content:
                            logger.warning(f"[FILTER_GUARDRAIL_JSON] content={repr(content)}")
                            continue

                        if "research_plan" not in tags:
                            if content and content.isascii():
                                punctuation = {".", ",", "!", "?", ":", ";", "'", '"', ")", "]", "}"}

                                if content not in punctuation:
                                    content = content + " "

                            logger.info(f"[SSE_YIELD] content={repr(content)}")

                            content_json = json.dumps(content, ensure_ascii=False)

                            yield f"data: {content_json}\n\n"

                    elif c.additional_kwargs.get("tool_calls"):
                        tool_calls = c.additional_kwargs.get("tool_calls", [])

                        for tool_call in tool_calls:
                            function = tool_call.get("function", {})
                            tool_name = function.get("name")
                            tool_args = function.get("arguments")

                            logger.warning(f"[TOOL_CALL] node={node_name}")
                            logger.warning(f"[TOOL_CALL] name={tool_name}")
                            logger.warning(f"[TOOL_CALL] args={tool_args}")

                try:
                    state = graph.get_state(thread_config)
                    tasks = getattr(state, "tasks", None)

                    if tasks:
                        for task in tasks:
                            interrupts = getattr(task, "interrupts", None)

                            if interrupts:
                                interrupt_json = json.dumps(
                                    {
                                        "interruption": True,
                                        "conversation_id": thread_id,
                                    },
                                    ensure_ascii=False,
                                )

                                yield f"data: {interrupt_json}\n\n"
                                break

                except Exception as e:
                    logger.warning(f"Could not inspect interrupt state: {e}")

                done_json = json.dumps(
                    {
                        "done": True,
                        "conversation_id": thread_id,
                    },
                    ensure_ascii=False,
                )

                yield f"data: {done_json}\n\n"

            except Exception as stream_error:
                logger.error(f"LangGraph stream error: {stream_error}",exc_info=True)

                error_json = json.dumps(
                    {
                        "error": str(stream_error),
                        "conversation_id": thread_id,
                    },
                    ensure_ascii=False,
                )

                yield f"data: {error_json}\n\n"

            finally:
                if image_path:
                    try:
                        image_file = Path(image_path)

                        if image_file.is_file():
                            image_file.unlink()
                            logger.info(f"Temporary uploaded image deleted: {image_path}")

                    except Exception as cleanup_error:
                        logger.warning(f"Could not delete temporary uploaded image: {cleanup_error}")

        response = StreamingResponse(process_stream(),media_type="text/event-stream")

        response.headers["X-Conversation-ID"] = thread_id
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Connection"] = "keep-alive"

        return response

    except HTTPException:
        if image_path:
            try:
                image_file = Path(image_path)
                if image_file.is_file():
                    image_file.unlink()
            except Exception as cleanup_error:
                logger.warning(f"Could not clean up uploaded image after HTTP error: {cleanup_error}")
        raise

    except Exception as e:
        if image_path:
            try:
                image_file = Path(image_path)
                if image_file.is_file():
                    image_file.unlink()
            except Exception as cleanup_error:
                logger.warning(f"Could not clean up uploaded image after query error: {cleanup_error}")
        logger.error(f"LangGraph query error: {str(e)}", exc_info=True)

        raise HTTPException(status_code=500,detail=str(e))


# LangGraph Resume interface
@app.post("/api/langgraph/resume")
async def langgraph_resume(request: LangGraphResumeRequest):
    """
    The interruption and recovery interface in LangGraph.
    Used in scenarios where human involvement is required or when additional user information is needed.
    """
    try:
        logger.info(
            f"Resuming LangGraph query, user_id={request.user_id}, "
            f"conversation_id={request.conversation_id}"
        )

        thread_config = {
            "configurable": {
                "thread_id": request.conversation_id,
                "user_id": request.user_id,
            }
        }

        async def process_resume():
            async for c, metadata in graph.astream(
                Command(resume=request.query),
                stream_mode="messages",
                config=thread_config,
            ):
                node_name = metadata.get("langgraph_node")
                tags = metadata.get("tags", [])
                if c.content and not c.additional_kwargs.get("tool_calls"):
                    if "research_plan" not in tags:
                        content = c.content

                        if isinstance(content, str) and content.strip() and content.isascii():
                            punctuation = {".", ",", "!", "?", ":", ";", "'", '"', ")", "]", "}"}
                            if content not in punctuation:
                                content = content + " "

                        # yield f"data: {content}\n\n"
                        content_json = json.dumps(content, ensure_ascii=False)
                        yield f"data: {content_json}\n\n"
                elif c.additional_kwargs.get("tool_calls"):
                    tool_data = c.additional_kwargs.get("tool_calls")[0]["function"].get("arguments")
                    logger.debug(f"Tool call: {tool_data}")

            done_json = json.dumps({
                "done": True,
                "conversation_id": request.conversation_id,
            }, ensure_ascii=False)
            yield f"data: {done_json}\n\n"
        return StreamingResponse(
            process_resume(),
            media_type="text/event-stream",
        )

    except Exception as e:
        logger.error(f"LangGraph resume error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

STATIC_DIR = Path(__file__).parent / "static" / "dist"

if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
else:
    logger.warning(f"Static frontend directory not found: {STATIC_DIR}")