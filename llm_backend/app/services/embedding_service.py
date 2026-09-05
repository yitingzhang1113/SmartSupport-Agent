from typing import Dict, List, Optional
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import json
from pathlib import Path
import os
import hashlib
import time
import PyPDF2

class EmbeddingService:
    def __init__(self):
        # Use a multilingual model to support multiple languages.
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self.index_dir = Path("indexes")
        self.index_dir.mkdir(exist_ok=True)

        # Initialize an empty index and document store.
        self.dimension = 384  # Must match the output dimension of the embedding model.
        self.current_index = None
        self.current_documents = {}

    def _generate_safe_id(self, metadata: dict) -> str:
        """Generate a safe file ID."""
        # Generate a unique ID using the timestamp and file information.
        timestamp = str(int(time.time()))
        file_info = f"{metadata.get('filename', '')}_{timestamp}"
        # Generate a safe filename using MD5.
        return hashlib.md5(file_info.encode()).hexdigest()

    def _create_index(self) -> faiss.IndexFlatL2:
        """Create a new FAISS index."""
        return faiss.IndexFlatL2(self.dimension)

    def _get_index_path(self, file_path: str) -> str:
        """Generate the index file path."""
        # Use the hash of the file path as the index filename.
        file_hash = hashlib.md5(file_path.encode()).hexdigest()
        return f"indexes/index_{file_hash}.bin"

    async def create_embeddings(self, file_path: str, index_dir: str) -> Dict:
        """Create a vector index from a file."""
        try:
            # Read the PDF content.
            text_chunks = []
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text_chunks.append(page.extract_text())

            # Create a new index.
            index = self._create_index()

            # Generate embeddings using SentenceTransformer.
            vectors = self.model.encode(text_chunks)
            vectors = vectors.astype('float32')  # Ensure the correct data type.

            # Add embeddings to the index.
            index.add(vectors)

            # Generate the file ID.
            file_hash = hashlib.md5(file_path.encode()).hexdigest()
            index_id = f"index_{file_hash}"

            # Create document metadata.
            documents = {}
            for i, text in enumerate(text_chunks):
                documents[str(i)] = {
                    "text": text,
                    "metadata": {
                        "page": i + 1,
                        "source": file_path
                    }
                }

            # Save the index and document metadata.
            self._save_index(file_hash, index, documents)

            return {
                "status": "success",
                "index_id": index_id,
                "chunks": len(text_chunks)
            }

        except Exception as e:
            raise Exception(f"Failed to create embeddings: {str(e)}")

    def _save_index(self, file_id: str, index: faiss.Index, documents: dict):
        """Save the index and document metadata."""
        try:
            # Use a safe filename.
            index_path = self.index_dir / f"index_{file_id}.bin"  # Add the "index_" prefix.
            docs_path = self.index_dir / f"docs_{file_id}.json"

            # Save the FAISS index.
            faiss.write_index(index, str(index_path))

            # Save the document metadata.
            with open(docs_path, 'w', encoding='utf-8') as f:
                json.dump(documents, f, ensure_ascii=False, indent=2)

        except Exception as e:
            raise Exception(f"Failed to save the index: {str(e)}")

    def _load_index(self, index_id: str):
        """Load the index and document metadata."""
        try:
            # Use the same filename format as when saving.
            index_path = self.index_dir / f"{index_id}.bin"  # Do not add the "index_" prefix because index_id already contains it.
            docs_path = self.index_dir / f"docs_{index_id.replace('index_', '')}.json"

            if not index_path.exists() or not docs_path.exists():
                # Try the legacy filename format.
                old_index_path = self.index_dir / f"index_{index_id}.bin"
                old_docs_path = self.index_dir / f"docs_{index_id}.json"

                if old_index_path.exists() and old_docs_path.exists():
                    index_path = old_index_path
                    docs_path = old_docs_path
                else:
                    raise FileNotFoundError(f"Index file not found: {index_id}")

            # Load the FAISS index.
            self.current_index = faiss.read_index(str(index_path))

            # Validate the embedding dimension.
            if self.current_index.d != self.dimension:
                raise ValueError(f"Embedding dimension mismatch: expected {self.dimension}, got {self.current_index.d}")

            # Load the document metadata.
            with open(docs_path, 'r', encoding='utf-8') as f:
                self.current_documents = json.load(f)

            # Verify that documents exist.
            if not self.current_documents:
                raise ValueError("The document store is empty.")

            print(f"Successfully loaded index {index_id}: {self.current_index.ntotal} vectors, {len(self.current_documents)} documents")

        except Exception as e:
            self.current_index = None
            self.current_documents = {}
            raise Exception(f"Failed to load the index: {str(e)}")

    async def search(self, query: str, top_k: int = 3) -> List[dict]:
        """Search for the most relevant document chunks."""
        try:
            if not self.current_index:
                raise Exception("No index has been loaded.")

            # Generate the query embedding.
            query_vector = self.model.encode([query], convert_to_tensor=False)
            query_vector = query_vector.astype('float32')

            # Search for the most similar embeddings.
            distances, indices = self.current_index.search(query_vector, top_k)

            # Return the search results.
            results = []
            for i in range(len(indices[0])):
                idx_str = str(int(indices[0][i]))
                if idx_str in self.current_documents:
                    results.append({
                        "score": float(distances[0][i]),
                        "content": self.current_documents[idx_str]["text"],
                        "metadata": self.current_documents[idx_str]["metadata"]
                    })

            return results

        except Exception as e:
            raise Exception(f"Search failed: {str(e)}")