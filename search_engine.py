import re
import logging

class SimpleSearchEngine:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def search(self, query, documents_dict):
        """
        単純なキーワード検索
        
        Parameters:
        - query: 検索クエリ
        - documents_dict: {document_name: content} の辞書
        
        Returns:
        - 検索結果のリスト [{document, score, matches}]
        """
        results = []
        query_terms = self._tokenize(query)
        
        if not query_terms:
            return results
            
        for doc_name, content in documents_dict.items():
            if not content:
                continue
                
            score, matches = self._calculate_score(query_terms, content)
            
            if score > 0:
                results.append({
                    "document": doc_name,
                    "score": score,
                    "matches": matches[:5]  # 最大5件のマッチを返す
                })
        
        # スコアでソート
        results.sort(key=lambda x: x["score"], reverse=True)
        return results
    
    def _tokenize(self, text):
        """テキストをトークン化"""
        if not text:
            return []
        # 簡易的な日本語・英語のトークン化
        terms = re.findall(r'[一-龯ぁ-んァ-ヶa-zA-Z0-9]+', text)
        return [term.lower() for term in terms if term]
    
    def _calculate_score(self, query_terms, content):
        """スコアを計算"""
        score = 0
        matches = []
        content_lower = content.lower()
        
        for term in query_terms:
            count = content_lower.count(term.lower())
            if count > 0:
                score += count
                
                # マッチした部分の前後の文脈を抽出
                start_pos = max(0, content_lower.find(term.lower()) - 20)
                end_pos = min(len(content), content_lower.find(term.lower()) + len(term) + 20)
                context = content[start_pos:end_pos]
                matches.append(context)
        
        return score, matches
