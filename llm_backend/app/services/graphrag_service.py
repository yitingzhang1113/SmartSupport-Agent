import asyncio
from pathlib import Path

from app.core.config import settings
from app.core.logger import get_logger


logger = get_logger(service="graphrag_service")


class GraphRAGService:
    """Microsoft GraphRAG query service.

    The current implementation invokes GraphRAG through the CLI.
    This can be replaced with the GraphRAG Python API in the future.
    """

    def __init__(self):
        self.project_dir = Path(settings.GRAPHRAG_PROJECT_DIR).expanduser().resolve()
        self.query_type = settings.GRAPHRAG_QUERY_TYPE


    async def _query(self, query: str, root_dir: Path, method: str = "local") -> str:
        if not self.project_dir.exists():
            logger.error(f"GraphRAG project directory not found: {self.project_dir}")
            return "Sorry, the GraphRAG project directory is not configured correctly."

        if not root_dir.exists():
            logger.error(f"GraphRAG knowledge base directory not found: {root_dir}")
            return "Sorry, the GraphRAG knowledge base directory is not configured correctly."

        process = await asyncio.create_subprocess_exec(
            "poetry",
            "run",
            "poe",
            "query",
            "--root",
            str(root_dir),
            "--method",
            method,
            "--query",
            query,
            cwd=str(self.project_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        stdout_text = stdout.decode("utf-8", errors="ignore")
        stderr_text = stderr.decode("utf-8", errors="ignore")

        if process.returncode != 0:
            logger.error(f"GraphRAG query failed: {stderr_text}")
            return "Sorry, I could not retrieve information from the knowledge base."

        markers = [
            "SUCCESS: Local Search Response:",
            "SUCCESS: Global Search Response:",
            "SUCCESS: Basic Search Response:",
            "SUCCESS: DRIFT Search Response:",
        ]

        for marker in markers:
            if marker in stdout_text:
                return stdout_text.split(marker, 1)[1].strip()

        return stdout_text.strip()


graphrag_service = GraphRAGService()