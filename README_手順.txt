V5安全修正版（feature-affiliate-sns 専用）

1. GitHubの feature-affiliate-sns ブランチに以下3ファイルをアップロード／置換する。
   affiliate_quality_v5.py
   install_affiliate_quality_v5.py
   test_affiliate_quality_v5.py
   ※ auto_pipeline.py、social_tools.py、affiliate_auto.yml は変更しない。
2. GitHub Actionsの既存 safe_patch_check は旧V4用なので、V5検証には使用しない。
3. GitHub ActionsでV5の実行を自動化する前に、テスト用の別ワークフローを追加するか、ローカルPython環境で次を実行する。
   python test_affiliate_quality_v5.py
4. テスト成功後にのみ、バックアップを取った上で以下を実行する。
   python install_affiliate_quality_v5.py auto_creative.py
5. インストール後はGeminiを使った保存済み記事の再生成で検証する。
   初回は本番公開しない。出力された文章・PR表記・リンク・医療関連表現を人が確認する。

注意：このパッケージは生成プロンプトを整えるもので、画像・動画そのものを作りません。
医療広告等の法令適合性や公式情報の事実確認を保証するものではありません。
