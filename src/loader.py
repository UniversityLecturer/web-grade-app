import pandas as pd
from typing import Tuple, List, Optional
from .normalize import normalize_columns

def load_file(file) -> Tuple[pd.DataFrame, List[str]]:
    """
    Streamlitのuploaded_fileからDataFrameを返す。
    xlsxの場合は、シート一覧も返す（選択はapp.py側）。
    """
    name = getattr(file, "name", "").lower()

    if name.endswith(".csv"):
        df = pd.read_csv(file)
        df.columns = normalize_columns(list(df.columns))
        return df, []

    if name.endswith(".xlsx") or name.endswith(".xls"):
        # シート一覧だけ先に
        xls = pd.ExcelFile(file)
        return pd.DataFrame(), xls.sheet_names

    raise ValueError("Unsupported file type. Please upload .xlsx or .csv")

def load_excel_sheet(file, sheet_name: str) -> pd.DataFrame:
    df = pd.read_excel(file, sheet_name=sheet_name)
    df.columns = normalize_columns(list(df.columns))
    return df
