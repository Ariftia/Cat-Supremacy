"""Shared helper utilities for bot commands.

Keeps attachment-parsing and response-splitting logic in one place
so command handlers stay concise.
"""

from __future__ import annotations

from services.pdf import extract_pdf_text

# ── File extension sets ──────────────────────────────────

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")

TEXT_EXTS = (
    ".txt", ".md", ".csv", ".json", ".xml", ".py", ".js", ".ts",
    ".html", ".css", ".log", ".yaml", ".yml", ".toml", ".ini",
    ".cfg", ".sh", ".bat", ".sql", ".java", ".c", ".cpp", ".h",
    ".rs", ".go", ".rb", ".php", ".env", ".conf",
)


# ── Attachment parsing ───────────────────────────────────

async def parse_attachments(
    attachments,
    *,
    question_ref: list[str] | None = None,
) -> list[dict]:
    """Parse Discord message attachments into a list of dicts for the AI.

    Each dict has keys:
    - ``type``: ``"image"`` or ``"text"``
    - ``url``: image URL (images only)
    - ``filename``: original filename
    - ``content``: extracted text (text / PDF only)

    If *question_ref* is provided (a single-element list holding the
    question string), un-readable files will be noted there.
    """
    result: list[dict] = []

    for att in attachments:
        fname = att.filename.lower()

        # Images
        if any(fname.endswith(ext) for ext in IMAGE_EXTS) or (
            att.content_type and att.content_type.startswith("image/")
        ):
            result.append({"type": "image", "url": att.url, "filename": att.filename})
            print(f"[ATTACH] Image: {att.filename}")

        # PDFs
        elif fname.endswith(".pdf") or (att.content_type and att.content_type == "application/pdf"):
            try:
                raw = await att.read()
                pdf_text = extract_pdf_text(raw)
                if pdf_text:
                    result.append({"type": "text", "filename": att.filename, "content": pdf_text})
                    print(f"[ATTACH] PDF read: {att.filename} ({len(pdf_text)} chars)")
                elif question_ref is not None:
                    question_ref[0] += f"\n[User attached a PDF: {att.filename} — scanned image, no extractable text]"
                    print(f"[ATTACH] PDF has no extractable text: {att.filename}")
            except Exception as e:
                if question_ref is not None:
                    question_ref[0] += f"\n[User attached a PDF: {att.filename} — failed to read: {e}]"
                print(f"[ATTACH] Failed to read PDF {att.filename}: {e}")

        # Text-based files
        elif any(fname.endswith(ext) for ext in TEXT_EXTS) or (
            att.content_type and att.content_type.startswith("text/")
        ):
            try:
                raw = await att.read()
                text_content = raw.decode("utf-8", errors="replace")[:8000]
                result.append({"type": "text", "filename": att.filename, "content": text_content})
                print(f"[ATTACH] Text file read: {att.filename} ({len(text_content)} chars)")
            except Exception as e:
                print(f"[ATTACH] Failed to read {att.filename}: {e}")

        # Unknown
        else:
            if question_ref is not None:
                question_ref[0] += (
                    f"\n[User attached a file: {att.filename} "
                    f"({att.content_type or 'unknown type'}) — cannot be read directly]"
                )
            print(f"[ATTACH] Unsupported attachment skipped: {att.filename} ({att.content_type})")

    return result


# ── Response splitting ───────────────────────────────────

async def send_long_response(ctx, text: str) -> None:
    """Send a potentially long response, splitting at Discord's 2 000-char limit."""
    while len(text) > 2000:
        split_at = text.rfind("\n", 0, 2000)
        if split_at == -1:
            split_at = 2000
        await ctx.send(text[:split_at])
        text = text[split_at:].lstrip()
    if text:
        await ctx.send(text)
