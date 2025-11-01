import logging
from typing import List, Tuple, Dict, Any

logger = logging.getLogger(__name__)

class SafeCustomerBot:
    """安全な顧客対応ボット"""
    
    def __init__(self):
        try:
            from simple_search import SimpleSearch
            self.search_engine = SimpleSearch()
        except ImportError:
            # フォールバック用の簡易検索エンジン
            class SimpleSearchFallback:
                def __init__(self):
                    self.documents = {}
                def add_document(self, doc_id, content):
                    self.documents[doc_id] = content
                def search(self, query, limit=5):
                    results = []
                    for doc_id, content in self.documents.items():
                        if query.lower() in content.lower():
                            results.append((doc_id, content[:200], 1.0))
                    return results[:limit]
            self.search_engine = SimpleSearchFallback()
            
        self.emergency_keywords = [
            '緊急', '急ぎ', '至急', '大至急', 'すぐに', '今すぐ',
            '事故', '怪我', 'ケガ', '病気', '体調不良', '救急',
            '火事', '地震', '災害', '停電', '断水'
        ]
        
        self.polite_phrases = {
            'greeting': 'お問い合わせありがとうございます。',
            'found': '以下の情報が見つかりました：\n\n',
            'not_found': '申し訳ございません。お問い合わせの内容について、マニュアルに該当する情報が見つかりませんでした。',
            'emergency': '緊急のご用件のようです。すぐに担当者にお繋ぎいたします。',
            'contact': '\n\n詳細については、フロント（内線0）までお問い合わせください。',
            'wait': '\n\nただいま確認いたしますので、少々お待ちください。'
        }
    
    def safe_response(self, user_message: str) -> str:
        """安全な応答を生成"""
        try:
            # 緊急チェック
            if self.is_emergency(user_message):
                return self._emergency_response()
            
            # 検索実行
            results = self.search_engine.search(user_message, limit=3)
            
            if results:
                return self._found_response(results)
            else:
                return self._not_found_response()
                
        except Exception as e:
            logger.error(f"応答生成エラー: {e}")
            return self._error_response()
    
    def is_emergency(self, message: str) -> bool:
        """緊急メッセージかチェック"""
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in self.emergency_keywords)
    
    def _found_response(self, results: List[Tuple[str, str, float]]) -> str:
        """検索結果がある場合の応答"""
        response = self.polite_phrases['greeting'] + self.polite_phrases['found']
        
        for i, (doc_id, excerpt, score) in enumerate(results[:2]):
            response += f"{excerpt}\n\n"
        
        if len(results) > 2:
            response += "その他の関連情報もございます。"
        
        response += self.polite_phrases['contact']
        return response
    
    def _not_found_response(self) -> str:
        """検索結果がない場合の応答"""
        return (
            self.polite_phrases['greeting'] + 
            self.polite_phrases['not_found'] + 
            self.polite_phrases['wait'] +
            self.polite_phrases['contact']
        )
    
    def _emergency_response(self) -> str:
        """緊急時の応答"""
        return (
            self.polite_phrases['emergency'] + 
            "\n\nフロント直通: 内線0" +
            "\n緊急連絡先: 000-0000-0000"
        )
    
    def _error_response(self) -> str:
        """エラー時の応答"""
        return (
            "申し訳ございません。システムエラーが発生しました。" +
            self.polite_phrases['contact']
        )
    
    def filter_response(self, response: str) -> str:
        """AI応答をフィルタリングして安全な応答に変換"""
        try:
            # 不適切な内容をチェック
            inappropriate_keywords = ['死', '殺', '暴力', '違法']
            
            response_lower = response.lower()
            if any(keyword in response_lower for keyword in inappropriate_keywords):
                logger.warning(f"Inappropriate content detected, using safe response")
                return self._not_found_response()
            
            # 応答が空または短すぎる場合
            if not response or len(response.strip()) < 5:
                return self._not_found_response()
            
            # 丁寧な挨拶を追加
            if not response.startswith(('お', 'ご', 'こんにちは', 'ありがとう')):
                response = self.polite_phrases['greeting'] + "\n\n" + response
            
            return response
            
        except Exception as e:
            logger.error(f"Response filtering error: {e}")
            return response  # エラー時は元の応答を返す