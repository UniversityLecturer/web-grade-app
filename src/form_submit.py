import pandas as pd
from .normalize import normalize_text

def count_form_submissions(
    df: pd.DataFrame,
    col_email: str,
    col_timestamp: str,
    cap: int = 15
) -> pd.DataFrame:
    """
    フォーム提出数：
    - email × date でユニーク（同日複数送信は1回）
    - cap（上限）をかける
    """
    base = df[[col_email, col_timestamp]].copy()
    base[col_email] = base[col_email].map(normalize_text).str.lower()
    base[col_timestamp] = pd.to_datetime(base[col_timestamp], errors="coerce")

    base = base[base[col_email] != ""]
    base = base.dropna(subset=[col_timestamp])

    base["date"] = base[col_timestamp].dt.date

    # 同日重複は1回扱い
    base = base.drop_duplicates(subset=[col_email, "date"])

    out = (
        base.groupby(col_email, as_index=False)
            .size()
            .rename(columns={"size": "form_submit_count"})
    )
    out["form_submit_count"] = out["form_submit_count"].clip(upper=cap).astype(int)
    out = out.rename(columns={col_email: "email"})
    return out
