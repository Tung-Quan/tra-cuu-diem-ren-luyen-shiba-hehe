"""
Vietnamese text processing utilities.
Handles encoding fixes, diacritic removal, and text normalization.
"""
import re
import unicodedata
from typing import Optional, Tuple

from ftfy import fix_text, fix_encoding

# Mojibake detection patterns
_MOJIBAKE_SIGNS = ("Ã", "Â", "Æ°", "Ä'", "áº", "á»", "â€", "Ê", "Ð", "Þ")


def _looks_mojibake(s: str) -> bool:
    """Check if string contains mojibake (encoding errors)."""
    if not s:
        return False
    return any(x in s for x in _MOJIBAKE_SIGNS) or "\ufffd" in s


def _latin1_to_utf8(s: str) -> Optional[str]:
    """Try to fix text by re-encoding as latin-1 -> utf-8."""
    try:
        return s.encode("latin-1", errors="strict").decode("utf-8", errors="strict")
    except Exception:
        return None


def _cp1252_to_utf8(s: str) -> Optional[str]:
    """Try to fix text by re-encoding as cp1252 -> utf-8."""
    try:
        return s.encode("cp1252", errors="strict").decode("utf-8", errors="strict")
    except Exception:
        return None


def fix_vietnamese_text(s: str) -> str:
    """
    Fix Vietnamese text with aggressive encoding repair.
    
    Steps:
    1. ftfy.fix_encoding
    2. latin-1 -> utf-8 if still has mojibake
    3. cp1252 -> utf-8 if still has mojibake
    4. ftfy.fix_text + normalize Unicode to NFC
    
    This is the primary text fixing function.
    """
    if s is None:
        return ""
    s0 = str(s)

    # Step 1: fix_encoding
    try:
        s1 = fix_encoding(s0)
    except Exception:
        s1 = s0

    # Step 2: latin-1 -> utf-8 if needed
    if _looks_mojibake(s1):
        s2 = _latin1_to_utf8(s1) or s1
    else:
        s2 = s1

    # Step 3: cp1252 -> utf-8 if needed
    if _looks_mojibake(s2):
        s3 = _cp1252_to_utf8(s2) or s2
    else:
        s3 = s2

    # Step 4: clean up and normalize
    try:
        s4 = fix_text(s3)
    except Exception:
        s4 = s3

    s4 = s4.replace("\u00A0", " ").replace("\u200b", "")
    s4 = re.sub(r"[ \t]+", " ", s4)
    s4 = re.sub(r"\n{3,}", "\n\n", s4)
    s4 = unicodedata.normalize("NFC", s4)

    return s4.strip()


def fold_vietnamese(s: str) -> str:
    """
    Remove Vietnamese diacritics for fuzzy matching.
    
    Steps:
    - Fix encoding first
    - Replace đ/Đ with d/D
    - NFKD decomposition
    - Remove combining characters
    - Lowercase
    """
    if not isinstance(s, str):
        s = "" if s is None else str(s)
    
    s = fix_vietnamese_text(s)
    s = s.replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.lower()


def normalize_query(q: str) -> Tuple[str, str]:
    """
    Normalize a search query.
    
    Returns:
        (q_fixed, q_folded) - fixed encoding, and folded (no diacritics)
    """
    q_fixed = fix_vietnamese_text(q or "")
    q_folded = fold_vietnamese(q_fixed)
    return q_fixed, q_folded


def decode_http_response(resp) -> str:
    """
    Decode HTTP response bytes to string with proper Vietnamese handling.
    
    Priority:
    1. utf-8-sig (handles BOM)
    2. utf-8
    3. Server-suggested encoding
    4. Fallback with replace
    """
    # Try utf-8-sig first
    try:
        return resp.content.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass

    # Try server-suggested encoding
    enc: Optional[str] = None
    try:
        enc = getattr(resp, "encoding", None)
        if not enc:
            enc = getattr(resp, "apparent_encoding", None)
    except Exception:
        enc = None

    if enc:
        try:
            return resp.content.decode(enc, errors="replace")
        except Exception:
            pass

    # Fallback to requests .text
    try:
        return resp.text
    except Exception:
        return resp.content.decode("utf-8", errors="replace")
