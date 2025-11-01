#!/bin/bash

# Railwayデプロイスクリプト
echo "🚀 Manual Bot AI - Railwayデプロイスクリプト"
echo "=============================================="

# 現在のディレクトリがプロジェクトルートか確認
if [ ! -f "main.py" ]; then
    echo "❌ エラー: main.pyが見つかりません。プロジェクトルートで実行してください。"
    exit 1
fi

# Railway CLIのインストール確認
if ! command -v railway &> /dev/null; then
    echo "📦 Railway CLIをインストールします..."
    npm install -g @railway/cli
fi

# Railwayにログイン
echo "🔐 Railwayにログインしてください..."
railway login

# 新しいRailwayプロジェクトを作成
echo "📁 新しいRailwayプロジェクトを作成します..."
railway init manual-bot-ai --source=.

# 環境変数を設定
echo "🔧 環境変数を設定します..."
railway variables set LINE_CHANNEL_ACCESS_TOKEN="$LINE_CHANNEL_ACCESS_TOKEN"
railway variables set LINE_CHANNEL_SECRET="$LINE_CHANNEL_SECRET"
railway variables set OPENAI_API_KEY="$OPENAI_API_KEY"
railway variables set STRIPE_PUBLISHABLE_KEY="$STRIPE_PUBLISHABLE_KEY"
railway variables set ADMIN_LINE_USER_ID="$ADMIN_LINE_USER_ID"
railway variables set FLASK_SECRET_KEY="$(openssl rand -hex 32)"
railway variables set SUPABASE_URL="$SUPABASE_URL"
railway variables set SUPABASE_KEY="$SUPABASE_KEY"

# データベースの設定（Supabaseを使用）
railway variables set DATABASE_URL="$SUPABASE_URL"

# デプロイ
echo "🚀 デプロイを開始します..."
railway deploy

# デプロイ完了後、URLを取得
echo "📋 デプロイ情報を取得します..."
railway domain

echo ""
echo "✅ Railwayデプロイ完了！"
echo "📝 次の手順:"
echo "   1. RailwayダッシュボードでURLを確認"
echo "   2. LINEデベロッパーコンソールでWebhook URLを更新"
echo "   3. アプリをテスト"
echo ""
echo "🔗 Railwayダッシュボード: https://railway.app/dashboard"
