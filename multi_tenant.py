"""
マルチテナント管理システム
企業ごとのデータ完全分離
"""

import sqlite3
import os
from datetime import datetime
from typing import Dict, List

class MultiTenantManager:
    def __init__(self, db_path='manual_bot.db'):
        self.db_path = db_path
        self._init_tenant_tables()
    
    def _get_connection(self):
        """データベース接続取得"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_tenant_tables(self):
        """テナント管理テーブル初期化"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # テナント（企業）テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tenants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                subdomain TEXT UNIQUE NOT NULL,
                admin_email TEXT NOT NULL,
                plan TEXT DEFAULT 'starter',
                status TEXT DEFAULT 'active',
                stripe_customer_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # テナント設定テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tenant_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NOT NULL,
                notification_channels TEXT DEFAULT 'email',
                storage_limit_gb INTEGER DEFAULT 10,
                monthly_message_limit INTEGER DEFAULT 100,
                auto_delete_months INTEGER DEFAULT 6,
                FOREIGN KEY (tenant_id) REFERENCES tenants (id)
            )
        ''')
        
        # テナント使用量テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tenant_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NOT NULL,
                month TEXT NOT NULL,
                files_uploaded INTEGER DEFAULT 0,
                storage_used_mb INTEGER DEFAULT 0,
                messages_sent INTEGER DEFAULT 0,
                api_calls_made INTEGER DEFAULT 0,
                total_cost REAL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tenant_id) REFERENCES tenants (id),
                UNIQUE(tenant_id, month)
            )
        ''')
        
        # usersテーブルにtenant_id追加（既存テーブル拡張）
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN tenant_id INTEGER')
        except sqlite3.OperationalError:
            pass  # 既に存在する場合
        
        # filesテーブルにtenant_id追加
        try:
            cursor.execute('ALTER TABLE files ADD COLUMN tenant_id INTEGER')
        except sqlite3.OperationalError:
            pass
        
        # conversationsテーブルにtenant_id追加
        try:
            cursor.execute('ALTER TABLE conversations ADD COLUMN tenant_id INTEGER')
        except sqlite3.OperationalError:
            pass
        
        conn.commit()
        conn.close()
    
    def create_tenant(self, company_name: str, admin_email: str, subdomain: str = None) -> int:
        """
        新規テナント（企業）作成
        
        Args:
            company_name: 企業名
            admin_email: 管理者メールアドレス
            subdomain: サブドメイン（省略時は自動生成）
        
        Returns:
            int: テナントID
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # サブドメイン生成（省略時）
        if not subdomain:
            subdomain = company_name.lower().replace(' ', '-').replace('株式会社', '').replace('(', '').replace(')', '')
        
        # テナント作成
        cursor.execute(
            'INSERT INTO tenants (company_name, admin_email, subdomain) VALUES (?, ?, ?)',
            (company_name, admin_email, subdomain)
        )
        
        tenant_id = cursor.lastrowid
        
        # デフォルト設定作成
        cursor.execute(
            'INSERT INTO tenant_settings (tenant_id) VALUES (?)',
            (tenant_id,)
        )
        
        conn.commit()
        conn.close()
        
        return tenant_id
    
    def get_tenant_by_subdomain(self, subdomain: str) -> Dict:
        """
        サブドメインからテナント情報取得
        
        Args:
            subdomain: サブドメイン
        
        Returns:
            dict: テナント情報
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM tenants WHERE subdomain = ?', (subdomain,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_tenant_settings(self, tenant_id: int) -> Dict:
        """
        テナント設定取得
        
        Args:
            tenant_id: テナントID
        
        Returns:
            dict: テナント設定
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM tenant_settings WHERE tenant_id = ?', (tenant_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return dict(row)
        return {}
    
    def update_tenant_settings(self, tenant_id: int, settings: Dict):
        """
        テナント設定更新
        
        Args:
            tenant_id: テナントID
            settings: 更新する設定（dict）
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 動的にUPDATE文を生成
        set_clause = ', '.join([f"{key} = ?" for key in settings.keys()])
        values = list(settings.values()) + [tenant_id]
        
        cursor.execute(
            f'UPDATE tenant_settings SET {set_clause} WHERE tenant_id = ?',
            values
        )
        
        conn.commit()
        conn.close()
    
    def track_tenant_usage(self, tenant_id: int, usage_type: str, amount: int = 1):
        """
        テナント使用量追跡
        
        Args:
            tenant_id: テナントID
            usage_type: 使用量タイプ（files_uploaded, messages_sent, etc.）
            amount: 増加量
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        current_month = datetime.now().strftime('%Y-%m')
        
        # 既存レコード確認
        cursor.execute(
            'SELECT id FROM tenant_usage WHERE tenant_id = ? AND month = ?',
            (tenant_id, current_month)
        )
        
        if cursor.fetchone():
            # 更新
            cursor.execute(
                f'UPDATE tenant_usage SET {usage_type} = {usage_type} + ?, updated_at = CURRENT_TIMESTAMP WHERE tenant_id = ? AND month = ?',
                (amount, tenant_id, current_month)
            )
        else:
            # 新規作成
            cursor.execute(
                f'INSERT INTO tenant_usage (tenant_id, month, {usage_type}) VALUES (?, ?, ?)',
                (tenant_id, current_month, amount)
            )
        
        conn.commit()
        conn.close()
    
    def get_tenant_usage(self, tenant_id: int, month: str = None) -> Dict:
        """
        テナント使用量取得
        
        Args:
            tenant_id: テナントID
            month: 月（YYYY-MM形式、省略時は当月）
        
        Returns:
            dict: 使用量情報
        """
        if not month:
            month = datetime.now().strftime('%Y-%m')
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT * FROM tenant_usage WHERE tenant_id = ? AND month = ?',
            (tenant_id, month)
        )
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return dict(row)
        return {
            'files_uploaded': 0,
            'storage_used_mb': 0,
            'messages_sent': 0,
            'api_calls_made': 0,
            'total_cost': 0
        }
    
    def check_usage_limits(self, tenant_id: int) -> Dict:
        """
        使用量制限チェック
        
        Args:
            tenant_id: テナントID
        
        Returns:
            dict: {
                'within_limits': bool,
                'exceeded': List[str],
                'usage': Dict,
                'limits': Dict
            }
        """
        settings = self.get_tenant_settings(tenant_id)
        usage = self.get_tenant_usage(tenant_id)
        
        exceeded = []
        
        # ストレージ制限チェック
        if usage['storage_used_mb'] / 1024 > settings.get('storage_limit_gb', 10):
            exceeded.append('storage')
        
        # メッセージ制限チェック
        if usage['messages_sent'] > settings.get('monthly_message_limit', 100):
            exceeded.append('messages')
        
        return {
            'within_limits': len(exceeded) == 0,
            'exceeded': exceeded,
            'usage': usage,
            'limits': settings
        }
    
    def list_all_tenants(self) -> List[Dict]:
        """
        全テナント一覧取得
        
        Returns:
            List[dict]: テナント情報リスト
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM tenants ORDER BY created_at DESC')
        rows = cursor.fetchall()
        
        conn.close()
        
        return [dict(row) for row in rows]

# 使用例
if __name__ == "__main__":
    manager = MultiTenantManager()
    
    # テナント作成
    tenant_id = manager.create_tenant(
        company_name="株式会社テスト",
        admin_email="admin@test.com",
        subdomain="test-company"
    )
    print(f"✅ テナント作成: ID={tenant_id}")
    
    # 使用量追跡
    manager.track_tenant_usage(tenant_id, 'files_uploaded', 1)
    manager.track_tenant_usage(tenant_id, 'messages_sent', 10)
    
    # 使用量確認
    usage = manager.get_tenant_usage(tenant_id)
    print(f"📊 使用量: {usage}")
    
    # 制限チェック
    check = manager.check_usage_limits(tenant_id)
    print(f"⚠️  制限内: {check['within_limits']}")


