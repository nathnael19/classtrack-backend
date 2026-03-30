from urllib.parse import quote


def build_content_disposition_attachment(filename: str) -> str:
    """
    RFC5987-ish Content-Disposition value with CRLF/header injection protection.
    Produces: attachment; filename="..."; filename*=UTF-8''...
    """
    # Strip any path components and control chars.
    safe = (filename or "").split("/")[-1].split("\\")[-1]
    safe = safe.replace("\r", "").replace("\n", "").replace("\0", "")
    # Keep it conservative to avoid odd browser parsing.
    safe = "".join(ch for ch in safe if ch.isprintable() and ch not in {"\"", "\r", "\n", "\0"})
    safe = safe[:200] or "download"

    quoted = quote(safe, safe="")
    # filename="..." needs quotes; filename* carries proper encoding.
    return f'attachment; filename="{safe}"; filename*=UTF-8\'\'{quoted}'

