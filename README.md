# Manual Bot AI 🚀

エンタープライズ向けLINE Bot管理システム。PDF/Wordドキュメントをアップロードして、AIが自動で質問に回答します。

## 🌟 特徴

- **LINE Bot統合**: 自然な会話でマニュアル検索
- **多言語対応**: 日本語・英語・中国語・韓国語
- **厳密RAGシステム**: アップロードされたマニュアルのみ参照
- **Stripe決済**: サブスクリプションモデル
- **マルチテナント**: 複数顧客管理

## 🚀 Railwayデプロイ

### 1. Railwayアカウント作成
[railway.app](https://railway.app) でアカウントを作成

### 2. Railway CLIインストール
```bash
npm install -g @railway/cli
```

### 3. デプロイスクリプト実行
```bash
chmod +x deploy_to_railway.sh
./deploy_to_railway.sh
```

### 4. 環境変数設定（Railwayダッシュボードで）
```bash
LINE_CHANNEL_ACCESS_TOKEN=your_line_access_token
LINE_CHANNEL_SECRET=your_line_secret
OPENAI_API_KEY=your_openai_key
STRIPE_PUBLISHABLE_KEY=your_stripe_key
ADMIN_LINE_USER_ID=your_admin_line_user_id
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

## 🔧 ローカル開発

### 環境構築
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 起動
```bash
python main.py
```

ブラウザで http://localhost:8080 にアクセス

## 📋 APIキー取得

### LINE Developers
1. [LINE Developers](https://developers.line.biz/) でアカウント作成
2. Messaging APIチャンネル作成
3. Channel Access Token と Channel Secret を取得

### OpenAI
1. [OpenAI Platform](https://platform.openai.com/) でAPIキー取得

### Stripe
1. [Stripe Dashboard](https://dashboard.stripe.com/) でアカウント作成
2. Publishable Keyを取得

## 🎯 使い方

1. **LPアクセス**: `https://your-app.railway.app/landing`
2. **ログイン**: テストアカウント `test@example.com` / `password`
3. **ファイルアップロード**: PDF/Wordファイルをアップロード
4. **LINE連携**: ダッシュボードからLINE Botと連携
5. **質問**: LINEでマニュアルについて質問

## 📁 プロジェクト構造

```
├── main.py                 # Flaskメインアプリ
├── templates/             # HTMLテンプレート
├── static/               # CSS/JSファイル
├── requirements.txt      # Python依存関係
├── railway.json         # Railway設定
├── nixpacks.toml       # Railwayビルド設定
└── README.md           # このファイル
```

## 🔒 セキュリティ

- JWT認証
- ファイルアップロード制限
- SQLインジェクション対策
- 環境変数管理

## 📞 サポート

- **ドキュメント**: [OPERATION_MANUAL.md](OPERATION_MANUAL.md)
- **テストガイド**: [COMPLETE_TEST_GUIDE.md](COMPLETE_TEST_GUIDE.md)
- **本番設定**: [PRODUCTION_SETUP.md](PRODUCTION_SETUP.md)

---

## 📊 システム要件

- Python 3.11+
- SQLite (開発) / PostgreSQL (本番)
- 512MB RAM以上

## 💰 料金目安

- Railway: $5/月 (Starterプラン)
- OpenAI: $0.002/1Kトークン
- Stripe: 3.4% + 35円/決済
- Supabase: $0/月 (無料枠内)

---

Made with ❤️ for enterprise automation
