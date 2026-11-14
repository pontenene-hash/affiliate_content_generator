# アフィリエイト記事＋SNS制作プロンプト機能

既存のSEO記事生成、競合調査、A8登録商品、WordPress下書き保存、毎月5・15・25日のスケジュールは維持しています。

## 追加内容

記事のWordPress下書き保存に成功した場合、同じ記事本文を元にGeminiでSNS投稿文・画像動画制作プロンプトを作ります。ブログ用4枚の画像プロンプトとGBP用投稿・画像・動画プロンプトも保存します。

GitHub Actions「Affiliate draft generation」の実行結果から `affiliate-creative-prompts-実行番号` をダウンロードします。記事IDごとのフォルダに `blog_images.md`、`social_posts.md`、`social_image_video_prompts.md`、`gbp.md`、`all_prompts.json` が入ります。ChatGPTで画像を生成し、WordPressへ手動でアップロードしてください。

SNS用プロンプトは元アプリの `social_tools.py` を再利用します。Geminiの利用枠・出力トークン上限によりSNS生成が失敗しても、WordPress記事の下書きは保持され、レポートに `creative: error` が記録されます。無料枠内での動作は保証されません。

## 注意

このZIPはアップロードされたアフィリエイトアプリの版に対する修正版です。GitHub上の最新版と差分を確認し、既存のGitHubワークフローを不用意に上書きしないでください。アップロードされた `affiliate_images(2).yml` は既存の手動画像プロンプトワークフローとして変更していません。

A8.netのリンクと各種広告表記、医療・健康情報、SNS規約は公開前に確認してください。GBPはアフィリエイト誘導投稿が媒体の規約・店舗との関連性に合うかを必ず確認してください。
