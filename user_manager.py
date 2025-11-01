import hashlib
import secrets
import time
from datetime import datetime, timedelta
import json
import requests

class UserManager:
    def __init__(self):
        # 固定ユーザーのみ初期化
        self.users = {
            "demo_user": {
                "password": self._hash_password("demo123"),
                "company_name": "デモ企業株式会社",
                "plan": "premium",
                "permissions": ["upload", "delete", "view_all", "admin"],
                "created_at": "2024-01-01",
                "expires_at": "2025-12-31",
                "max_manuals": 100,
                "max_groups": 20
            },
            "trial_user": {
                "password": self._hash_password("trial123"),
                "company_name": "トライアル会社",
                "plan": "trial",
                "permissions": ["upload", "view_all"],
                "created_at": datetime.now().strftime("%Y-%m-%d"),
                "expires_at": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
                "max_manuals": 5,
                "max_groups": 2
            }
        }
        
        self.sessions = {}
        self.payment_system_url = "https://payment-system-1044399895607.asia-northeast1.run.app"
    
    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def get_dynamic_customers(self):
        try:
            response = requests.get(f"{self.payment_system_url}/api/customers", timeout=3)
            return response.json() if response.status_code == 200 else []
        except:
            return []
    
    def authenticate(self, user_id, password):
        # 固定ユーザー確認
        if user_id in self.users:
            user = self.users[user_id]
            if user["password"] != self._hash_password(password):
                return False
            expires_at = datetime.strptime(user["expires_at"], "%Y-%m-%d")
            return datetime.now() <= expires_at
        
        # 動的顧客確認
        customers = self.get_dynamic_customers()
        for customer in customers:
            if customer.get("user_id") == user_id and customer.get("password") == password:
                try:
                    created_at = datetime.fromisoformat(customer["created_at"].replace('Z', '+00:00'))
                    return datetime.now() <= created_at + timedelta(days=7)
                except:
                    return True
        
        return False
    
    def get_user_info(self, user_id):
        if user_id in self.users:
            return self.users[user_id]
        
        customers = self.get_dynamic_customers()
        for customer in customers:
            if customer.get("user_id") == user_id:
                return {
                    "company_name": customer.get("company_name", ""),
                    "plan": "trial",
                    "permissions": ["upload", "view_all"],
                    "created_at": customer.get("created_at", ""),
                    "expires_at": "",
                    "max_manuals": 5,
                    "max_groups": 2
                }
        
        return {"company_name": "Unknown", "plan": "trial"}
    
    def get_user_stats(self, user_id):
        user_info = self.get_user_info(user_id)
        
        if user_info["plan"] == "premium":
            return {"plan": "Premium", "max_manuals": 100, "max_groups": 20}
        elif user_info["plan"] == "standard":
            return {"plan": "Standard", "max_manuals": 20, "max_groups": 5}
        else:
            return {"plan": "Trial", "max_manuals": 5, "max_groups": 2}
    
    def check_permission(self, user_id, permission):
        user_info = self.get_user_info(user_id)
        permissions = user_info.get("permissions", ["upload", "view_all"])
        return permission in permissions
    
    def create_session(self, user_id):
        session_token = secrets.token_urlsafe(32)
        self.sessions[session_token] = {
            "user_id": user_id,
            "expires_at": time.time() + (24 * 60 * 60),
            "created_at": time.time()
        }
        return session_token
    
    def validate_session(self, session_token):
        if session_token not in self.sessions:
            return None
        
        session = self.sessions[session_token]
        if time.time() > session["expires_at"]:
            del self.sessions[session_token]
            return None
        
        return session["user_id"]
