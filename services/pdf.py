"""PDF text extraction using PyMuPDF."""


def extract_pdf_text(pdf_bytes: bytes, max_chars: int = 8000) -> str:
    """Extract text from a PDF byte stream using PyMuPDF.

    Returns up to *max_chars* characters of text.  If the PDF contains
    no extractable text (scanned image), returns an empty string.
    """
    import fitz  # PyMuPDF — lazy import (heavy C extension)

    text_parts: list[str] = []
    total = 0
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            for page_num, page in enumerate(doc, 1):
                page_text = page.get_text()
                if not page_text.strip():
                    continue
                header = f"--- Page {page_num} ---\n"
                chunk = header + page_text
                if total + len(chunk) > max_chars:
                    remaining = max_chars - total
                    if remaining > len(header):
                        text_parts.append(chunk[:remaining])
                    break
                text_parts.append(chunk)
                total += len(chunk)
    except Exception as e:
        print(f"[PDF] Failed to extract text: {e}")
        return ""
    return "\n".join(text_parts)
