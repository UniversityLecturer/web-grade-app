import re
from typing import Any, Dict, List

def normalize_text(x: Any) -> str:
    """改行をスペース化し、余白を1つに整える。"""
    if x is None:
        return ""
    s = str(x)
    s = s.replace("\r", " ").replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def normalize_columns(cols: List[str]) -> List[str]:
    """列名の改行・余白を正規化。"""
    out = []
    for c in cols:
        c2 = normalize_text(c)
        out.append(c2)
    return out

def find_column_by_hint(df_columns: List[str], hint: str) -> str | None:
    """
    hintに部分一致する列名を探す（大小無視）。
    例：hint='Class' が 'Class 記入例）2-1' にヒット
    """
    h = (hint or "").strip().lower()
    if not h:
        return None
    for c in df_columns:
        if h in c.lower():
            return c
    return None

def resolve_columns(df_columns: List[str], config: Dict[str, Any]) -> Dict[str, str]:
    """
    columns.yamlのヒントから、実データ列名へ解決する。
    """
    resolved = {}

    for key in ["timestamp", "email", "class", "name"]:
        hint = config.get(key, "")
        resolved[key] = find_column_by_hint(df_columns, hint) or ""

    quiz_hints = config.get("quiz_cols", []) or []
    resolved_quiz = []
    for qh in quiz_hints:
        col = find_column_by_hint(df_columns, str(qh))
        if col:
            resolved_quiz.append(col)
    resolved["quiz_cols"] = resolved_quiz
    return resolved
