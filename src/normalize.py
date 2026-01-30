import re
from typing import Any, List

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
    return [normalize_text(c) for c in cols]
