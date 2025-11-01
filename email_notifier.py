"""
メール通知システム
SMTP経由で企業メールを送信
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class EmailNotifier:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        
        if not self.smtp_user or not self.smtp_password:
            print("⚠️ SMTP設定が不完全です。メール通知は無効です。")
            self.enabled = False
        else:
            self.enabled = True
    
    def send_email(self, to_email: str, subject: str, body: str, html_body: str = None):
        """
        メール送信
        
        Args:
            to_email: 送信先メールアドレス
            subject: 件名
            body: 本文（テキスト）
            html_body: 本文（HTML、オプション）
        
        Returns:
            bool: 送信成功/失敗
        """
        if not self.enabled:
            print("⚠️ メール通知が無効です")
            return False
        
        try:
            # メッセージ作成
            msg = MIMEMultipart('alternative')
            msg['From'] = self.smtp_user
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # テキスト部分
            text_part = MIMEText(body, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # HTML部分（オプション）
            if html_body:
                html_part = MIMEText(html_body, 'html', 'utf-8')
                msg.attach(html_part)
            
            # SMTP接続・送信
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            print(f"✅ メール送信成功: {to_email}")
            return True
        
        except Exception as e:
            print(f"❌ メール送信失敗: {str(e)}")
            return False
    
    def send_question_notification(self, admin_email: str, question: str, user_email: str):
        """
        質問通知メールを管理者に送信
        
        Args:
            admin_email: 管理者メールアドレス
            question: 質問内容
            user_email: 質問者のメールアドレス
        """
        subject = "【Manual Bot AI】新しい質問が届きました"
        
        body = f"""
Manual Bot AIから新しい質問が届きました。

【質問者】
{user_email}

【質問内容】
{question}

【日時】
{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

管理画面から回答してください。
"""
        
        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif;">
    <h2>📧 新しい質問が届きました</h2>
    
    <div style="background: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0;">
        <p><strong>質問者:</strong> {user_email}</p>
        <p><strong>日時:</strong> {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
    </div>
    
    <div style="background: white; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
        <h3>質問内容</h3>
        <p>{question}</p>
    </div>
    
    <p style="margin-top: 30px;">
        <a href="https://your-domain.com/admin" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            管理画面で回答する
        </a>
    </p>
</body>
</html>
"""
        
        return self.send_email(admin_email, subject, body, html_body)
    
    def send_answer_notification(self, user_email: str, question: str, answer: str):
        """
        回答通知メールをユーザーに送信
        
        Args:
            user_email: ユーザーメールアドレス
            question: 質問内容
            answer: 回答内容
        """
        subject = "【Manual Bot AI】質問への回答が届きました"
        
        body = f"""
ご質問いただきありがとうございます。
回答をお送りします。

【ご質問】
{question}

【回答】
{answer}

【日時】
{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

他にご不明点がございましたら、お気軽にお問い合わせください。
"""
        
        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif;">
    <h2>💬 質問への回答が届きました</h2>
    
    <div style="background: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0;">
        <h3>ご質問</h3>
        <p>{question}</p>
    </div>
    
    <div style="background: #e7f3ff; padding: 20px; border: 1px solid #0066cc; border-radius: 5px;">
        <h3>回答</h3>
        <p>{answer}</p>
    </div>
    
    <p style="margin-top: 30px; color: #666;">
        他にご不明点がございましたら、お気軽にお問い合わせください。
    </p>
</body>
</html>
"""
        
        return self.send_email(user_email, subject, body, html_body)
    
    def send_welcome_email(self, user_email: str, username: str):
        """
        ウェルカムメールを送信
        
        Args:
            user_email: ユーザーメールアドレス
            username: ユーザー名
        """
        subject = "【Manual Bot AI】ご登録ありがとうございます"
        
        body = f"""
{username} 様

Manual Bot AIへのご登録ありがとうございます。

アカウントが正常に作成されました。
以下のURLからログインしてご利用ください。

ログインURL: https://your-domain.com/login

【ご利用開始の手順】
1. PDFファイルをアップロード
2. RAGシステムに追加
3. LINE/メールで質問

ご不明点がございましたら、お気軽にお問い合わせください。

Manual Bot AI チーム
"""
        
        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif;">
    <h2>🎉 ご登録ありがとうございます</h2>
    
    <p>{username} 様</p>
    
    <p>Manual Bot AIへのご登録ありがとうございます。<br>
    アカウントが正常に作成されました。</p>
    
    <div style="background: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0;">
        <h3>ご利用開始の手順</h3>
        <ol>
            <li>PDFファイルをアップロード</li>
            <li>RAGシステムに追加</li>
            <li>LINE/メールで質問</li>
        </ol>
    </div>
    
    <p style="margin-top: 30px;">
        <a href="https://your-domain.com/login" style="background: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            ログインする
        </a>
    </p>
    
    <p style="margin-top: 30px; color: #666;">
        ご不明点がございましたら、お気軽にお問い合わせください。
    </p>
</body>
</html>
"""
        
        return self.send_email(user_email, subject, body, html_body)

# 使用例
if __name__ == "__main__":
    notifier = EmailNotifier()
    if notifier.enabled:
        notifier.send_welcome_email("test@example.com", "テストユーザー")
    else:
        print("⚠️ メール通知は無効です")


