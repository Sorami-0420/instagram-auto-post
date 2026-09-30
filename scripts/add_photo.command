#!/bin/bash
set -e
cd "$(dirname "$0")/.."

echo "投稿する写真を選んでください..."
SRC_FILE=$(osascript -e 'POSIX path of (choose file with prompt "投稿する写真を選んでください" default location (path to pictures folder))') || {
  echo "キャンセルされました。"
  exit 0
}

echo "保存するファイル名を入力してください(半角英数字、拡張子込み)"
NEW_NAME=$(osascript -e 'text returned of (display dialog "保存するファイル名を入力してください\n半角英数字のみ・拡張子込み(例: item1.jpg)" default answer "item.jpg")') || {
  echo "キャンセルされました。"
  exit 0
}

DEST="posts/$NEW_NAME"
cp "$SRC_FILE" "$DEST"

git add "$DEST"
git commit -m "画像を追加: $NEW_NAME"
git push origin main

osascript -e "display notification \"posts/$NEW_NAME として公開しました\" with title \"画像の追加が完了しました\""
echo ""
echo "完了しました: $DEST"
echo "このウィンドウは閉じて大丈夫です。"
read -p "Enterキーを押すと閉じます..."
