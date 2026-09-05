import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any
import mimetypes
import shutil
import uuid

import graphrag.api as api
from graphrag.config.load_config import load_config
from graphrag.config.enums import IndexingMethod
from graphrag.logger.rich_progress import RichProgressLogger
from graphrag.index.typing.pipeline_run_result import PipelineRunResult

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(service="indexing")


class IndexingService:
    def __init__(self):
        self.project_dir = settings.GRAPHRAG_PROJECT_DIR
        self.data_dir_name = settings.GRAPHRAG_DATA_DIR
        self.data_dir = os.path.join(self.project_dir, self.data_dir_name)

        # Default GraphRAG configuration file
        self.default_config = "settings.yaml"

    def _get_file_type(self, file_path: str) -> str:
        """Detect the MIME type of the uploaded file."""
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or "application/octet-stream"

    def _get_config_file(self, file_type: str) -> str:
        """Return the configuration file for the specified file type."""
        return self.default_config

    def _check_existing_index(self, file_path: str, output_dir: str) -> bool:
        """Check whether an index already exists for the specified file."""
        file_name = Path(file_path).stem
        index_path = os.path.join(output_dir, f"{file_name}_index")
        return os.path.exists(index_path)

    def _prepare_user_directories(self, user_id: int) -> tuple:
        """Create isolated input and output directories for the user."""

        # Generate a deterministic UUID for the user
        user_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"user_{user_id}"))

        # Create the user's GraphRAG input directory
        user_input_dir = os.path.join(self.data_dir, "input", user_uuid)
        os.makedirs(user_input_dir, exist_ok=True)

        # Create the user's GraphRAG output directory
        user_output_dir = os.path.join(self.data_dir, "output", user_uuid)
        os.makedirs(user_output_dir, exist_ok=True)

        return user_input_dir, user_output_dir

    def _copy_file_to_input_dir(self, file_path: str, input_dir: str) -> str:
        """Copy the uploaded file into the GraphRAG input directory."""

        file_name = os.path.basename(file_path)
        dest_path = os.path.join(input_dir, file_name)

        shutil.copy2(file_path, dest_path)

        logger.info(f"Copied uploaded file to GraphRAG input directory: {dest_path}")

        return dest_path

    async def process_file(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Build a GraphRAG index for a single uploaded file."""

        try:
            file_path = file_info["path"]
            file_type = self._get_file_type(file_path)
            user_id = file_info.get("user_id", 0)

            logger.info(f"Processing uploaded file: {file_path}, MIME type: {file_type}, User ID: {user_id}")

            # Prepare user-specific working directories
            user_input_dir, user_output_dir = self._prepare_user_directories(user_id)

            # Copy the uploaded file into GraphRAG input
            input_file_path = self._copy_file_to_input_dir(file_path, user_input_dir)

            # Determine which configuration file to use
            config_file = self._get_config_file(file_type)

            logger.info(f"Using GraphRAG configuration: {config_file}")

            # Determine whether incremental indexing is required
            is_update = self._check_existing_index(input_file_path, user_output_dir)

            # Build configuration path
            config_path = os.path.join(self.data_dir, config_file)

            if not os.path.exists(config_path):
                logger.warning(f"Configuration file not found: {config_path}. Falling back to the default configuration.")
                config_path = os.path.join(self.data_dir, self.default_config)

            # Override runtime configuration
            config_overrides = {
                "input.base_dir": user_input_dir,
                "output.base_dir": user_output_dir,
                "input.file_pattern": f".*{os.path.basename(input_file_path)}$$",
            }

            # Load GraphRAG configuration
            graphrag_config = load_config(Path(self.data_dir), Path(config_path), config_overrides)

            # Create progress logger
            progress_logger = RichProgressLogger(prefix="graphrag-index")

            logger.info(f"Starting {'incremental indexing' if is_update else 'index construction'} for {input_file_path}")
            logger.info(f"Input directory: {user_input_dir}")
            logger.info(f"Output directory: {user_output_dir}")

            # Execute GraphRAG indexing
            index_result = await api.build_index(
                config=graphrag_config,
                method=IndexingMethod.Standard,
                is_update_run=is_update,
                memory_profile=False,
                progress_logger=progress_logger,
            )

            result_info = {
                "original_file_path": file_path,
                "input_file_path": input_file_path,
                "file_type": file_type,
                "config_used": config_file,
                "is_update": is_update,
                "status": "success",
                "user_id": user_id,
                "input_dir": user_input_dir,
                "output_dir": user_output_dir,
            }

            # Check whether any workflow failed
            for workflow_result in index_result:
                if workflow_result.errors:
                    result_info["status"] = "error"
                    result_info["errors"] = workflow_result.errors

                    logger.error(f"GraphRAG indexing failed: {workflow_result.errors}")

            return result_info

        except Exception as e:
            logger.error(f"Error occurred while processing uploaded file: {str(e)}", exc_info=True)

            return {
                "file_path": file_info.get("path", ""),
                "status": "error",
                "error": str(e),
            }

    async def process_directory(self, directory_path: str, user_id: int = 0) -> Dict[str, Any]:
        """Build GraphRAG indexes for all files within a directory."""

        try:
            results = []

            for root, _, files in os.walk(directory_path):
                for file in files:
                    file_path = os.path.join(root, file)

                    file_info = {
                        "path": file_path,
                        "original_name": file,
                        "user_id": user_id,
                    }

                    result = await self.process_file(file_info)
                    results.append(result)

            return {
                "status": "success",
                "processed_files": len(results),
                "results": results,
            }

        except Exception as e:
            logger.error(f"Error occurred while processing directory: {str(e)}", exc_info=True)

            return {
                "status": "error",
                "error": str(e),
            }