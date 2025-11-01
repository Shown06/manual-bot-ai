
import os
from google.cloud import firestore
from functools import wraps
import sqlite3
from datetime import datetime

class DatabaseManager:
    """ハイブリッドデータベース管理（SQLite/Firestore）"""
    
    def __init__(self):
        self.use_firestore = os.environ.get('USE_FIRESTORE', 'false').lower() == 'true'
        
        if self.use_firestore:
            try:
                self.db = firestore.Client()
                print("✅ Firestore接続成功")
            except Exception as e:
                print(f"⚠️ Firestore接続失敗、SQLiteにフォールバック: {e}")
                self.use_firestore = False
                self._init_sqlite()
        else:
            self._init_sqlite()
    
    def _init_sqlite(self):
        """SQLite初期化"""
        # Cloud Runでも永続化できるパス
        self.db_path = os.environ.get('DATABASE_PATH', '/tmp/manual_bot.db')
        
        # 初期テーブル作成
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # ユーザーテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        ''')
        
        # ファイルテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER,
                upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # 会話履歴テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                line_user_id TEXT NOT NULL,
                message_type TEXT NOT NULL,
                message_content TEXT,
                ai_response TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"✅ SQLite初期化完了: {self.db_path}")
    
    def get_user(self, user_id=None, email=None, line_user_id=None):
        """ユーザー取得"""
        if self.use_firestore:
            query = self.db.collection('users')
            if user_id:
                doc = query.document(str(user_id)).get()
                return doc.to_dict() if doc.exists else None
            elif email:
                docs = query.where('email', '==', email).limit(1).get()
                return docs[0].to_dict() if docs else None
            elif line_user_id:
                docs = query.where('line_user_id', '==', line_user_id).limit(1).get()
                return docs[0].to_dict() if docs else None
        else:
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
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        if self.use_firestore:
            doc_ref = self.db.collection('users').document()
            user_data['id'] = doc_ref.id
            doc_ref.set(user_data)
            return doc_ref.id
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
        kwargs['updated_at'] = datetime.now()
        
        if self.use_firestore:
            self.db.collection('users').document(str(user_id)).update(kwargs)
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values()) + [user_id]
            
            cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
            conn.commit()
            conn.close()
    
    def migrate_to_firestore(self):
        """SQLiteからFirestoreへ移行"""
        if self.use_firestore:
            return "Already using Firestore"
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Firestoreクライアント作成
        fs_client = firestore.Client()
        
        # ユーザー移行
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        for user in users:
            doc_ref = fs_client.collection('users').document(str(user['id']))
            doc_ref.set(dict(user))
        
        # ファイル移行
        try:
            cursor.execute("SELECT * FROM files")
            files = cursor.fetchall()
            for file in files:
                doc_ref = fs_client.collection('files').document(str(file['id']))
                doc_ref.set(dict(file))
        except:
            pass
        
        # 会話履歴移行
        try:
            cursor.execute("SELECT * FROM conversations")
            conversations = cursor.fetchall()
            for conv in conversations:
                doc_ref = fs_client.collection('conversations').document(str(conv['id']))
                doc_ref.set(dict(conv))
        except:
            pass
        
        conn.close()
        
        return f"✅ 移行完了: {len(users)}ユーザー"

# グローバルインスタンス
db_manager = DatabaseManager()
