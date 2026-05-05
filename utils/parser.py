import fitz  # PyMuPDF


def read_pdf(file_path: str) -> str:
    """Extract text content from a PDF file."""
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text() + " "
    doc.close()
    return text.strip()


def read_markdown(file_path: str) -> str:
    """Read content from a Markdown file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def read_text(file_path: str) -> str:
    """Read content from a plain text file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def read_file(file_path: str) -> str:
    """Read file content based on file extension."""
    extension = file_path.lower().split(".")[-1]
    
    if extension == "pdf":
        return read_pdf(file_path)
    elif extension in ["md", "markdown"]:
        return read_markdown(file_path)
    elif extension == "txt":
        return read_text(file_path)
    else:
        raise ValueError(f"Unsupported file type: {extension}")