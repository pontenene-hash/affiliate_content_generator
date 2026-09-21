# アフィリエイト記事・SNS一括生成アプリ

商品ページURLとアフィリエイトURLを入力するだけで、SEO記事、SNS投稿文、投稿画像、動画台本、動画素材まで作成するStreamlitアプリです。

## 自動生成するもの

- 想定読者の深い悩み・検索意図
- H2・H3のSEO見出し構成
- PREP法による完成記事（Markdown／WordPress HTML）
- Instagramキャプションと9枚カルーセル
- X投稿文3パターン
- Facebook投稿文と1200×630pxアイキャッチ
- Threads投稿文
- LINE配信用文
- Instagramリール動画（1080×1920）
- YouTube動画（1920×1080）とサムネイル
- TikTok動画（1080×1920）
- 完成素材の一括ZIP

投稿文には【PR】表記とアフィリエイトURLを自動挿入します。Instagramでは「プロフィールのリンク」への誘導も生成します。

## 無料で使う方法

記事・SNS文章・動画ナレーションにはGemini APIの無料枠を使います。投稿画像は追加APIを使わず、Pythonで標準イラストを描画するため無料です。

1. [Google AI Studio](https://aistudio.google.com/apikey)へアクセス
2. Googleアカウントでログイン
3. 新しいGemini APIキーを作成してコピー
4. アプリ左側の「Gemini APIキー」に貼り付け

有料請求を設定しない限り有料枠へ自動移行しません。ただし無料枠には回数・速度の上限があります。

## Windowsで起動する方法

Python 3.10以上をインストールし、このフォルダ内でPowerShellを開いて次を実行します。

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

ブラウザが開かない場合は、画面に表示される `http://localhost:8501` を開きます。

## Streamlit Community Cloudへ公開する方法

1. このフォルダ内のファイルをGitHubリポジトリへアップロード
2. Streamlit Community Cloudでリポジトリと `app.py` を選択
3. Settings → Secrets に次を登録

```toml
GEMINI_API_KEY = "ここにGemini APIキー"
GEMINI_MODEL = "gemini-3.5-flash-lite"
BRAND_NAME = "表示したいサイト名"
```

4. Saveしてアプリを再起動

APIキーをGitHub上のファイルへ直接書かないでください。

## 使い方

1. 商品の公式ページまたは詳細ページURLを入力
2. ASPで発行した自分のアフィリエイトURLを入力
3. 「記事を生成する」を押す
4. 記事・SNS文章・画像を確認してダウンロード
5. 必要な動画だけ個別に作成

動画は処理負荷と無料枠を節約するため、リール・YouTube・TikTokを別々に生成します。途中で無料枠の上限になっても、完成済み素材はZIPで保存できます。

## 売上につなげる運用提案

- 記事公開前に、実際に使った感想や独自写真を追加する
- 商品名だけでなく「悩み＋商品ジャンル」の記事も作り、内部リンクで商品記事へつなぐ
- InstagramのプロフィールリンクにアフィリエイトURLまたは記事URLを設定する
- SNSから直接商品へ送る投稿と、詳しい記事へ送る投稿を使い分ける
- 価格、在庫、キャンペーン、特典は公開直前に公式ページで確認する
- クリック数・成約数をASPで確認し、反応の良い訴求へ寄せる

## 注意事項

- ログイン必須ページ、JavaScriptのみで表示するページ、取得を拒否するページは読み込めない場合があります。
- AIは誤ることがあります。公開前に商品情報、法令、媒体規約を確認してください。
- 架空の口コミや体験談は生成しない設計です。実体験がある場合は、生成後にご自身の言葉で追加してください。
- 健康・美容商品は薬機法、景品表示法、健康増進法などに配慮してください。
- SNSやASPごとにアフィリエイトリンク掲載ルールが異なります。利用中の規約を確認してください。
- Geminiの無料枠、モデル、TTSの提供条件は変更される場合があります。
