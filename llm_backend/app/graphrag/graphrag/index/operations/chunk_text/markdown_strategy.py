# Licensed under the MIT License

"""Markdown-based text chunking strategy."""

import re
from collections.abc import Iterable
import logging
import csv
import os
from datetime import datetime
import json

from graphrag.config.models.chunking_config import ChunkingConfig
from graphrag.index.operations.chunk_text.typing import TextChunk
from graphrag.logger.progress import ProgressTicker
from graphrag.index.text_splitting.text_splitting import TokenTextSplitter

log = logging.getLogger(__name__)

def run_markdown(
    input: list[str],
    config: ChunkingConfig,
    tick: ProgressTicker,
) -> Iterable[TextChunk]:
    """Chunks text based on Markdown structure, keeping tables and images with their context."""

    token_splitter = TokenTextSplitter(chunk_size=config.size, chunk_overlap=config.overlap)

    all_chunks = []

    size_tolerance = int(config.size * 0.5)
    max_size_with_tolerance = config.size + size_tolerance

    absolute_max_size = config.size * 2  
    parsed_docs = []
    for doc_idx, text in enumerate(input):
        if not text:
            tick(1)
            continue

        parsed_elements = parse_markdown_with_metadata(text)
        parsed_docs.append({
            "doc_idx": doc_idx,
            "elements": parsed_elements,
            "original_text": text
        })

    def group_by_headings(elements):
        groups = []
        current_group = []
        current_headings = []
        header_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        
        for element in elements:
            content = element["content"]
            header_match = header_pattern.match(content.strip())
            
            if header_match:
                header_level = len(header_match.group(1))
                if header_level == 1 and current_group:
                    groups.append((current_headings, current_group))
                    current_group = []
                    current_headings = [content]
                else:
                    while current_headings and len(header_pattern.match(current_headings[-1].strip()).group(1)) >= header_level:
                        current_headings.pop()
                    current_headings.append(content)
                    current_group.append(element)
            else:
                current_group.append(element)

        if current_group:
            groups.append((current_headings, current_group))
        
        return groups

    for parsed_doc in parsed_docs:
        doc_idx = parsed_doc["doc_idx"]
        elements = parsed_doc["elements"]

        grouped_elements = group_by_headings(elements)
        
        for headings, group_elements in grouped_elements:
            current_chunk = []
            current_metadata = {}
            
            for element in group_elements:
                content = element["content"]
                metadata = element.get("metadata", {})

                current_chunk.append(content)

                current_metadata.update(metadata)

                chunk_text = "\n\n".join(current_chunk)
                chunk_size = token_splitter.num_tokens(chunk_text)

                if chunk_size > absolute_max_size:
                    chunk_metadata = current_metadata.copy()
                    chunk_metadata["parent_headings"] = headings

                    metadata_str = json.dumps(chunk_metadata, ensure_ascii=False, indent=2)
                    full_text = f"METADATA:\n{metadata_str}\n\nCONTENT:\n{chunk_text}"

                    chunk = TextChunk(
                        text_chunk=full_text,
                        source_doc_indices=[doc_idx],
                        n_tokens=chunk_size,
                    )
                    all_chunks.append(chunk)

                    yield chunk

                    current_chunk = []
                    current_metadata = {}

            if current_chunk:
                chunk_text = "\n\n".join(current_chunk)
                chunk_metadata = current_metadata.copy()
                chunk_metadata["parent_headings"] = headings

                metadata_str = json.dumps(chunk_metadata, ensure_ascii=False, indent=2)
                full_text = f"METADATA:\n{metadata_str}\n\nCONTENT:\n{chunk_text}"

                n_tokens = token_splitter.num_tokens(chunk_text)

                chunk = TextChunk(
                    text_chunk=full_text,
                    source_doc_indices=[doc_idx],
                    n_tokens=n_tokens,
                )
                all_chunks.append(chunk)

                yield chunk
        
        tick(1)

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = f"chunk_results_{timestamp}.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(['doc_idx', 'chunk_idx', 'n_tokens', 'text_chunk'])
            
            for i, chunk in enumerate(all_chunks):
                csv_writer.writerow([
                    chunk.source_doc_indices[0] if chunk.source_doc_indices else 0,
                    i + 1,
                    chunk.n_tokens,
                    chunk.text_chunk
                ])
        
        print(f"分块结果已保存到: {os.path.abspath(csv_path)}")
        print(f"总共生成了 {len(all_chunks)} 个文本块")
    except Exception as e:
        print(f"保存CSV文件时出错: {str(e)}")

def parse_markdown_with_metadata(markdown: str) -> list[dict]:
    import re
    import json
    
    elements = []

    paragraphs = markdown.split('\n\n')

    metadata_pattern = re.compile(r'<!-- METADATA\n(.*?)\n-->', re.DOTALL)
    
    i = 0
    while i < len(paragraphs):
        paragraph = paragraphs[i]

        metadata_match = metadata_pattern.search(paragraph)
        
        if metadata_match:
            metadata_str = metadata_match.group(1)
            try:
                metadata = json.loads(metadata_str)

                if i + 1 < len(paragraphs):
                    content = paragraphs[i + 1]
                    elements.append({
                        "content": content,
                        "metadata": metadata
                    })
                    i += 2
                else:
                    elements.append({
                        "content": "",
                        "metadata": metadata
                    })
                    i += 1
            except json.JSONDecodeError:
                elements.append({
                    "content": paragraph,
                    "metadata": {}
                })
                i += 1
        else:
            elements.append({
                "content": paragraph,
                "metadata": {}
            })
            i += 1
    
    return elements
    
