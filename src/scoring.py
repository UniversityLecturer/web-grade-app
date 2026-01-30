import pandas as pd

REPORT_MAP = {
    "完全完成": 20,
    "一部間違い": 15,
    "データ間違い": 10,
    "未記入": 5,
    "未提出": 0,
}

FINAL_MAP = {
    "未提出": 0,
    "提出": 5,
    "良い": 10,
}

def _grade_letter(score: float, boundary: dict) -> str:
    if score >= boundary["S"]:
        return "S"
    if score >= boundary["A"]:
        return "A"
    if score >= boundary["B"]:
        return "B"
    if score >= boundary["C"]:
        return "C"
    return "D"

def build_gradebook(roster_master: pd.DataFrame, scoring_cfg: dict) -> pd.DataFrame:
    """
    roster_master（全員分）から GradeBook を作る（入力欄＋計算欄）。
    """
    total_sessions = int(scoring_cfg["attendance"]["total_sessions"])
    max_att_points = float(scoring_cfg["attendance"]["max_points"])
    gate_rate = float(scoring_cfg["attendance"]["gate_rate"])

    learning_cfg = scoring_cfg["learning"]
    boundary = scoring_cfg["grade_boundary"]
    defaults = scoring_cfg.get("defaults", {})

    gb = roster_master.copy()

    # ---- 入力欄（先生が埋める）----
    gb["absent_full"] = 0                         # 完全欠席数（OCRなど）
    gb["report_status"] = defaults.get("report_status", "一部間違い")
    gb["paiza_done"] = 0                          # 0〜27
    gb["site_requirements_done"] = 0              # 0〜項目数
    gb["site_requirements_total"] = int(defaults.get("site_requirements_total", 8))
    gb["final_status"] = defaults.get("final_status", "提出")
    gb["attitude_penalty"] = 0                    # 悪いときだけ減点（学習70から引く）
    gb["form_submit_count"] = gb.get("form_submit_count", 0).fillna(0).astype(int)

    # ---- 出席（30）----
    gb["attended"] = (total_sessions - gb["absent_full"].astype(int)).clip(lower=0)
    gb["attendance_rate"] = (gb["attended"] / total_sessions).fillna(0)
    gb["attendance_points_30"] = (gb["attendance_rate"] * max_att_points).round(1)

    # ---- 学習（70）----
    gb["report_points_20"] = gb["report_status"].map(REPORT_MAP).fillna(0).astype(float)

    gb["paiza_points_10"] = (gb["paiza_done"].clip(upper=27) / 27 * float(learning_cfg["paiza"])).round(1)

    denom = gb["site_requirements_total"].replace(0, 1)
    gb["site_points_20"] = (gb["site_requirements_done"].clip(lower=0) / denom * float(learning_cfg["site"])).round(1)

    gb["form_points_10"] = (gb["form_submit_count"].clip(upper=total_sessions) / total_sessions * float(learning_cfg["form"])).round(1)

    gb["final_points_10"] = gb["final_status"].map(FINAL_MAP).fillna(0).astype(float)

    gb["learning_points_70_raw"] = (
        gb["report_points_20"]
        + gb["paiza_points_10"]
        + gb["site_points_20"]
        + gb["form_points_10"]
        + gb["final_points_10"]
    ).round(1)

    gb["learning_points_70"] = (gb["learning_points_70_raw"] - gb["attitude_penalty"]).clip(lower=0).round(1)

    # ---- 総合（100）----
    gb["total_100"] = (gb["attendance_points_30"] + gb["learning_points_70"]).round(1)
    gb["grade"] = gb["total_100"].apply(lambda x: _grade_letter(float(x), boundary))

    gb["attendance_gate"] = gb["attendance_rate"].apply(lambda r: "OK" if r >= gate_rate else "NG(出席不足)")
    gb["final_judgement"] = gb.apply(
        lambda r: "不可(出席不足)" if r["attendance_rate"] < gate_rate else ("可" if r["total_100"] >= boundary["C"] else "不可"),
        axis=1
    )

    gb["mail_line"] = gb.apply(
        lambda r: f"結果：{r['total_100']}点（{r['grade']}） 出席率：{int(round(r['attendance_rate']*100))}% 判定：{r['final_judgement']}",
        axis=1
    )

    return gb
