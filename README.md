# Manual Bot AI

エンタープライズ向けLINE Bot管理システム。ドキュメントの自動回答とインテリジェントなカスタマーサポートを実現します。

## 🚀 特徴

- **LINE Bot統合**: シームレスなLINE Bot連携
- **ドキュメント処理**: PDF, DOCX, TXTファイルの自動処理
- **AI応答システム**: OpenAI GPT-3.5 Turboによるインテリジェント応答
- **RAGアーキテクチャ**: ドキュメントに基づいた正確な回答
- **マルチ言語対応**: 日本語・英語・中国語・韓国語
- **Stripe決済**: サブスクリプションベースの課金システム
- **マルチテナント**: 複数顧客の管理
- **リアルタイムダッシュボード**: MRR/ARR分析とチャーン分析

## 🏗️ アーキテクチャ

- **Frontend**: HTML/CSS/JavaScript, Bootstrap
- **Backend**: Python Flask
- **Database**: SQLite (開発), PostgreSQL (本番)
- **AI**: OpenAI GPT-3.5 Turbo
- **Messaging**: LINE Messaging API
- **Payment**: Stripe API
- **Hosting**: Railway (推奨)

## 📋 前提条件

- Python 3.11+
- LINE Business Account
- OpenAI API Key
- Stripe Account (オプション)

## 🚀 クイックスタート

### 1. リポジトリのクローン

```bash
git clone https://github.com/your-username/manual-bot-ai.git
cd manual-bot-ai
```

### 2. 環境構築

```bash
# 仮想環境作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt
```

### 3. 環境変数設定

`.env` ファイルを作成:

```bash
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret
OPENAI_API_KEY=your_openai_api_key
SECRET_KEY=your_secret_key_here
STRIPE_SECRET_KEY=your_stripe_secret_key  # オプション
DATABASE_PATH=manual_bot.db
```

### 4. データベース初期化

```bash
python -c "from main import init_db; init_db()"
```

### 5. アプリケーション起動

```bash
python main.py
```

ブラウザで `http://localhost:8080` にアクセス

## 🔧 設定

### LINE Bot設定

1. [LINE Developers Console](https://developers.line.biz/console/) にアクセス
2. 新しいチャンネルを作成 (Messaging API)
3. Channel Access Token と Channel Secret を取得
4. Webhook URL: `https://your-domain.com/webhook`

### OpenAI設定

1. [OpenAI Platform](https://platform.openai.com/) にアクセス
2. API Key を生成
3. 使用量制限を確認

### Stripe設定 (オプション)

1. [Stripe Dashboard](https://dashboard.stripe.com/) にアクセス
2. API Keys を取得
3. Webhook設定 (決済イベント用)

## 📁 プロジェクト構造

```
manual-bot-ai/
├── main.py                 # Flaskアプリケーション
├── requirements.txt        # Python依存関係
├── Procfile               # Railwayデプロイ設定
├── runtime.txt            # Pythonバージョン指定
├── static/                # CSS, JS, 画像
├── templates/             # HTMLテンプレート
│   ├── landing.html       # ランディングページ
│   ├── dashboard.html     # ダッシュボード
│   └── login.html         # ログインページ
├── uploads/               # アップロードファイル
├── .gitignore            # Git除外設定
└── README.md             # このファイル
```

## 🔒 セキュリティ

- JWTベースのセッションマネジメント
- ファイルアップロードのセキュリティ検証
- APIキーの環境変数管理
- SQLインジェクション対策
- XSS対策

## 🧪 テスト

### ローカルテスト

```bash
# 開発サーバー起動
python dev_start.sh

# テストアカウント
Email: test@example.com
Password: password
```

### LINE Botテスト

1. ダッシュボードからファイルをアップロード
2. LINE Botと連携
3. LINEから質問を送信

## 🚀 デプロイ

### Railway (推奨)

1. GitHubにプッシュ
2. Railwayでプロジェクト作成
3. 環境変数を設定
4. LINE Webhook URLを設定

### 手動デプロイ

```bash
# Railway CLI使用
railway login
railway link
railway up
```

## 📊 APIドキュメント

### 主要エンドポイント

- `GET /` - ランディングページ
- `GET /dashboard` - ダッシュボード
- `POST /upload` - ファイルアップロード
- `POST /webhook` - LINE Webhook
- `POST /login` - ログイン

## 🐛 トラブルシューティング

### 一般的な問題

1. **LINE Botが応答しない**
   - Webhook URLが正しく設定されているか確認
   - 環境変数が正しく設定されているか確認

2. **ファイルアップロードエラー**
   - ファイルサイズが50MBを超えていないか確認
   - サポートされたフォーマットか確認 (PDF, DOCX, TXT)

3. **AI応答エラー**
   - OpenAI APIキーが有効か確認
   - 使用量制限に達していないか確認

## 📈 パフォーマンス

- 平均応答時間: < 2秒
- 同時接続数: 100+
- ファイル処理: 最大50MB
- 月間メッセージ: 無制限 (プランによる)

## 🤝 貢献

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 📞 サポート

- Issue: [GitHub Issues](https://github.com/your-username/manual-bot-ai/issues)
- Email: support@manual-bot-ai.com

---

## 🎯 次のステップ

1. **デプロイ**: Railwayで本番環境を構築
2. **カスタマイズ**: UI/UXの改善
3. **拡張**: 新機能の追加 (音声対応, 複数言語, etc.)
4. **スケーリング**: クラウドインフラの最適化

**Manual Bot AI** であなたのビジネスを次のレベルへ！ 🚀