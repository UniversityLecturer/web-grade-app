import streamlit as st
import pandas as pd
import yaml

from src.loader import load_file, load_excel_sheet
from src.normalize import resolve_columns
from src.roster import build_roster
from src.form_submit import count_form_submissions
from src.scoring import build_gradebook, recompute_points
from src.export_excel import export_to_excel_bytes

st.set_page_config(page_title="WEB制作運用｜自動採点", layout="wide")

st.title("WEB制作運用｜名簿整備 → 採点台帳（Excel）出力")
st.caption("統合フォーム（複数回分）から、Roster（名簿）と GradeBook（採点台帳）を自動生成します。")

# ---- config load ----
with open("config/scoring.yaml", "r", encoding="utf-8") as f:
    scoring_cfg = yaml.safe_load(f)

with open("config/columns.yaml", "r", encoding="utf-8") as f:
    columns_cfg = yaml.safe_load(f)

defaults_cfg = scoring_cfg.get("defaults", {})
total_sessions = int(scoring_cfg["attendance"]["total_sessions"])

# ---- upload ----
uploaded = st.file_uploader("統合フォームをアップロード（.xlsx / .csv）", type=["xlsx", "csv"])

if not uploaded:
    st.info("まず統合フォームをアップロードしてください。")
    st.stop()

# ---- read ----
df, sheet_names = load_file(uploaded)

if sheet_names:
    sheet = st.selectbox("Excelのシートを選択", sheet_names)
    df = load_excel_sheet(uploaded, sheet)

st.write("読み込みデータ（先頭10行）")
st.dataframe(df.head(10), use_container_width=True)

# ---- resolve columns ----
resolved = resolve_columns(list(df.columns), columns_cfg)

st.subheader("列の割り当て（自動推定 → 必要なら手動で修正）")

cols = list(df.columns)
col_timestamp = st.selectbox("タイムスタンプ列", cols, index=cols.index(resolved["timestamp"]) if resolved["timestamp"] in cols else 0)
col_email     = st.selectbox("メールアドレス列", cols, index=cols.index(resolved["email"]) if resolved["email"] in cols else 0)
col_class     = st.selectbox("Class列", cols, index=cols.index(resolved["class"]) if resolved["class"] in cols else 0)
col_name      = st.selectbox("Name列", cols, index=cols.index(resolved["name"]) if resolved["name"] in cols else 0)

# ---- roster ----
roster = build_roster(df, col_class, col_name, col_email)
st.subheader("Roster（名簿：email基準で重複排除）")
st.dataframe(roster, use_container_width=True)

# ---- form submit count ----
st.subheader("フォーム提出数（同日複数送信は1回扱い）")
submit_counts = count_form_submissions(df, col_email=col_email, col_timestamp=col_timestamp, cap=total_sessions)
st.dataframe(submit_counts, use_container_width=True)

# ---- gradebook ----
gradebook = build_gradebook(
    roster=roster,
    total_sessions=total_sessions,
    scoring_cfg=scoring_cfg,
    defaults_cfg=defaults_cfg
)

# merge submit count by email
gradebook = gradebook.merge(submit_counts, on="email", how="left", suffixes=("", "_fromlog"))
gradebook["form_submit_count"] = gradebook["form_submit_count_fromlog"].fillna(0).astype(int)
gradebook = gradebook.drop(columns=["form_submit_count_fromlog"])

# recompute because form_submit_count updated
gradebook = recompute_points(gradebook, scoring_cfg)

# allow adjusting site total quickly
st.subheader("GradeBook（採点台帳：入力して使う）")
site_total = st.number_input(
    "サイト制作｜チェック項目数（主要項目数）",
    min_value=1, max_value=30,
    value=int(defaults_cfg.get("site_requirements_total", 8)),
    step=1
)
gradebook["site_requirements_total"] = int(site_total)
gradebook = recompute_points(gradebook, scoring_cfg)

st.dataframe(gradebook, use_container_width=True, height=520)

# ---- download excel ----
excel_bytes = export_to_excel_bytes(roster, gradebook)
st.download_button(
    label="Excelをダウンロード（Roster＋GradeBook）",
    data=excel_bytes,
    file_name="WEB制作運用_採点台帳_自動生成.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.divider()
st.caption("※次の拡張：OCR欠席数CSVをアップロード→email or 学籍番号でJOIN、paiza集計CSVのJOIN、サイト要件チェックの入力UIなど。")
