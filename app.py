import streamlit as st
import pandas as pd
import yaml

from src.loader import read_any
from src.roster_master import load_roster_master
from src.latest_email import latest_email_by_student
from src.form_submit import count_form_submissions_by_studentno
from src.scoring import build_gradebook
from src.export_excel import export_to_excel_bytes

st.set_page_config(page_title="WEB制作運用｜名簿＋フォーム統合", layout="wide")

st.title("WEB制作運用｜名簿＋フォーム統合 → 採点台帳Excel出力")
st.caption("学生の個人情報を扱うため、公開運用は避け、ローカル/限定環境推奨")

# ---- YAML読み込み（落ちた時に原因を表示）----
try:
    with open("config/scoring.yaml", "r", encoding="utf-8") as f:
        scoring_cfg = yaml.safe_load(f)
except Exception as e:
    st.error("config/scoring.yaml の読み込みに失敗しました。インデント(スペース)・全角記号・```混入を確認してください。")
    st.exception(e)
    st.stop()

total_sessions = int(scoring_cfg["attendance"]["total_sessions"])

# ---- Uploads ----
st.subheader("① 名簿（RosterMaster）")
roster_file = st.file_uploader("名簿をアップロード（.xlsx / .csv）", type=["xlsx", "csv"], key="roster")

st.subheader("② 統合フォーム（FormRaw）")
form_file = st.file_uploader("統合フォームをアップロード（.xlsx / .csv）", type=["xlsx", "csv"], key="form")

if not roster_file or not form_file:
    st.info("名簿とフォームの両方をアップロードしてください。")
    st.stop()

# ---- Read roster ----
st.markdown("### 名簿の読み込み")
if roster_file.name.lower().endswith(".xlsx"):
    roster_df, roster_sheets = read_any(roster_file, sheet_name=None)
    sheet = st.selectbox("名簿Excelのシートを選択", roster_sheets, key="roster_sheet")
    roster_df, _ = read_any(roster_file, sheet_name=sheet)
else:
    roster_df, _ = read_any(roster_file, sheet_name=None)

try:
    roster_master = load_roster_master(roster_df)
except Exception as e:
    st.error("名簿の列名が合っていない可能性があります。必須: class, Timetable, Time, student_no, name")
    st.exception(e)
    st.stop()

st.dataframe(roster_master, use_container_width=True)

# ---- Read form ----
st.markdown("### フォームの読み込み")
if form_file.name.lower().endswith(".xlsx"):
    form_df, form_sheets = read_any(form_file, sheet_name=None)
    f_sheet = st.selectbox("フォームExcelのシートを選択", form_sheets, key="form_sheet")
    form_df, _ = read_any(form_file, sheet_name=f_sheet)
else:
    form_df, _ = read_any(form_file, sheet_name=None)

st.dataframe(form_df.head(10), use_container_width=True)

# ---- Column mapping for form (manual select, safest) ----
st.markdown("### フォーム列の割り当て（手動で選択）")
cols = list(form_df.columns)

col_ts = st.selectbox("タイムスタンプ列", cols, index=cols.index("タイムスタンプ") if "タイムスタンプ" in cols else 0)
col_email = st.selectbox("メール列", cols, index=cols.index("メールアドレス") if "メールアドレス" in cols else 0)

# No列は「No. 記入例) 1」みたいに入っていることが多いので、選択式にして事故回避
default_no_idx = 0
for i, c in enumerate(cols):
    if c.lower().startswith("no."):
        default_no_idx = i
        break
col_no = st.selectbox("student_no（No.）列", cols, index=default_no_idx)

# ---- Latest email by student_no ----
st.markdown("### 最新メール（student_noごと）を抽出して名簿に反映")
email_latest = latest_email_by_student(form_df, col_no, col_email, col_ts)

# ---- Form submit count (student_no × date) ----
st.markdown("### フォーム提出回数（student_no × 日付でユニーク）")
submit_cnt = count_form_submissions_by_studentno(form_df, col_no, col_ts, cap=total_sessions)

# ---- Merge to roster_master ----
roster_enriched = roster_master.merge(email_latest, on="student_no", how="left", suffixes=("", "_new"))
roster_enriched["email"] = roster_enriched["email_new"].fillna(roster_enriched["email"])
roster_enriched = roster_enriched.drop(columns=["email_new"])

roster_enriched = roster_enriched.merge(submit_cnt, on="student_no", how="left")
roster_enriched["form_submit_count"] = roster_enriched["form_submit_count"].fillna(0).astype(int)

st.dataframe(roster_enriched, use_container_width=True)

# ---- GradeBook ----
st.markdown("### GradeBook（採点台帳）生成")
gradebook = build_gradebook(roster_enriched, scoring_cfg)

# 主要8項目の数を変更できるように（サイト制作）
site_total = st.number_input(
    "サイト制作｜チェック項目数（主要項目数）",
    min_value=1, max_value=30,
    value=int(scoring_cfg.get("defaults", {}).get("site_requirements_total", 8)),
    step=1
)
gradebook["site_requirements_total"] = int(site_total)

# 再計算（site_total変えた分だけ簡易再計算）
denom = gradebook["site_requirements_total"].replace(0, 1)
gradebook["site_points_20"] = (gradebook["site_requirements_done"].clip(lower=0) / denom * float(scoring_cfg["learning"]["site"])).round(1)
gradebook["learning_points_70_raw"] = (
    gradebook["report_points_20"]
    + gradebook["paiza_points_10"]
    + gradebook["site_points_20"]
    + gradebook["form_points_10"]
    + gradebook["final_points_10"]
).round(1)
gradebook["learning_points_70"] = (gradebook["learning_points_70_raw"] - gradebook["attitude_penalty"]).clip(lower=0).round(1)
gradebook["total_100"] = (gradebook["attendance_points_30"] + gradebook["learning_points_70"]).round(1)

# 評価更新
boundary = scoring_cfg["grade_boundary"]
def _grade_letter(x: float) -> str:
    if x >= boundary["S"]:
        return "S"
    if x >= boundary["A"]:
        return "A"
    if x >= boundary["B"]:
        return "B"
    if x >= boundary["C"]:
        return "C"
    return "D"
gradebook["grade"] = gradebook["total_100"].apply(lambda x: _grade_letter(float(x)))

gate = float(scoring_cfg["attendance"]["gate_rate"])
gradebook["attendance_gate"] = gradebook["attendance_rate"].apply(lambda r: "OK" if r >= gate else "NG(出席不足)")
gradebook["final_judgement"] = gradebook.apply(
    lambda r: "不可(出席不足)" if r["attendance_rate"] < gate else ("可" if r["total_100"] >= boundary["C"] else "不可"),
    axis=1
)
gradebook["mail_line"] = gradebook.apply(
    lambda r: f"結果：{r['total_100']}点（{r['grade']}） 出席率：{int(round(r['attendance_rate']*100))}% 判定：{r['final_judgement']}",
    axis=1
)

st.dataframe(gradebook, use_container_width=True, height=520)

# ---- Download Excel ----
excel_bytes = export_to_excel_bytes(roster_enriched, gradebook)
st.download_button(
    label="Excelをダウンロード（Roster＋GradeBook）",
    data=excel_bytes,
    file_name="WEB制作運用_採点台帳_自動生成.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
