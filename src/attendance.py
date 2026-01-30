import pandas as pd

def calc_attendance_points(
    absent_full: pd.Series,
    total_sessions: int,
    max_points: int = 30
) -> pd.DataFrame:
    """
    完全欠席数 → 出席率 → 出席点(30)
    """
    absent_full = absent_full.fillna(0).astype(int).clip(lower=0)
    attended = (total_sessions - absent_full).clip(lower=0)
    rate = (attended / total_sessions).fillna(0)

    points = (rate * max_points).round(1)
    return pd.DataFrame({
        "attended": attended,
        "attendance_rate": rate,
        "attendance_points_30": points
    })
