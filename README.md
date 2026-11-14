# ChatGPT画像4枚・WordPress下書き反映ツール（半自動・追加画像API料金なし）

## 何ができるか
- 記事タイトル・商品情報から、ChatGPT向けの画像指示書 `prompts.md` を生成
- 公式画像1枚＋ChatGPTで作った画像3枚をZIPにまとめて受け取り
- WordPress REST APIで4枚をメディアライブラリに登録し、下書き本文とアイキャッチに設定
- 既存の `auto_pipeline.py`、Gemini、Brave、A8.net、GitHub Actionsの設定を**変更しない**独立した追加ツール
- 画像生成APIキーは不要。ChatGPTでの画像作成は契約中の利用枠に従う

## 重要な違い
現段階は既存のGitHub Actionsへ自動組み込み済みではありません。元の `auto_pipeline.py` と `affiliate_auto.yml` を確認していないため、記事生成時に自動でプロンプトを出力する連携は未実装です。まず安全に独立動作を確認してください。

## 操作手順
1. `article.example.json` をコピーして `article.json` とし、記事の `post_id`（WordPress編集画面のURLの `post=数字`）、`title`、`product_name`、`audience` を入力。**プレビューURLの `p=数字` は一致する場合がありますが、編集画面で確認してください。**
2. `python image_workflow.py prompts --article article.json --output image_prompts` を実行。
3. `image_prompts/prompts.md` の指示をChatGPTへ渡して画像を作成。**1枚目は公式の使用許可済み商品写真を用意**し、2〜4枚目はChatGPTで生成。
4. 4枚の画像を次の名前で保存してZIPにまとめる（ZIP直下でもフォルダ内でも可）：
   - `01_official.png`（またはjpg/webp）
   - `02_lifestyle.png`
   - `03_explainer.png`
   - `04_empathy.png`
5. WordPressの**アプリケーションパスワード**を用意し、環境変数 `WP_SITE_URL`、`WP_USERNAME`、`WP_APP_PASSWORD` を設定。既存のGitHub Secretsを使う場合も、値を画面やチャットに貼らないでください。
6. `python image_workflow.py install --post-id 1006 --zip images.zip` で事前チェック。実際に反映する場合は `--apply` を付けて実行。
7. WordPressの下書きを開き、4枚・アイキャッチ・広告リンクを確認してから公開。

## 注意
- WordPress側でREST APIとメディアアップロードを許可してください。403の場合はXserverの設定やユーザー権限を確認。
- 既存の本文は上書き保存されるため、**WordPressの下書きバックアップを推奨**。画像反映は下書きのみ対象。
- 実行途中で失敗すると、WordPressにアップロード済み画像だけが残る場合があります。
- 元記事の生成、重複防止、広告リンクには触れません。医療・検査・健康関連では効果や体験談の捏造に注意。
- WordPressの標準投稿 (`posts`) に対応。カスタム投稿タイプは別途調整が必要。
- ZIP画像は各10MB以下。画像形式はPNG/JPEG/WebP。
