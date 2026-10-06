---
name: check-posted
description: 自動投稿が実際に投稿されたかを確認する手順。「投稿された?」「今日の投稿は大丈夫?」と聞かれたときに使う。
---

# 投稿されたか確認する

「投稿された」と言う前に、シートのフラグと実行結果の両方を見る。確認できていないことは、確認できていないと言う。読み取りだけなので安全。

1. GitHub Actionsの実行履歴(成功・失敗):
   ```bash
   curl -s "https://api.github.com/repos/Sorami-0420/instagram-auto-post/actions/runs?per_page=5"
   ```
   ログの中身は認証が必要で取れない。失敗時は、そらみさんに画面を見せてもらう
2. スプレッドシートの内容: ローカルの `service-account.json` と `.env` を使い、`scripts/sheets_client.py`(フィード)/`scripts/story_sheets_client.py`(ストーリー)で読み取る。値(キー・トークン)は表示しない
3. 公開された写真が取得できるか(200が返れば取得できる):
   ```bash
   curl -s -o /dev/null -w "%{http_code}" https://raw.githubusercontent.com/Sorami-0420/instagram-auto-post/main/posts/<ファイル名>
   ```
4. Instagramのプロフィールも、そらみさんに見てもらう

## 投稿されていないとき
- 自動実行は予定時刻の「ちょうど」には投稿されず、次の実行で処理される。毎時0分は遅れることがある
- 失敗しているときは、スキル `handle-failure` に進む
