import pandas as pd
from .normalize import normalize_text

def build_roster(df: pd.DataFrame, col_class: str, col_name: str, col_email: str) -> pd.DataFrame:
    tmp = df[[col_class, col_name, col_email]].copy()
    tmp.columns = ["class", "name", "email"]

    tmp["class"] = tmp["class"].map(normalize_text)
    tmp["name"]  = tmp["name"].map(normalize_text)
    tmp["email"] = tmp["email"].map(normalize_text).str.lower()

    # email空は除外
    tmp = tmp[tmp["email"] != ""]

    # email基準で名簿化（表記ゆれに強い）
    tmp = tmp.drop_duplicates(subset=["email"], keep="first")
    tmp = tmp.sort_values(["class", "name", "email"]).reset_index(drop=True)
    return tmp
