# WEB制作運用｜自動採点アプリ（Streamlit）

## できること（v1）
- 統合フォーム（複数回分を1枚にまとめたExcel/CSV）をアップロード
- class / name / email の名簿（Roster）を自動生成（email基準で重複排除）
- フォーム提出回数（同日複数送信は1回）を自動集計
- GradeBook（採点台帳）を生成（出席30＋学習70、出席率75%未満は不可）
- Excel（Roster + GradeBook）をダウンロード

## 起動
```bash
pip install -r requirements.txt
streamlit run app.py
