import os
import logging
import requests
import json
from language_handler import LanguageHandler

class AIResponseGenerator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_key = os.environ.get('CORE_API_KEY')  # OpenAI APIキー
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.language_handler = LanguageHandler()
        
        if not self.api_key:
            self.logger.warning("OpenAI API key not set")
            self.enabled = False
        else:
            self.enabled = True
            self.logger.info("OpenAI API initialized with multilingual support")
    
    def generate_response(self, query, context_texts=None, max_tokens=300, language=None):
        """AI回答を生成（多言語対応）"""
        # 言語検出
        if not language:
            language = self.language_handler.detect_language(query)
        
        if not self.enabled:
            return self.language_handler.messages['ai_unavailable'][language].format(query=query)
        
        # コンテキストの準備
        context = ""
        if context_texts:
            context = "\n\n".join(context_texts[:3])  # 最大3つのコンテキスト
        
        # 言語別プロンプト取得
        system_prompt = self.language_handler.get_ai_prompt_by_language(language)
        
        # 言語別ユーザープロンプト
        user_prompts = {
            'ja': f"マニュアル情報:\n{context}\n\nお客様の質問: {query}\n\n上記のマニュアル情報を参考に、お客様の質問に丁寧にお答えください。",
            'en': f"Manual information:\n{context}\n\nCustomer question: {query}\n\nPlease answer the customer's question politely based on the manual information above.",
            'zh': f"手册信息:\n{context}\n\n客户问题: {query}\n\n请根据上述手册信息，礼貌地回答客户的问题。",
            'ko': f"매뉴얼 정보:\n{context}\n\n고객 질문: {query}\n\n위의 매뉴얼 정보를 참고하여 고객의 질문에 정중하게 답변해 주세요."
        }
        
        user_prompt = user_prompts.get(language, user_prompts['ja'])
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
            
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    ai_response = result["choices"][0]["message"]["content"].strip()
                    self.logger.info(f"AI response generated in {language}")
                    return ai_response
                else:
                    self.logger.error("No choices in OpenAI response")
                    return self._get_error_message(language, "generation_failed")
            else:
                self.logger.error(f"OpenAI API error: {response.status_code}")
                return self._get_error_message(language, "api_error")
                
        except requests.exceptions.Timeout:
            self.logger.error("OpenAI API timeout")
            return self._get_error_message(language, "timeout")
        except Exception as e:
            self.logger.error(f"Error generating AI response: {str(e)}")
            return self._get_error_message(language, "general_error")
    
    def _get_error_message(self, language, error_type):
        """エラーメッセージを言語別で取得"""
        error_messages = {
            'generation_failed': {
                'ja': '申し訳ございません。AI回答の生成に失敗しました。',
                'en': 'I apologize. Failed to generate AI response.',
                'zh': '很抱歉，AI回答生成失败。',
                'ko': '죄송합니다. AI 답변 생성에 실패했습니다.'
            },
            'api_error': {
                'ja': '申し訳ございません。AI回答の生成中にエラーが発生しました。',
                'en': 'I apologize. An error occurred during AI response generation.',
                'zh': '很抱歉，AI回答生成过程中发生错误。',
                'ko': '죄송합니다. AI 답변 생성 중 오류가 발생했습니다.'
            },
            'timeout': {
                'ja': '申し訳ございません。AI回答の生成がタイムアウトしました。',
                'en': 'I apologize. AI response generation timed out.',
                'zh': '很抱歉，AI回答生成超时。',
                'ko': '죄송합니다. AI 답변 생성이 타임아웃되었습니다.'
            },
            'general_error': {
                'ja': '申し訳ございません。AI回答の生成中にエラーが発生しました。',
                'en': 'I apologize. An error occurred during AI response generation.',
                'zh': '很抱歉，AI回答生成过程中发生错误。',
                'ko': '죄송합니다. AI 답변 생성 중 오류가 발생했습니다.'
            }
        }
        
        return error_messages.get(error_type, {}).get(language, error_messages[error_type]['ja'])
