import os
import logging
import hashlib
import hmac
import base64
import json
import requests
from language_handler import LanguageHandler

class LineBotHandler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.channel_access_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
        self.channel_secret = os.environ.get('LINE_CHANNEL_SECRET')
        self.language_handler = LanguageHandler()
        
        if not self.channel_access_token or not self.channel_secret:
            self.logger.warning("LINE credentials not set")
            self.enabled = False
        else:
            self.enabled = True
            self.logger.info("LINE Bot handler initialized with multilingual support")
    
    def verify_signature(self, body, signature):
        """LINE Webhook署名検証"""
        if not self.enabled:
            return True  # 開発環境では署名検証をスキップ
            
        if not signature:
            return False
            
        hash_value = hmac.new(
            self.channel_secret.encode('utf-8'),
            body.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        expected_signature = base64.b64encode(hash_value).decode('utf-8')
        return hmac.compare_digest(signature, expected_signature)
    
    def handle_message(self, message_text, user_id):
        """メッセージ処理（多言語対応）"""
        self.logger.info(f"Message from {user_id}: {message_text}")
        
        # 言語検出
        language = self.language_handler.detect_language(message_text)
        self.logger.info(f"Detected language: {language}")
        
        # キーワードベース応答
        response_text = self.language_handler.get_response_by_keywords(message_text, language)
        
        return response_text
    
    def send_reply(self, reply_token, message_text):
        """返信送信"""
        if not self.enabled:
            self.logger.info(f"Reply would be sent: {message_text}")
            return
            
        url = "https://api.line.me/v2/bot/message/reply"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.channel_access_token}"
        }
        
        data = {
            "replyToken": reply_token,
            "messages": [
                {
                    "type": "text",
                    "text": message_text
                }
            ]
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                self.logger.info("Reply sent successfully")
            else:
                self.logger.error(f"Failed to send reply: {response.status_code}")
        except Exception as e:
            self.logger.error(f"Error sending reply: {str(e)}")
    
    def send_multilingual_welcome(self, reply_token):
        """多言語ウェルカムメッセージ送信"""
        if not self.enabled:
            return
            
        welcome_messages = [
            "🇯🇵 こんにちは！カプセルホテル朝日プラザのマニュアル検索ボットです。",
            "🇺🇸 Hello! Welcome to Capsule Hotel Asahi Plaza manual search bot.",
            "🇨🇳 您好！欢迎使用朝日广场胶囊酒店手册搜索机器人。",
            "🇰🇷 안녕하세요! 아사히 플라자 캡슐 호텔 매뉴얼 검색 봇입니다."
        ]
        
        url = "https://api.line.me/v2/bot/message/reply"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.channel_access_token}"
        }
        
        messages = []
        for msg in welcome_messages:
            messages.append({"type": "text", "text": msg})
        
        data = {
            "replyToken": reply_token,
            "messages": messages
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                self.logger.info("Multilingual welcome sent successfully")
            else:
                self.logger.error(f"Failed to send welcome: {response.status_code}")
        except Exception as e:
            self.logger.error(f"Error sending welcome: {str(e)}")
