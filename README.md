# WEB制作運用｜名簿＋フォーム統合 自動採点（Streamlit）

## できること（v1）
- ①名簿（RosterMaster）と ②統合フォーム（FormRaw）をアップロード
- student_no（出席NO）で統合し、未提出者も名簿に残す
- email は「最新タイムスタンプの提出」の email を採用（複数メール対応）
- フォーム提出回数は student_no × 日付でユニーク集計（同日二重送信は1回）
- 採点台帳 GradeBook を生成し、Excel（Roster+GradeBook）をダウンロード

## 名簿（RosterMaster）の必須列
- class
- Timetable
- Time
- student_no
- name

※列名は大文字小文字は問わない（正規化します）

## 起動
```bash
pip install -r requirements.txt
streamlit run app.py
