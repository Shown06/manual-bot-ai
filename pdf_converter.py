"""
PDF変換エンジン（Doclingから移植）
OpenAI GPT-4o Visionを使用した高精度PDF変換
"""

import openai
import base64
from pdf2image import convert_from_path
import io
import os
from dotenv import load_dotenv
from pathlib import Path
import time

load_dotenv()

class PDFConverter:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY_DOCLING") or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI APIキーが設定されていません")
        
        self.client = openai.OpenAI(api_key=self.api_key)
    
    def convert_to_markdown(self, pdf_path, dpi=200):
        """
        PDFをMarkdownに変換
        
        Args:
            pdf_path: PDFファイルのパス
            dpi: 画像解像度（デフォルト: 200）
        
        Returns:
            dict: {
                'markdown': 変換されたMarkdown,
                'pages': ページ数,
                'cost': 推定コスト
            }
        """
        try:
            # PDFを画像に変換
            images = convert_from_path(pdf_path, dpi=dpi)
            
            markdown_result = ""
            total_cost = 0
            
            for page_num, image in enumerate(images, 1):
                # 画像をBase64エンコード
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                # OpenAI API呼び出し
                prompt = """このページをMarkdown形式に変換してください。

【重要な要件】
1. テーブルは必ず正確に再現（列の区切りを明確に）
2. 数字・日付・金額は一字一句正確に
3. 見出しは ## を使用
4. 箇条書きは - を使用
5. 数式がある場合は $$数式$$ 形式

出力はMarkdownのみ。説明不要。"""
                
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
                        ]
                    }],
                    max_tokens=4096
                )
                
                page_markdown = response.choices[0].message.content
                markdown_result += f"## ページ {page_num}\n\n{page_markdown}\n\n---\n\n"
                
                # コスト計算
                cost = (response.usage.prompt_tokens / 1_000_000 * 2.5) + \
                       (response.usage.completion_tokens / 1_000_000 * 10)
                total_cost += cost
            
            return {
                'markdown': markdown_result,
                'pages': len(images),
                'cost': round(total_cost, 4)
            }
        
        except Exception as e:
            raise Exception(f"PDF変換エラー: {str(e)}")
    
    def convert_and_save(self, pdf_path, output_path=None):
        """
        PDFを変換してファイルに保存
        
        Args:
            pdf_path: PDFファイルのパス
            output_path: 出力先（省略時は同名.md）
        
        Returns:
            dict: 変換結果
        """
        result = self.convert_to_markdown(pdf_path)
        
        if output_path is None:
            output_path = Path(pdf_path).with_suffix('.md')
        
        Path(output_path).write_text(result['markdown'], encoding='utf-8')
        result['output_path'] = str(output_path)
        
        return result

# 使用例
if __name__ == "__main__":
    converter = PDFConverter()
    result = converter.convert_and_save("test.pdf")
    print(f"✅ 変換完了: {result['pages']}ページ, コスト: ${result['cost']}")


