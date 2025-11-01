#!/bin/bash

# Railway環境変数設定スクリプト
echo "🔧 Manual Bot AI - Railway環境変数設定"
echo "========================================"

# 環境変数の確認
echo "📋 必要なAPIキーを確認してください："
echo ""

# LINE APIキーの確認
if [ -z "$LINE_CHANNEL_ACCESS_TOKEN" ]; then
    echo "❌ LINE_CHANNEL_ACCESS_TOKEN が設定されていません"
    echo "   LINE Developers Consoleから取得してください"
    exit 1
fi

if [ -z "$LINE_CHANNEL_SECRET" ]; then
    echo "❌ LINE_CHANNEL_SECRET が設定されていません"
    echo "   LINE Developers Consoleから取得してください"
    exit 1
fi

# OpenAI APIキーの確認
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY が設定されていません"
    echo "   OpenAI Platformから取得してください"
    exit 1
fi

# Stripe APIキーの確認
if [ -z "$STRIPE_PUBLISHABLE_KEY" ]; then
    echo "❌ STRIPE_PUBLISHABLE_KEY が設定されていません"
    echo "   Stripe Dashboardから取得してください"
    exit 1
fi

echo "✅ 全てのAPIキーが設定されています"
echo ""

# Railway CLIの確認
if ! command -v railway &> /dev/null; then
    echo "📦 Railway CLIをインストールします..."
    npm install -g @railway/cli
fi

# Railwayログイン確認
echo "🔐 Railwayにログインしてください..."
railway login

# プロジェクト選択
echo "📁 Railwayプロジェクトを選択してください..."
railway list

# 環境変数設定
echo "🔧 環境変数をRailwayに設定します..."

railway variables set LINE_CHANNEL_ACCESS_TOKEN="$LINE_CHANNEL_ACCESS_TOKEN"
railway variables set LINE_CHANNEL_SECRET="$LINE_CHANNEL_SECRET"
railway variables set OPENAI_API_KEY="$OPENAI_API_KEY"
railway variables set STRIPE_PUBLISHABLE_KEY="$STRIPE_PUBLISHABLE_KEY"
railway variables set ADMIN_LINE_USER_ID="${ADMIN_LINE_USER_ID:-U7e1c32868dab73e2852161aa72833a2a}"
railway variables set FLASK_SECRET_KEY="$(openssl rand -hex 32)"
railway variables set SUPABASE_URL="${SUPABASE_URL:-}"
railway variables set SUPABASE_KEY="${SUPABASE_KEY:-}"

echo ""
echo "✅ 環境変数設定完了！"
echo ""
echo "🚀 次にデプロイスクリプトを実行してください："
echo "   ./deploy_to_railway.sh"
echo ""
echo "📋 設定された環境変数:"
echo "   • LINE_CHANNEL_ACCESS_TOKEN: ✅"
echo "   • LINE_CHANNEL_SECRET: ✅"
echo "   • OPENAI_API_KEY: ✅"
echo "   • STRIPE_PUBLISHABLE_KEY: ✅"
echo "   • ADMIN_LINE_USER_ID: ✅"
echo "   • FLASK_SECRET_KEY: ✅ (自動生成)"
echo "   • SUPABASE_URL: $([ -n "$SUPABASE_URL" ] && echo '✅' || echo '⚠️  未設定')"
echo "   • SUPABASE_KEY: $([ -n "$SUPABASE_KEY" ] && echo '✅' || echo '⚠️  未設定')"
