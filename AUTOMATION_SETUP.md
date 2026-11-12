# A8.net案件 → SEO記事 → WordPress下書き自動保存

## 対応範囲と制約
- 既存の `app.py` の記事・SNS・動画制作プロンプト機能はそのまま残します。
- GitHub Actionsは毎月5・15・25日 00:00 UTC（日本時間09:00）に実行を試みます。混雑時は遅延・スキップの可能性があります。
- 1回最大5件、月最大15件。**提携済みで正規広告リンクを登録した案件のみ**記事化します。条件未達なら5件に届きません。
- A8.netのログインを自動操作しません。A8ランキング上位5件を自動・確実に取得できる公開APIは確認できないため、会員画面で順位を確認し `data/a8_verified_items.json` に登録してください。Brave検索結果は候補調査用で、A8のランキング順位として扱いません。
- 9ジャンルを指定可能です。各ジャンル1〜5位の案件を登録できます。実行は未作成の案件から最大5件ずつです。
- 正規アフィリエイトリンクはA8.netで提携・取得して登録。自動生成・偽造しません。
- 競合分析はBraveの検索結果のタイトル・概要を使用します。**Google上位10件や競合本文のH2/H3抽出とは異なります。**
- 記事の下書き保存はWordPress REST APIを利用します。自動公開しません。
- SEO記事本文のみ自動生成します。既存の手動アプリにあるSNS/動画プロンプトの自動バッチ生成はまだ含みません。

## 初期設定
1. このフォルダを**非公開GitHubリポジトリ**へアップロードします（無料枠・Actions利用条件を確認）。
2. `data/a8_verified_items.example.json` を参考に `data/a8_verified_items.json` を作成。対象9ジャンルそれぞれ1〜5位を登録できます。**実データの順位を確認してから**入力します。
3. A8の広告主と提携し、各案件の `affiliate_url` に正規の広告URLを登録します。代わりに `data/affiliate_links.json` で商品URL→正規広告URLの対応を登録できます。
4. 定期実行用にはGitHub Actions Secretsに `A8_ITEMS_JSON` として案件JSON配列全体を登録します。広告リンクを別管理する場合は `AFFILIATE_LINKS_JSON` に対応JSON全体を登録します。実行時に一時ファイルへ復元します。ファイルはGitにコミットしません。
5. GitHub Settings → Secrets and variables → Actions → Secrets に `GEMINI_API_KEY`, `BRAVE_API_KEY`, `WP_SITE_URL`, `WP_USERNAME`, `WP_APP_PASSWORD` を登録。WordPressは「ユーザー → アプリケーションパスワード」で専用パスワードを発行。通常のログインパスワードは使いません。
6. WordPressのURLは `https://...`、ユーザーには下書き作成権限が必要です。必要ならREST APIへのアクセスをセキュリティプラグインで許可してください。
7. Actions → Affiliate draft generation → Run workflow でテストし、下書きが保存されることを確認してください。
8. `data/pipeline.sqlite3` をActionsがコミットすることで重複作成を避けます。初回は未作成で正常です。GitHubの書き込み権限を許可してください。

## ローカルテスト
```bash
pip install -r requirements.txt
python auto_pipeline.py --limit 5 --dry-run
python auto_pipeline.py --limit 5
```
`--dry-run` でもBrave検索・商品ページ取得は実行しますが、Gemini生成とWordPress投稿はしません。

## 運用上の注意
- A8の広告主との提携審査、広告リンクの取得、記事の最終チェックと公開は手動です。
- API利用枠・料金は提供者側の最新条件に従います。無料継続は保証されません。
- GitHub Actionsでデータファイルが無い場合は0件で終了します。ランキングやリンクを勝手に補完しません。
- WP保存成功後に履歴コミットが失敗すると次回重複の恐れがあります。運用時はWordPress側の下書き一覧も確認してください。
- WordPress REST APIはHTTPSを推奨。公開前に表現・出典・薬機法・景表法・広告表記を確認してください。
