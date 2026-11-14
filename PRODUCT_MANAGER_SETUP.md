# A8.net商品管理（追加機能）

## 登録方法
Streamlitアプリの「🛍️ A8.net 提携商品を登録・停止・削除」を開きます。A8.netで提携承認済みの案件について、商品名、ジャンル、**公式商品紹介ページURL**、A8.netの**通常広告コード**を入力して登録してください。登録後、停止・再開・削除ができます。

**重要**：A8.netの広告コードだけでは公式の商品紹介ページURLを特定できません。別途入力してください。承認状況は自動照会できないため、A8.netの会員画面で確認してください。

## GitHub Actionsと同期するための設定
Streamlit Community Cloudのアプリ設定 > Secrets に次の値を追加します（トークンはコードやチャットに貼らないでください）。

```toml
GITHUB_TOKEN = "GitHub fine-grained token (対象リポジトリ Contents: Read and write)"
GITHUB_REPOSITORY = "ユーザー名/affiliate_content_generator"
GITHUB_BRANCH = "main"
```

登録・停止・削除は `data/affiliate_products.json` にGitHub Contents APIで保存され、次のGitHub Actions実行時に読み込まれます。StreamlitとGitHubを同期しない場合はローカルJSONに保存されますが、クラウド環境では永続性・自動処理との同期を保証できません。

## 動作上の注意
- 登録が0件のときは従来の `a8_verified_items.json` にフォールバックします。
- 有効な登録商品が存在するときは、その登録商品を優先します。
- 1回につき最大5件の未処理商品を対象とし、履歴に記録された同じ商品は再処理しません。
- WordPressへは**下書き**で保存し、公開はしません。
- GitHub Actionsの実行が成功しても、処理対象が0件のことがあります。実行ログの `processed` と `results` を確認してください。
- 本ZIPは既存の手動記事生成・競合分析・SNS生成コードを残した追加版です。API接続を含む本番実行は未検証です。
