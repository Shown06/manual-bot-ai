#!/usr/bin/env python3
"""
Supabase移行スクリプト - SQLiteからSupabaseへ
"""
import os
import sqlite3
from datetime import datetime

print("🚀 Supabase セットアップ")

# Supabase接続設定
supabase_config = '''
import os
from supabase import create_client, Client
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any

class SupabaseManager:
    """Supabaseデータベース管理"""
    
    def __init__(self):
        # Supabase設定（環境変数から取得）
        self.supabase_url = os.environ.get('SUPABASE_URL', '')
        self.supabase_key = os.environ.get('SUPABASE_ANON_KEY', '')
        
        if self.supabase_url and self.supabase_key:
            try:
                self.client: Client = create_client(self.supabase_url, self.supabase_key)
                print("✅ Supabase接続成功")
                self.use_supabase = True
            except Exception as e:
                print(f"⚠️ Supabase接続失敗: {e}")
                self.use_supabase = False
                self._init_sqlite()
        else:
            print("⚠️ Supabase設定がありません。SQLiteを使用します。")
            self.use_supabase = False
            self._init_sqlite()
    
    def _init_sqlite(self):
        """SQLiteフォールバック"""
        self.db_path = os.environ.get('DATABASE_PATH', '/tmp/manual_bot.db')
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 既存のテーブル作成コード（省略）
        cursor.execute(\'\'\'
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                line_user_id TEXT UNIQUE,
                plan TEXT DEFAULT 'starter',
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        \'\'\')
        conn.commit()
        conn.close()
    
    def get_user(self, user_id=None, email=None, line_user_id=None) -> Optional[Dict[str, Any]]:
        """ユーザー取得"""
        if self.use_supabase:
            try:
                if user_id:
                    response = self.client.table('users').select("*").eq('id', user_id).single().execute()
                elif email:
                    response = self.client.table('users').select("*").eq('email', email).single().execute()
                elif line_user_id:
                    response = self.client.table('users').select("*").eq('line_user_id', line_user_id).single().execute()
                else:
                    return None
                
                return response.data if response.data else None
            except:
                return None
        else:
            # SQLiteフォールバック
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if user_id:
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            elif email:
                cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            elif line_user_id:
                cursor.execute("SELECT * FROM users WHERE line_user_id = ?", (line_user_id,))
            
            user = cursor.fetchone()
            conn.close()
            return dict(user) if user else None
    
    def create_user(self, username, email, password_hash, line_user_id=None):
        """ユーザー作成"""
        user_data = {
            'username': username,
            'email': email,
            'password_hash': password_hash,
            'line_user_id': line_user_id,
            'plan': 'starter',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        if self.use_supabase:
            response = self.client.table('users').insert(user_data).execute()
            return response.data[0]['id'] if response.data else None
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, line_user_id)
                VALUES (?, ?, ?, ?)
            """, (username, email, password_hash, line_user_id))
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return user_id
    
    def update_user(self, user_id, **kwargs):
        """ユーザー更新"""
        kwargs['updated_at'] = datetime.now().isoformat()
        
        if self.use_supabase:
            self.client.table('users').update(kwargs).eq('id', user_id).execute()
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values()) + [user_id]
            
            cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
            conn.commit()
            conn.close()
    
    def migrate_to_supabase(self):
        """SQLiteからSupabaseへ移行"""
        if not self.use_supabase:
            return "Supabase設定が必要です"
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # ユーザー移行
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        
        for user in users:
            user_dict = dict(user)
            # datetimeを文字列に変換
            if user_dict.get('created_at'):
                user_dict['created_at'] = str(user_dict['created_at'])
            if user_dict.get('updated_at'):
                user_dict['updated_at'] = str(user_dict['updated_at'])
            
            try:
                self.client.table('users').upsert(user_dict).execute()
            except Exception as e:
                print(f"ユーザー移行エラー: {e}")
        
        conn.close()
        return f"✅ 移行完了: {len(users)}ユーザー"

# グローバルインスタンス
db = SupabaseManager()
'''

with open('supabase_manager.py', 'w') as f:
    f.write(supabase_config)

print("✅ supabase_manager.py作成完了")

# Supabaseのテーブル作成SQL
sql_schema = '''
-- Supabaseで実行するSQL

-- ユーザーテーブル
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    line_user_id TEXT UNIQUE,
    plan TEXT DEFAULT 'starter',
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ファイルテーブル
CREATE TABLE IF NOT EXISTS files (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size INTEGER,
    upload_timestamp TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- 会話履歴テーブル
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    line_user_id TEXT NOT NULL,
    message_type TEXT NOT NULL,
    message_content TEXT,
    ai_response TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- インデックス
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_line_user_id ON users(line_user_id);
CREATE INDEX idx_files_user_id ON files(user_id);
CREATE INDEX idx_conversations_user_id ON conversations(user_id);

-- Row Level Security (RLS)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE files ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
'''

with open('supabase_schema.sql', 'w') as f:
    f.write(sql_schema)

print("✅ supabase_schema.sql作成完了")

print("""
📋 次のステップ:

1. Supabaseプロジェクト作成:
   https://app.supabase.com でプロジェクト作成

2. SQL実行:
   Supabase Dashboard > SQL Editor で supabase_schema.sql を実行

3. 環境変数取得:
   Settings > API から:
   - Project URL → SUPABASE_URL
   - anon public key → SUPABASE_ANON_KEY

4. 環境変数設定:
   gcloud run services update line-manual-api \\
     --region asia-northeast1 \\
     --update-env-vars "SUPABASE_URL=your-url,SUPABASE_ANON_KEY=your-key"
""")

