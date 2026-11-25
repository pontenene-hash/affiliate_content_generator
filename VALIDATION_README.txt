検証専用候補版（本番導入不可）
元の第98回ZIPを基準に、別ブランチでのみファイルを配置してください。
Actions > Affiliate V2 Offline Validation > Run workflow で検証ブランチを指定。既存の Affiliate Auto Generator は実行しないでください。
このワークフローは手動起動のみ、contents: read、APIシークレットを渡さず、テスト結果XMLを保存します。
実記事のテスト用資料はURLを匿名化しています。
ローカルではMarkdown不足のため test_stage5_ads.py を除外して57件通過、別途2つのスクリプトも成功。
実API、実際の5記事生成、定期運用は未検証。
