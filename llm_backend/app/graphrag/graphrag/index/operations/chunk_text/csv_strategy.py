"""A module containing run_csv function for CSV text chunking."""

from typing import List, Any

from graphrag.index.operations.chunk_text.typing import (
    ChunkingConfig, 
    TextChunk
)
from graphrag.logger.progress import ProgressTicker
from graphrag.index.text_splitting.text_splitting import TokenTextSplitter


def run_csv(
    texts: Any,
    config: ChunkingConfig,
    tick: ProgressTicker,
) -> List[TextChunk]:
    results = []

    token_splitter = TokenTextSplitter(chunk_size=config.size, chunk_overlap=config.overlap)

    for doc_idx, text in enumerate(texts):
        if not isinstance(text, str) or not text.strip():
            continue

        if "<ROW_SEP>" in text:
            rows = text.split("<ROW_SEP>")
            rows = [row.strip() for row in rows if row.strip()]
        else:
            rows = text.split("\n")
            rows = [row.strip() for row in rows if row.strip()]

        current_chunk_texts = []
        current_chunk_size = 0

        for row in rows:
            row_tokens = token_splitter.num_tokens(row)

            if row_tokens > config.size:
                if current_chunk_texts:
                    chunk_text = "\n\n".join(current_chunk_texts)
                    results.append(
                        TextChunk(
                            text_chunk=chunk_text,
                            source_doc_indices=[doc_idx],
                            n_tokens=current_chunk_size
                        )
                    )
                    current_chunk_texts = []
                    current_chunk_size = 0

                split_chunks = token_splitter.split_text(row)

                for chunk in split_chunks:
                    chunk_tokens = token_splitter.num_tokens(chunk)
                    results.append(
                        TextChunk(
                            text_chunk=chunk,
                            source_doc_indices=[doc_idx],
                            n_tokens=chunk_tokens
                        )
                    )
                continue

            if current_chunk_size + row_tokens > config.size and current_chunk_texts:
                chunk_text = "\n\n".join(current_chunk_texts)
                results.append(
                    TextChunk(
                        text_chunk=chunk_text,
                        source_doc_indices=[doc_idx],
                        n_tokens=current_chunk_size
                    )
                )
                current_chunk_texts = []
                current_chunk_size = 0

            current_chunk_texts.append(row)
            current_chunk_size += row_tokens

        if current_chunk_texts:
            chunk_text = "\n\n".join(current_chunk_texts)
            results.append(
                TextChunk(
                    text_chunk=chunk_text,
                    source_doc_indices=[doc_idx],
                    n_tokens=current_chunk_size
                )
            )

        tick()
    
    return results
