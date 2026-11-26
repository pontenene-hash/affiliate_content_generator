第18段階 検証ブランチ専用パッチ（本番導入不可）
対象: pontenene-hash/affiliate_content_generator / feature-affiliate-v2-validation
既存ファイルのバックアップ後、ZIP内のパスを維持して上書き。main、affiliate_auto.yml は変更しない。
Actions > Affiliate V5 Safety Test > Run workflow > feature-affiliate-v2-validation を選択。
最初は run_live=false のまま実行。全テスト合格後に run_live=true、preview_product=HARIO NETSHOP で実行。
成果物 affiliate-v2-validation-results と affiliate-v2-live-preview を取得。
実APIプレビューは1記事、WP保存なし。履歴書き込みなし。実料金・5記事・永続保存・WP下書きは別途検証。
ローカル315件合格。Markdown未導入のため test_stage5_ads.py 除外。CIでは除外なし。
戻す場合は今回のコミットを検証ブランチで revert。
