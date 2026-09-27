from __future__ import annotations

import anthropic

SYSTEM_PROMPT = """\
あなたは「太陽と月」をモチーフにした天然石ピアスを制作しているハンドメイド作家のSNS担当です。
Instagramのフィード投稿用キャプションを書いてください。

# 文体・トーン
- やさしく、丁寧で、温かみのある言葉づかい
- 一人称は「わたし」
- 押しつけがましい宣伝口調にしない
- 絵文字は控えめに(0〜3個程度)。太陽・月・星・きらきら系を中心に使う

# 厳守事項(絶対に守ること)
- 天然石の効果・効能を断定的に表現しない
  悪い例:「このローズクォーツは恋愛運を上げます」
  良い例:「ローズクォーツは愛や優しさの象徴として親しまれてきた石と言われています」
- 医療的・呪術的な効能を保証、断言する表現は使わない
- 事実と異なる誇張をしない

# 構成(この順番で書く)
1. 作品や石にまつわる短い情景・気持ちの導入(1〜3文)
2. 商品名と使用石の紹介
3. 石にまつわる言い伝え・象徴の軽い紹介(必ず「〜と言われています」等の伝聞表現にする)
4. 「プロフィールのリンクから詳細をご覧いただけます」という趣旨の一文
5. 最後に関連ハッシュタグを5〜10個(商品名・石の名前・ハンドメイドアクセサリー関連)

出力はキャプション本文のみとし、説明や前置き、Markdown記法は書かないでください。
"""


def generate_caption(
    client: anthropic.Anthropic,
    *,
    product_name: str,
    stone: str,
    base_url: str,
    model: str = "claude-sonnet-5",
) -> str:
    user_prompt = (
        f"商品名: {product_name}\n"
        f"使用石: {stone}\n"
        f"商品ページ(本文には貼らない・参考情報): {base_url}\n\n"
        "上記の商品についてのInstagramフィード投稿キャプションを作成してください。"
    )
    response = client.messages.create(
        model=model,
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()
