#!/bin/bash
set -e
cd "$(dirname "$0")/.."

echo "投稿する写真を選んでください..."
SRC_FILE=$(osascript -e 'POSIX path of (choose file with prompt "投稿する写真を選んでください" default location (path to pictures folder))') || {
  echo "キャンセルされました。"
  exit 0
}

echo "保存するファイル名を入力してください(半角英数字、拡張子込み)"
NEW_NAME=$(osascript -e 'text returned of (display dialog "保存するファイル名を入力してください(入力欄の文字は一度全部消してから入力してください)\n半角英数字のみ・拡張子込み(例: item1.jpg)" default answer "")') || {
  echo "キャンセルされました。"
  exit 0
}

if [ -z "$NEW_NAME" ]; then
  osascript -e 'display alert "ファイル名が空でした。もう一度実行してください。"'
  exit 1
fi

case "$NEW_NAME" in
  *.jpg|*.jpeg|*.png|*.JPG|*.JPEG|*.PNG) ;;
  *)
    osascript -e "display alert \"ファイル名の形式が正しくありません: $NEW_NAME\n.jpg か .png で終わる半角英数字の名前にしてください。もう一度実行してください。\""
    exit 1
    ;;
esac

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
