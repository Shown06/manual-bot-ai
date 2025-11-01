"""
RAGシステム（Retrieval-Augmented Generation）
Chromaを使用したベクトルDB + OpenAI Embeddings
"""

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
import openai
import os
from dotenv import load_dotenv
from typing import List, Dict
import sqlite3

load_dotenv()

class RAGSystem:
    def __init__(self, user_id, persist_directory="./chroma_db"):
        """
        RAGシステム初期化
        
        Args:
            user_id: ユーザーID（マルチテナント対応）
            persist_directory: Chroma DBの保存先
        """
        self.user_id = user_id
        self.persist_directory = f"{persist_directory}/user_{user_id}"
        
        # OpenAI Embeddings
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.getenv("OPENAI_API_KEY_DOCLING") or os.getenv("OPENAI_API_KEY")
        )
        
        # Chroma ベクトルDB
        self.vectorstore = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings
        )
        
        # テキスト分割
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", "。", "、", " "]
        )
        
        # OpenAI クライアント
        self.client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY_DOCLING") or os.getenv("OPENAI_API_KEY")
        )
    
    def add_document(self, markdown_text: str, metadata: Dict):
        """
        ドキュメントをRAGシステムに追加
        
        Args:
            markdown_text: Markdown形式のテキスト
            metadata: メタデータ（filename, file_id, etc.）
        
        Returns:
            int: 追加されたチャンク数
        """
        # チャンク分割
        chunks = self.text_splitter.split_text(markdown_text)
        
        # Document オブジェクト作成
        documents = [
            Document(
                page_content=chunk,
                metadata={
                    **metadata,
                    "user_id": self.user_id,
                    "chunk_index": i
                }
            )
            for i, chunk in enumerate(chunks)
        ]
        
        # ベクトルDBに保存
        self.vectorstore.add_documents(documents)
        self.vectorstore.persist()
        
        return len(chunks)
    
    def search(self, query: str, top_k: int = 5) -> List[Document]:
        """
        類似検索
        
        Args:
            query: 検索クエリ
            top_k: 取得する結果数
        
        Returns:
            List[Document]: 類似ドキュメント
        """
        # ユーザーIDでフィルタリング
        results = self.vectorstore.similarity_search(
            query,
            k=top_k,
            filter={"user_id": self.user_id}
        )
        
        return results
    
    def qa(self, question: str, top_k: int = 5) -> Dict:
        """
        質疑応答
        
        Args:
            question: 質問
            top_k: 検索する関連ドキュメント数
        
        Returns:
            dict: {
                'answer': 回答,
                'sources': ソース情報,
                'cost': コスト
            }
        """
        # 関連ドキュメント検索
        docs = self.search(question, top_k=top_k)
        
        if not docs:
            return {
                "answer": "関連する情報が見つかりませんでした。",
                "sources": [],
                "cost": 0
            }
        
        # コンテキスト作成
        context = "\n\n".join([
            f"[ドキュメント {i+1}]\n"
            f"ファイル名: {doc.metadata.get('filename', '不明')}\n"
            f"内容:\n{doc.page_content}"
            for i, doc in enumerate(docs)
        ])
        
        # GPT-4oで回答生成
        prompt = f"""以下の情報を元に質問に答えてください。

【コンテキスト】
{context}

【質問】
{question}

【回答形式】
1. 質問に対する明確な回答
2. 回答の根拠となるドキュメント名
3. 該当箇所の引用（簡潔に）

回答は簡潔に、正確に。"""
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024
        )
        
        answer = response.choices[0].message.content
        
        # コスト計算
        cost = (response.usage.prompt_tokens / 1_000_000 * 2.5) + \
               (response.usage.completion_tokens / 1_000_000 * 10)
        
        # ソース情報
        sources = [
            {
                "filename": doc.metadata.get('filename', '不明'),
                "chunk": doc.page_content[:100] + "..."
            }
            for doc in docs
        ]
        
        return {
            "answer": answer,
            "sources": sources,
            "cost": round(cost, 4)
        }
    
    def get_all_documents(self) -> List[str]:
        """
        登録されている全ドキュメントのファイル名を取得
        """
        # Chromaから全メタデータを取得
        all_docs = self.vectorstore.get()
        
        if not all_docs or 'metadatas' not in all_docs:
            return []
        
        # ユニークなファイル名を抽出
        filenames = set()
        for metadata in all_docs['metadatas']:
            if metadata.get('user_id') == self.user_id:
                filename = metadata.get('filename')
                if filename:
                    filenames.add(filename)
        
        return sorted(list(filenames))
    
    def delete_document(self, filename: str):
        """
        特定のドキュメントを削除
        
        Args:
            filename: 削除するファイル名
        """
        # Chromaから該当ドキュメントを削除
        all_docs = self.vectorstore.get()
        
        if not all_docs or 'ids' not in all_docs:
            return
        
        ids_to_delete = []
        for i, metadata in enumerate(all_docs['metadatas']):
            if metadata.get('user_id') == self.user_id and metadata.get('filename') == filename:
                ids_to_delete.append(all_docs['ids'][i])
        
        if ids_to_delete:
            self.vectorstore.delete(ids=ids_to_delete)
            self.vectorstore.persist()

# 使用例
if __name__ == "__main__":
    rag = RAGSystem(user_id=1)
    
    # ドキュメント追加
    markdown = "# テスト文書\n\n営業時間: 9:00-18:00"
    chunks = rag.add_document(
        markdown_text=markdown,
        metadata={"filename": "test.pdf", "file_id": 1}
    )
    print(f"✅ {chunks}チャンク追加")
    
    # 質疑応答
    result = rag.qa("営業時間は？")
    print(f"💬 回答: {result['answer']}")
    print(f"💰 コスト: ${result['cost']}")


