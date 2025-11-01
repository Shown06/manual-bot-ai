import re
from typing import Dict, Tuple

class LanguageHandler:
    """多言語対応ハンドラー"""
    
    def __init__(self):
        self.translations = {
            'ja': {
                'greeting': 'お問い合わせありがとうございます。',
                'not_found': '申し訳ございません。お問い合わせの内容について、マニュアルに該当する情報が見つかりませんでした。',
                'error': '申し訳ございません。エラーが発生しました。',
                'contact': 'フロント（内線0）までお問い合わせください。',
                'registration_required': 'このBotを利用するには、Webサイトでの登録が必要です。',
                'link_start': 'LINE連携を開始します。',
                'link_complete': '連携が完了しました！Manual Bot AIをご利用いただけます。',
                'manual_found': '以下の情報が見つかりました：'
            },
            'en': {
                'greeting': 'Thank you for your inquiry.',
                'not_found': 'Sorry, we could not find any information about your inquiry in the manual.',
                'error': 'Sorry, an error has occurred.',
                'contact': 'Please contact the front desk (ext. 0).',
                'registration_required': 'Registration on the website is required to use this Bot.',
                'link_start': 'Starting LINE integration.',
                'link_complete': 'Integration complete! You can now use Manual Bot AI.',
                'manual_found': 'The following information was found:'
            },
            'zh': {
                'greeting': '感谢您的咨询。',
                'not_found': '抱歉，在手册中找不到有关您咨询的信息。',
                'error': '抱歉，发生了错误。',
                'contact': '请联系前台（分机0）。',
                'registration_required': '使用此Bot需要在网站上注册。',
                'link_start': '开始LINE连接。',
                'link_complete': '连接完成！您现在可以使用Manual Bot AI。',
                'manual_found': '找到以下信息：'
            }
        }
    
    def detect_language(self, text: str) -> str:
        """言語を自動検出"""
        # 日本語パターン
        if re.search(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]', text):
            # 中国語の可能性もチェック
            if re.search(r'[你好谢请什么哪里怎么吗呢的了着过]', text):
                return 'zh'
            return 'ja'
        
        # 中国語パターン
        elif re.search(r'[\u4e00-\u9fff]', text):
            return 'zh'
        
        # 英語（デフォルト）
        else:
            return 'en'
    
    def get_message(self, key: str, lang: str = 'ja') -> str:
        """メッセージを取得"""
        return self.translations.get(lang, self.translations['ja']).get(key, key)
    
    def translate_response(self, response: str, target_lang: str) -> str:
        """応答を翻訳（簡易版）"""
        if target_lang == 'ja':
            return response
        
        # 簡易的な翻訳マッピング
        translations = {
            'en': {
                'チェックイン': 'check-in',
                '時間': 'time',
                'から': 'from',
                'まで': 'until',
                'フロント': 'front desk',
                '朝食': 'breakfast',
                '夕食': 'dinner',
                'レストラン': 'restaurant',
                '営業': 'open',
                'パスワード': 'password'
            },
            'zh': {
                'チェックイン': '入住',
                '時間': '时间',
                'から': '从',
                'まで': '到',
                'フロント': '前台',
                '朝食': '早餐',
                '夕食': '晚餐',
                'レストラン': '餐厅',
                '営業': '营业',
                'パスワード': '密码'
            }
        }
        
        result = response
        if target_lang in translations:
            for ja_word, translated in translations[target_lang].items():
                result = result.replace(ja_word, translated)
        
        return result
