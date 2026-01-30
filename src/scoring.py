import pandas as pd
from .attendance import calc_attendance_points

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

def grade_letter(score: float, boundary: dict) -> str:
    if score >= boundary["S"]:
        return "S"
    if score >= boundary["A"]:
        return "A"
    if score >= boundary["B"]:
        return "B"
    if score >= boundary["C"]:
        return "C"
    return "D"

def build_gradebook(
    roster: pd.DataFrame,
    total_sessions: int,
    scoring_cfg: dict,
    defaults_cfg: dict
) -> pd.DataFrame:
    """
    roster（class/name/email）から、採点台帳（入力欄＋計算欄）を生成。
    ここでは「基本C、事故だけ減点」を想定し、初期値を入れる。
    """
    gb = roster.copy()
    gb.insert(0, "student_id", "")  # 学籍番号は後で

    # 入力欄（先生が埋める）
    gb["total_sessions"] = total_sessions
    gb["absent_full"] = 0

    gb["report_status"] = defaults_cfg.get("report_status", "一部間違い")
    gb["paiza_done"] = 0
    gb["site_requirements_done"] = 0
    gb["site_requirements_total"] = int(defaults_cfg.get("site_requirements_total", 8))
    gb["final_status"] = defaults_cfg.get("final_status", "提出")
    gb["attitude_penalty"] = 0  # 悪い時だけ減点（学習70から引く）

    # フォーム提出数（後で merge で上書き）
    gb["form_submit_count"] = 0

    # --- 出席（30） ---
    att = calc_attendance_points(
        absent_full=gb["absent_full"],
        total_sessions=total_sessions,
        max_points=scoring_cfg["attendance"]["max_points"]
    )
    gb = pd.concat([gb, att], axis=1)

    # --- 学習（70） ---
    # Report(20)
    gb["report_points_20"] = gb["report_status"].map(REPORT_MAP).fillna(0).astype(float)

    # paiza(10) 最大27想定
    gb["paiza_points_10"] = (gb["paiza_done"].clip(upper=27) / 27 * scoring_cfg["learning"]["paiza"]).round(1)

    # site(20)
    denom = gb["site_requirements_total"].replace(0, 1)
    gb["site_points_20"] = (gb["site_requirements_done"].clip(lower=0) / denom * scoring_cfg["learning"]["site"]).round(1)

    # form(10)
    gb["form_points_10"] = (gb["form_submit_count"].clip(upper=total_sessions) / total_sessions * scoring_cfg["learning"]["form"]).round(1)

    # final(10)
    gb["final_points_10"] = gb["final_status"].map(FINAL_MAP).fillna(0).astype(float)

    gb["learning_points_70_raw"] = (
        gb["report_points_20"]
        + gb["paiza_points_10"]
        + gb["site_points_20"]
        + gb["form_points_10"]
        + gb["final_points_10"]
    ).round(1)

    gb["learning_points_70"] = (gb["learning_points_70_raw"] - gb["attitude_penalty"]).clip(lower=0).round(1)

    # --- 総合（100） ---
    gb["total_100"] = (gb["attendance_points_30"] + gb["learning_points_70"]).round(1)

    boundary = scoring_cfg["grade_boundary"]
    gb["grade"] = gb["total_100"].apply(lambda x: grade_letter(float(x), boundary))

    gate = scoring_cfg["attendance"]["gate_rate"]
    gb["attendance_gate"] = gb["attendance_rate"].apply(lambda r: "OK" if r >= gate else "NG(出席不足)")
    gb["final_judgement"] = gb.apply(
        lambda r: "不可(出席不足)" if r["attendance_rate"] < gate else ("可" if r["total_100"] >= boundary["C"] else "不可"),
        axis=1
    )

    gb["mail_line"] = gb.apply(
        lambda r: f"結果：{r['total_100']}点（{r['grade']}） 出席率：{int(round(r['attendance_rate']*100))}% 判定：{r['final_judgement']}",
        axis=1
    )

    return gb

def recompute_points(gb: pd.DataFrame, scoring_cfg: dict) -> pd.DataFrame:
    """
    入力欄（欠席数、report_status、paiza_done…）を編集後に再計算する用。
    """
    total_sessions = int(gb["total_sessions"].iloc[0])
    att = calc_attendance_points(gb["absent_full"], total_sessions, scoring_cfg["attendance"]["max_points"])
    for c in att.columns:
        gb[c] = att[c]

    # Report
    gb["report_points_20"] = gb["report_status"].map(REPORT_MAP).fillna(0).astype(float)

    # paiza
    gb["paiza_points_10"] = (gb["paiza_done"].clip(upper=27) / 27 * scoring_cfg["learning"]["paiza"]).round(1)

    # site
    denom = gb["site_requirements_total"].replace(0, 1)
    gb["site_points_20"] = (gb["site_requirements_done"].clip(lower=0) / denom * scoring_cfg["learning"]["site"]).round(1)

    # form
    gb["form_points_10"] = (gb["form_submit_count"].clip(upper=total_sessions) / total_sessions * scoring_cfg["learning"]["form"]).round(1)

    # final
    gb["final_points_10"] = gb["final_status"].map(FINAL_MAP).fillna(0).astype(float)

    gb["learning_points_70_raw"] = (
        gb["report_points_20"]
        + gb["paiza_points_10"]
        + gb["site_points_20"]
        + gb["form_points_10"]
        + gb["final_points_10"]
    ).round(1)

    gb["learning_points_70"] = (gb["learning_points_70_raw"] - gb["attitude_penalty"]).clip(lower=0).round(1)

    gb["total_100"] = (gb["attendance_points_30"] + gb["learning_points_70"]).round(1)

    boundary = scoring_cfg["grade_boundary"]
    gb["grade"] = gb["total_100"].apply(lambda x: grade_letter(float(x), boundary))

    gate = scoring_cfg["attendance"]["gate_rate"]
    gb["attendance_gate"] = gb["attendance_rate"].apply(lambda r: "OK" if r >= gate else "NG(出席不足)")
    gb["final_judgement"] = gb.apply(
        lambda r: "不可(出席不足)" if r["attendance_rate"] < gate else ("可" if r["total_100"] >= boundary["C"] else "不可"),
        axis=1
    )

    gb["mail_line"] = gb.apply(
        lambda r: f"結果：{r['total_100']}点（{r['grade']}） 出席率：{int(round(r['attendance_rate']*100))}% 判定：{r['final_judgement']}",
        axis=1
    )

    return gb
