from supabase import create_client

SUPABASE_URL = "https://fsbakbrllarivbqcrbyj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZzYmFrYnJsbGFyaXZicWNyYnlqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ2MzUxNjIsImV4cCI6MjA3MDIxMTE2Mn0.7GfvlJjJUY48U-VP1LvBG1lxNrvKMvF9n_9QtiXBrQ0"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("🔍 Supabaseテーブル確認中...")

tables = ['users', 'files', 'conversations', 'usage_tracking']
for table in tables:
    try:
        result = supabase.table(table).select("*").limit(1).execute()
        print(f"✅ {table}テーブル: 正常")
    except Exception as e:
        print(f"❌ {table}テーブル: {str(e)[:50]}...")

print("\n🎯 テスト用ユーザー作成...")
try:
    test_user = {
        'username': 'test_user_001',
        'email': 'test@example.com',
        'password_hash': 'dummy_hash',
        'plan': 'starter'
    }
    result = supabase.table('users').insert(test_user).execute()
    if result.data:
        print(f"✅ テストユーザー作成成功: ID {result.data[0]['id']}")
        
        # 作成したテストユーザーを削除
        supabase.table('users').delete().eq('email', 'test@example.com').execute()
        print("✅ テストユーザー削除完了")
    else:
        print("❌ テストユーザー作成失敗")
except Exception as e:
    print(f"❌ エラー: {e}")

print("\n🚀 Supabase準備完了！")
