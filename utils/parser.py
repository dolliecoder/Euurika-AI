import asyncio
import fitz  # PyMuPDF
import aiofiles

# MIME type to extension mapping
MIME_TYPES = {
    "application/pdf": "pdf",
    "text/markdown": "md",
    "text/x-markdown": "md",
    "text/plain": "txt",
}


async def read_pdf(file_path: str) -> str:
    """Extract text content from a PDF file asynchronously."""
    def _read_sync():
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text() + " "
        doc.close()
        return text.strip()
    return await asyncio.to_thread(_read_sync)


async def read_markdown(file_path: str) -> str:
    """Read content from a Markdown file asynchronously."""
    async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
        content = await f.read()
        return content.strip()


async def read_text(file_path: str) -> str:
    """Read content from a plain text file asynchronously."""
    async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
        content = await f.read()
        return content.strip()


async def read_file(file_path: str, mime_type: str = None) -> str:
    """
    Read file content based on MIME type asynchronously.
    
    Args:
        file_path: Path to the file
        mime_type: MIME type of the file (optional, derived from extension if not provided)
    """
    if mime_type:
        extension = MIME_TYPES.get(mime_type)
        if extension is None:
            raise ValueError(f"Unsupported MIME type: {mime_type}")
    else:
        extension = file_path.lower().split(".")[-1]
    
    if extension == "pdf":
        return await read_pdf(file_path)
    elif extension in ["md", "markdown"]:
        return await read_markdown(file_path)
    elif extension == "txt":
        return await read_text(file_path)
    else:
        raise ValueError(f"Unsupported file type: {extension}")