import re
from typing import List, Tuple, Dict
import logging

logger = logging.getLogger(__name__)

class SimpleSearch:
    """シンプルな全文検索エンジン"""
    
    def __init__(self):
        self.documents = {}
        self.index = {}
        
    def add_document(self, doc_id: str, content: str):
        """ドキュメントを追加"""
        self.documents[doc_id] = content
        
        # 単語分割してインデックス作成
        words = self._tokenize(content)
        for word in words:
            if word not in self.index:
                self.index[word] = []
            if doc_id not in self.index[word]:
                self.index[word].append(doc_id)
    
    def search(self, query: str, limit: int = 5) -> List[Tuple[str, str, float]]:
        """検索実行"""
        query_words = self._tokenize(query)
        scores = {}
        
        for word in query_words:
            if word in self.index:
                for doc_id in self.index[word]:
                    if doc_id not in scores:
                        scores[doc_id] = 0
                    scores[doc_id] += 1
        
        # スコア順にソート
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        results = []
        for doc_id, score in sorted_docs:
            content = self.documents[doc_id]
            # 関連部分を抽出
            excerpt = self._extract_excerpt(content, query)
            results.append((doc_id, excerpt, score))
        
        return results
    
    def _tokenize(self, text: str) -> List[str]:
        """テキストをトークン化"""
        # 日本語対応の簡易トークナイザー
        text = text.lower()
        # 単語境界で分割（英数字と日本語文字）
        words = re.findall(r'\b\w+\b|[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]+', text)
        return [w for w in words if len(w) > 1]
    
    def _extract_excerpt(self, content: str, query: str, context_length: int = 100) -> str:
        """クエリ周辺のテキストを抽出"""
        query_lower = query.lower()
        content_lower = content.lower()
        
        pos = content_lower.find(query_lower)
        if pos == -1:
            # クエリの単語で検索
            for word in self._tokenize(query):
                pos = content_lower.find(word)
                if pos != -1:
                    break
        
        if pos == -1:
            return content[:200] + "..." if len(content) > 200 else content
        
        start = max(0, pos - context_length)
        end = min(len(content), pos + len(query) + context_length)
        
        excerpt = content[start:end]
        if start > 0:
            excerpt = "..." + excerpt
        if end < len(content):
            excerpt = excerpt + "..."
        
        return excerpt
    
    def get_all_documents(self) -> Dict[str, str]:
        """全ドキュメントを取得"""
        return self.documents.copy()
    
    def clear(self):
        """インデックスをクリア"""
        self.documents.clear()
        self.index.clear()
