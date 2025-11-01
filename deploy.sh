#!/bin/bash

# Manual Bot AI - 自動デプロイスクリプト
# Railwayへのデプロイを自動化します

set -e  # エラー発生時に停止

echo "🚀 Manual Bot AI - 自動デプロイスクリプト"
echo "========================================"

# 色の定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 関数定義
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 環境チェック
check_environment() {
    log_info "環境チェックを開始..."

    # Gitがインストールされているか
    if ! command -v git &> /dev/null; then
        log_error "Gitがインストールされていません"
        exit 1
    fi

    # Pythonがインストールされているか
    if ! command -v python3 &> /dev/null; then
        log_error "Python3がインストールされていません"
        exit 1
    fi

    log_info "環境チェック完了"
}

# 依存関係チェック
check_dependencies() {
    log_info "依存関係チェック..."

    if [ ! -f "requirements.txt" ]; then
        log_error "requirements.txtが見つかりません"
        exit 1
    fi

    if [ ! -f "Procfile" ]; then
        log_error "Procfileが見つかりません"
        exit 1
    fi

    if [ ! -f "runtime.txt" ]; then
        log_error "runtime.txtが見つかりません"
        exit 1
    fi

    log_info "依存関係チェック完了"
}

# セキュリティチェック
security_check() {
    log_info "セキュリティチェック..."

    # APIキーがハードコードされていないかチェック
    if grep -r "sk-" main.py &> /dev/null; then
        log_error "main.pyにハードコードされたAPIキーが見つかりました"
        log_error "環境変数を使用してください"
        exit 1
    fi

    if grep -r "LINE_CHANNEL_ACCESS_TOKEN.*=.*[" main.py &> /dev/null; then
        log_error "main.pyにハードコードされたLINEトークンが見つかりました"
        log_error "環境変数を使用してください"
        exit 1
    fi

    log_info "セキュリティチェック完了"
}

# コード品質チェック
code_quality_check() {
    log_info "コード品質チェック..."

    # Python構文チェック
    if python3 -m py_compile main.py; then
        log_info "Python構文チェック: ✅"
    else
        log_error "Python構文エラー"
        exit 1
    fi

    # インポートチェック
    if python3 -c "import main" &> /dev/null; then
        log_info "インポートチェック: ✅"
    else
        log_error "インポートエラー"
        exit 1
    fi

    log_info "コード品質チェック完了"
}

# Gitチェック
git_check() {
    log_info "Gitリポジトリチェック..."

    if [ ! -d ".git" ]; then
        log_error "Gitリポジトリが見つかりません"
        exit 1
    fi

    # 未コミットの変更があるか
    if [ -n "$(git status --porcelain)" ]; then
        log_warn "未コミットの変更があります"
        log_warn "以下のコマンドで変更を確認:"
        log_warn "git status"
        log_warn "git add . && git commit -m 'Deploy changes'"
        read -p "続行しますか？ (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    # リモートが存在するか
    if ! git remote get-url origin &> /dev/null; then
        log_error "Git remote 'origin'が設定されていません"
        exit 1
    fi

    log_info "Gitチェック完了"
}

# Railwayチェック
railway_check() {
    log_info "Railwayチェック..."

    # Railway CLIがインストールされているか
    if ! command -v railway &> /dev/null; then
        log_error "Railway CLIがインストールされていません"
        log_error "インストール方法: npm install -g @railway/cli"
        exit 1
    fi

    # Railwayにログインしているか
    if ! railway whoami &> /dev/null; then
        log_error "Railwayにログインしていません"
        log_error "railway login を実行してください"
        exit 1
    fi

    log_info "Railwayチェック完了"
}

# デプロイ実行
deploy() {
    log_info "デプロイスクリプト実行開始..."

    # チェック実行
    check_environment
    check_dependencies
    security_check
    code_quality_check
    git_check
    railway_check

    echo
    log_info "🎯 すべてのチェックが完了しました"
    echo
    log_info "🚀 デプロイを開始します"
    echo

    # Gitプッシュ
    log_info "GitHubへのプッシュ..."
    git add .
    git commit -m "🚀 Deploy: $(date)" || true
    git push origin main

    # Railwayデプロイ
    log_info "Railwayデプロイ..."
    railway up

    echo
    log_info "✅ デプロイ完了！"
    echo
    log_info "📊 次のステップ:"
    log_info "1. Railwayダッシュボードでデプロイステータスを確認"
    log_info "2. 環境変数を設定:"
    log_info "   - LINE_CHANNEL_ACCESS_TOKEN"
    log_info "   - LINE_CHANNEL_SECRET"
    log_info "   - OPENAI_API_KEY"
    log_info "   - SECRET_KEY"
    log_info "3. RailwayのURLを取得してLINE Webhookを設定"
    echo
    log_info "🎉 Manual Bot AIのデプロイが完了しました！"
}

# ヘルプ表示
show_help() {
    echo "Manual Bot AI - 自動デプロイスクリプト"
    echo ""
    echo "使用方法:"
    echo "  ./deploy.sh          # デプロイ実行"
    echo "  ./deploy.sh check    # チェックのみ実行"
    echo "  ./deploy.sh help     # このヘルプ表示"
    echo ""
    echo "必要な環境:"
    echo "  - Git"
    echo "  - Python3"
    echo "  - Railway CLI (npm install -g @railway/cli)"
    echo "  - GitHubリポジトリ"
    echo ""
    echo "注意事項:"
    echo "  - 環境変数をハードコードしないこと"
    echo "  - Railwayにログイン済みであること"
    echo "  - GitHubにプッシュ権限があること"
}

# メイン処理
case "${1:-deploy}" in
    "deploy")
        deploy
        ;;
    "check")
        log_info "チェックモード実行..."
        check_environment
        check_dependencies
        security_check
        code_quality_check
        git_check
        railway_check
        log_info "✅ すべてのチェックが完了しました"
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        log_error "無効な引数: $1"
        show_help
        exit 1
        ;;
esac
