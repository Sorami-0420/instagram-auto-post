# セットアップ手順書

この順番で進めてください。それぞれ完了したら次に進みます。

- [ ] STEP 0: 全体の流れを理解する
- [ ] STEP 1: GitHubリポジトリを作る
- [ ] STEP 2: Googleスプレッドシートを作る
- [ ] STEP 3: Google Cloud サービスアカウントを作る(スプレッドシート連携用)
- [ ] STEP 4: Instagram Graph APIを設定する(Facebookアプリ・アクセストークン)
- [ ] STEP 5: Claude APIキーを取得する
- [ ] STEP 6: GitHub Secretsに登録する
- [ ] STEP 7: テストモードで動作確認する
- [ ] STEP 8: 本番モードに切り替える
- [ ] STEP 9(任意): 商品タグ付けを設定する
- [ ] STEP 10(任意): ストーリーズ自動投稿を設定する

---

## STEP 1: GitHubリポジトリを作る

1. https://github.com/new を開く
2. リポジトリ名を決める(例: `instagram-auto-post`)
3. **Public(公開)** を選ぶ
   - 理由: Instagram Graph APIが画像を取得するとき、`raw.githubusercontent.com` 経由の
     公開URLでアクセスする必要があるためです。APIキーやトークンはコードに書かず、
     すべてGitHub Secrets(暗号化されて非公開)で管理するので、公開リポジトリでも
     秘密情報が漏れることはありません。
4. 「Create repository」を押す
5. このフォルダの中身をpushする(私からコマンドを提示するので、実行してよいか確認してから進めます)

## STEP 2: Googleスプレッドシートを作る

1. https://sheets.google.com で新しいスプレッドシートを作成
2. シート(タブ)名を `投稿管理` にする(または好きな名前にして、あとでSecretsの
   `SHEET_NAME` に登録)
3. 1行目に、[README.md](../README.md) の「スプレッドシートの列構成」の表にある
   列名をそのまま入力する:
   `投稿日 / 投稿時刻 / 投稿日時 / 画像ファイル名 / 商品名 / 使用石 / 内包物 / BASE商品URL / 商品タグID / 投稿済みフラグ / 投稿日時(実績) / 結果メモ`
   (「投稿日時」は旧形式との互換用の列です。新規に使う場合は「投稿日」「投稿時刻」の
   2列に日付・時刻を分けて入力してください)
4. 2行目からテスト用のデータを1〜2件入れてみる(投稿日時は過去の日時にすると、
   テスト実行時にすぐ「未処理」として検出されます)
5. URLの `https://docs.google.com/spreadsheets/d/【この部分】/edit` の
   【この部分】が スプレッドシートID です。あとで使うのでメモしておいてください。

## STEP 3: Google Cloud サービスアカウントを作る

1. https://console.cloud.google.com にアクセスし、新しいプロジェクトを作成(名前は任意)
2. 左メニュー「APIとサービス」→「ライブラリ」から
   **Google Sheets API** を検索して「有効にする」
3. 「APIとサービス」→「認証情報」→「認証情報を作成」→「サービスアカウント」
4. 名前を適当につけて作成(ロールの割り当てはスキップしてOK)
5. 作成したサービスアカウントの詳細画面 →「キー」タブ →「鍵を追加」→
   「新しい鍵を作成」→ JSON を選択 → ダウンロードされる
   このJSONファイルの中身をあとでSecretsに登録します。**他人に渡さないでください。**
6. JSONファイルの中の `client_email`(例: `xxx@xxx.iam.gserviceaccount.com`)をコピー
7. STEP 2で作ったスプレッドシートを開き、右上の「共有」から、その `client_email` を
   **編集者** 権限で共有する(これをしないとスクリプトから読み書きできません)

## STEP 4: Instagram Graph APIを設定する

これが一番手順が多いパートです。前提として、InstagramアカウントがInstagram
「ビジネスアカウント」または「クリエイターアカウント」になっていて、
Facebookページと連携している必要があります。

1. Instagramアプリ側の設定 →「アカウントの種類とツール」で
   ビジネス/クリエイターアカウントになっているか確認(なっていなければ切り替える)
2. https://www.facebook.com でFacebookページを作成(まだなければ)し、
   InstagramアカウントをそのページにInstagram側の設定から連携する
3. https://developers.facebook.com/apps にアクセスし「アプリを作成」
   - アプリタイプは「ビジネス」を選択
4. 作成したアプリのダッシュボードで「製品を追加」→ **Instagram** を追加
5. 左メニューの「Instagram」→「APIセットアップ」などの案内に従い、
   連携したFacebookページ・Instagramアカウントを選択する
6. アクセストークンを取得する
   - 開発中は「Graph API Explorer」(https://developers.facebook.com/tools/explorer/)
     で自分のアプリを選び、権限に `instagram_basic` `instagram_content_publish`
     `pages_show_list` `pages_read_engagement` を追加してトークンを生成できます
   - このままだと有効期限が短い(1〜2時間)ので、**長期(60日)アクセストークン**に交換します。
     以下のURLの `{app-id}` `{app-secret}` `{short-lived-token}` を置き換えてブラウザでアクセス:
     ```
     https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id={app-id}&client_secret={app-secret}&fb_exchange_token={short-lived-token}
     ```
   - 60日ごとに再取得が必要です(自動更新はこの仕組みには含めていません。期限が近くなったら
     同じ手順で再取得し、Secretsを更新してください)
7. Instagram Business Account ID (`IG_USER_ID`) を確認する
   - Graph API Explorerで `GET /me/accounts` → 出てきたページIDで
     `GET /{page-id}?fields=instagram_business_account` を実行すると
     `instagram_business_account.id` が取得できます。これが `IG_USER_ID` です

## STEP 5: Claude APIキーを取得する

1. https://console.anthropic.com にアクセスしてサインアップ/ログイン
2. 「API Keys」から新しいキーを作成
3. 表示されたキー(`sk-ant-...`)をコピーしておく(再表示できないので必ず保存)

## STEP 6: GitHub Secretsに登録する

作成したリポジトリの GitHub ページ →「Settings」→「Secrets and variables」→
「Actions」→「New repository secret」で、以下をひとつずつ登録します。

| Secret名 | 値 |
|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | STEP 3でダウンロードしたJSONファイルの中身をそのまま貼り付け |
| `SPREADSHEET_ID` | STEP 2でメモしたスプレッドシートID |
| `SHEET_NAME` | シート(タブ)名。省略した場合は `投稿管理` |
| `ANTHROPIC_API_KEY` | STEP 5で取得したキー |
| `IG_USER_ID` | STEP 4で取得したInstagramビジネスアカウントID |
| `IG_ACCESS_TOKEN` | STEP 4で取得した長期アクセストークン |

「Secrets and variables」→「Actions」→「Variables」タブでは以下を登録します
(こちらは非公開ではないので、投稿の公開/非公開切り替えフラグのみ入れます)。

| Variable名 | 値 |
|---|---|
| `TEST_MODE` | 最初は `true`。本番投稿を始めるときに `false` に変更する |

## STEP 7: テストモードで動作確認する

1. `posts/` フォルダにテスト用画像を1枚追加してpush
2. スプレッドシートに、その画像ファイル名を使った行を1つ追加(投稿日時は過去にする)
3. GitHubリポジトリの「Actions」タブ →「Instagram Auto Post」→
   「Run workflow」→ `test_mode` を `true` のまま実行
4. 実行ログと、スプレッドシートの「結果メモ」列に生成されたキャプションが
   表示されることを確認する(Instagramには投稿されません)
5. 文体やハッシュタグの雰囲気を見て、必要なら
   [scripts/caption_generator.py](../scripts/caption_generator.py) の
   `SYSTEM_PROMPT` を調整する

## STEP 8: 本番モードに切り替える

1. テスト結果に問題がなければ、リポジトリの Variables で `TEST_MODE` を `false` に変更
2. スプレッドシートのテスト行を削除するか、投稿済みフラグを手動で埋めて無視する
3. 本番用の行を登録していく
4. 以降は1日4回(10:00 / 13:00 / 18:00 / 20:00 JST)、GitHub Actionsが自動でチェック・投稿します
   (手動で今すぐ試したいときは「Run workflow」→ `test_mode` を `false` で実行)

### 運用メモ

- 投稿に失敗した行は「投稿済みフラグ」が `エラー` になり、自動では再試行されません。
  「結果メモ」列で原因を確認し、直せたらフラグを空欄に戻すと次回実行時に再処理されます。
- アクセストークンは60日で切れます。切れるとエラーになるので、期限前にSTEP 4-6を
  再取得してSecretsを更新してください。

## STEP 9(任意): 商品タグ付けを設定する

投稿する画像に、Instagramの商品タグ(タップすると商品ページに飛べるマーカー)を
自動で付けたい場合の設定です。すでにInstagramアプリから手動で商品タグ付けができている
場合、ショッピング機能自体はすでに有効なので、以下は「APIからも同じことをできるようにする」
ための追加設定になります。

### 1. 商品カタログをアプリのビジネスと共有する

STEP 4で行ったFacebookページの共有と同じ手順です。

1. https://business.facebook.com/settings/catalogs を開く
2. 左上のポートフォリオ切り替えで、**そらみ**(商品カタログを持っている方)を選択
3. 対象のカタログを選び「パートナーを追加」→ Sorami-auto-post ビジネスに
   フルコントロールで共有する
   (見つからない場合は、逆に Sorami-auto-post 側から
   「アカウント」→「カタログ」→「追加」→「アクセスの共有をリクエスト」でも同様に共有できます)

### 2. 権限を追加してアクセストークンを再取得する

1. https://developers.facebook.com/apps でアプリを開く →「ユースケース」→
   「Facebookログインによる API」→「アクセス許可と機能」
2. `catalog_management` と `instagram_shopping_tag_products` を追加
3. STEP 4と同じ手順で、Graph API Explorerからアクセストークンを再生成し
   (今回追加した2つの権限も含める)、長期トークンに交換する
4. 新しい長期トークンで、GitHub Secretsの `IG_ACCESS_TOKEN` を更新する

### 3. 商品IDを確認する

1. https://business.facebook.com/commerce/ を開き、対象のカタログを選択
2. 「商品」の一覧から、タグ付けしたい商品をクリック
3. URLや商品詳細に表示される数字の商品ID(Content ID / Retailer IDとは別の、
   カタログ内部のID)をコピーする

### 4. スプレッドシートに入力する

タグ付けしたい行の「商品タグID」列に、その商品IDを貼り付けてください。
空欄の行は、これまで通りタグなしで投稿されます。

タグは画像の中央に固定で表示されます(位置を商品ごとに変えたい場合は、また
教えてください)。

## STEP 10(任意): ストーリーズ自動投稿を設定する

フィード投稿とは別に、Instagramストーリーズを自動投稿する機能です。
フィード投稿と同じアプリ・同じアクセストークンを使うので、追加のSecrets登録は不要です。

### 1. スプレッドシートに「ストーリー管理」タブを追加する

1. スプレッドシート下部の「+」ボタンで新しいタブを作成
2. タブ名を `ストーリー管理` にする
3. 1行目に以下の列名をそのまま入力する

   ```
   投稿日 / 投稿時刻 / 投稿日時 / 動画ファイル名 / 投稿済みフラグ / 投稿日時(実績) / 結果メモ
   ```

### 2. 先にスプレッドシートで投稿予定日を決めておく

「ストーリー管理」タブに、投稿したい日時だけ先に入力してください(動画ファイル名は空欄のまま)。
週2回程度など、ご自身で投稿したいペースに合わせて、複数行まとめて決めておいても構いません。

### 3. ストーリー動画を追加する

1. `scripts/add_story.command` をダブルクリック
2. 投稿したい動画ファイル(.mp4 または .mov)を選ぶ
3. 保存するファイル名(半角英数字、例: `story1.mp4`)を入力
4. 自動で `stories/` フォルダに追加され、GitHubにpushされる
5. 続けて、「投稿日時は入力済みだが動画ファイル名が空欄」の一番上の行に、
   自動でそのファイル名が入力される(フィード投稿の`add_photo.command`と同じ仕組み)

見つからなかった場合は「手動で入力してください」とメッセージが出るので、
その場合はスプレッドシートに直接入力してください。

### 運用メモ

- 同じ日にフィード投稿(「投稿管理」タブ)が予定されている場合、その日のストーリーは
  自動的にスキップされます(投稿済みフラグが `スキップ` になります)。同じ日に両方
  投稿したい場合は、日付をずらすか、後日この仕組みの調整を相談してください。
- 動画ファイルはGitHubリポジトリに保存されるため、あまり大きすぎるファイル
  (数十MB以上)は避けてください。
