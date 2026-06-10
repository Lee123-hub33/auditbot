# app/utils/document_parser.py
"""
Extracts plain text from uploaded documents.
Supports: PDF (via pdfplumber), TXT.
"""

import io
import structlog

log = structlog.get_logger()


def extract_text(content: bytes, mime_type: str, filename: str) -> str:
    """
    Extract all readable text from a document's raw bytes.
    Returns a plain text string.
    """
    if mime_type == "application/pdf":
        return _extract_pdf(content, filename)
    elif mime_type == "text/plain":
        return _extract_txt(content, filename)
    else:
        log.warning(
            "unsupported_mime_for_extraction", mime=mime_type, filename=filename
        )
        return ""


def _extract_pdf(content: bytes, filename: str) -> str:
    try:
        import pdfplumber

        text_parts = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"[Page {i+1}]\n{page_text}")
        full_text = "\n\n".join(text_parts)
        log.info(
            "pdf_extracted",
            filename=filename,
            pages=len(text_parts),
            chars=len(full_text),
        )
        return full_text
    except Exception as e:
        log.error("pdf_extraction_failed", filename=filename, error=str(e))
        return ""


def _extract_txt(content: bytes, filename: str) -> str:
    try:
        # Try UTF-8 first, fall back to latin-1
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
        log.info("txt_extracted", filename=filename, chars=len(text))
        return text
    except Exception as e:
        log.error("txt_extraction_failed", filename=filename, error=str(e))
        return ""
