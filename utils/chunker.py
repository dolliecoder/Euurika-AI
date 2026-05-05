from llama_index.core.node_parser import SentenceSplitter


def chunk_document(text: str, chunk_size: int = 256, overlap: int = 50) -> list[str]:
    """
    Chunk a document into smaller pieces using LlamaIndex's SentenceSplitter.
    
    Args:
        text: The full document text to chunk
        chunk_size: Number of tokens per chunk (default: 256)
        overlap: Number of overlapping tokens between chunks (default: 50)
    
    Returns:
        List of text chunks (only text, no IDs or metadata)
    """
    splitter = SentenceSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        # Return only the text content
        include_metadata=False,
        include_prev_next_rel=False,
    )
    
    nodes = splitter.split_text(text)
    
    # Return only the text content of each chunk
    return [node.text for node in nodes]