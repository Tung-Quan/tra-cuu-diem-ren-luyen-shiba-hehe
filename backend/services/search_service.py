"""Search service - business logic for searching."""
from typing import Any, Dict, List
import re
import time
from rapidfuzz import fuzz

from backend.config import DATABASE_ROWS
from backend.utils.text_processing import fix_vietnamese_text, fold_vietnamese, normalize_query


def _tokens(q_fold: str) -> List[str]:
    """Tokenize folded query (min length 2)."""
    return [t for t in re.split(r"\s+", q_fold) if len(t) >= 2]


def _all_tokens_in_text(q_fold: str, text_fold: str) -> bool:
    """Check if all query tokens appear in text (word boundary)."""
    toks = _tokens(q_fold)
    return all(re.search(rf"\b{re.escape(tok)}\b", text_fold) for tok in toks)


def _snippet(s: str, q: str, window: int = 60) -> str:
    """Extract snippet around query match."""
    s_fix = fix_vietnamese_text(s)
    q_fix = fix_vietnamese_text(q)
    s_fold = fold_vietnamese(s_fix)
    q_fold = fold_vietnamese(q_fix)
    
    m = re.search(re.escape(q_fold), s_fold, flags=re.IGNORECASE)
    if not m:
        return s_fix[:window * 2]
    
    i = m.start()
    left = max(0, i - window)
    right = min(len(s_fix), i + window)
    return s_fix[left:right]


class SearchService:
    """Service for searching in indexed rows."""
    
    @staticmethod
    def search_rows(
        query: str,
        top_k: int = 20,
        fuzz_threshold: int = 85,
        exact: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search in indexed rows.
        
        Args:
            query: Search query
            top_k: Maximum results to return
            fuzz_threshold: Fuzzy matching threshold (0-100)
            exact: If True, all tokens must appear in text
            
        Returns:
            List of search results sorted by score
        """
        results: List[tuple[int, Dict[str, Any]]] = []
        if not query or not str(query).strip():
            return []
        
        q_fixed, q_fold = normalize_query(query)
        
        for row in DATABASE_ROWS:
            raw = row.get("text") or ""
            text_fixed = fix_vietnamese_text(raw)
            text_fold = fold_vietnamese(text_fixed)
            
            if exact:
                ok = _all_tokens_in_text(q_fold, text_fold)
                score = 100 if ok else 0
            else:
                if q_fixed.lower() in text_fixed.lower() or q_fold in text_fold:
                    score = 100
                else:
                    score = max(
                        fuzz.partial_ratio(q_fixed, text_fixed),
                        fuzz.partial_ratio(q_fold, text_fold)
                    )
            
            if score >= (100 if exact else fuzz_threshold):
                results.append((score, {
                    "sheet": row["sheet"],
                    "row": row["row"],
                    "snippet": _snippet(text_fixed, q_fixed),
                    "snippet_nodau": _snippet(text_fold, q_fold),
                    "links": sorted(set(row.get("links", []))),
                    "score": score
                }))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in results[:top_k]]
    
    @staticmethod
    def search_with_timing(
        query: str,
        top_k: int = 20,
        fuzz_threshold: int = 85,
        exact: bool = False
    ) -> tuple[List[Dict[str, Any]], float]:
        """Search with execution time tracking."""
        start = time.time()
        results = SearchService.search_rows(query, top_k, fuzz_threshold, exact)
        elapsed = time.time() - start
        return results, elapsed
