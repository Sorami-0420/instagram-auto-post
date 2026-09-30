#!/bin/bash
set -e
cd "$(dirname "$0")/.."

echo "投稿するストーリー動画を選んでください..."
SRC_FILE=$(osascript -e 'POSIX path of (choose file with prompt "投稿するストーリー動画を選んでください" default location (path to movies folder))') || {
  echo "キャンセルされました。"
  exit 0
}

echo "保存するファイル名を入力してください(半角英数字、拡張子込み)"
NEW_NAME=$(osascript -e 'text returned of (display dialog "保存するファイル名を入力してください(入力欄の文字は一度全部消してから入力してください)\n半角英数字のみ・拡張子込み(例: story1.mp4)" default answer "")') || {
  echo "キャンセルされました。"
  exit 0
}

if [ -z "$NEW_NAME" ]; then
  osascript -e 'display alert "ファイル名が空でした。もう一度実行してください。"'
  exit 1
fi

case "$NEW_NAME" in
  *.mp4|*.mov|*.MP4|*.MOV) ;;
  *)
    osascript -e "display alert \"ファイル名の形式が正しくありません: $NEW_NAME\n.mp4 か .mov で終わる半角英数字の名前にしてください。もう一度実行してください。\""
    exit 1
    ;;
esac

DEST="stories/$NEW_NAME"
cp "$SRC_FILE" "$DEST"

git add "$DEST"
git commit -m "ストーリー動画を追加: $NEW_NAME"
git push origin main

osascript -e "display notification \"stories/$NEW_NAME として公開しました\" with title \"ストーリー動画の追加が完了しました\""
echo ""
echo "完了しました: $DEST"
echo ""

echo "スプレッドシートに自動反映を試みます..."
SHEET_RESULT=$(python3 scripts/update_story_sheet.py "$NEW_NAME" 2>&1) || SHEET_RESULT="スプレッドシートへの自動入力でエラーが発生しました。手動で入力してください。"
echo "$SHEET_RESULT"

echo ""
echo "このウィンドウは閉じて大丈夫です。"
read -p "Enterキーを押すと閉じます..."
