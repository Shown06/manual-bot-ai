import logging
from datetime import datetime
import json
from typing import Dict, Any, Tuple
import uuid

logger = logging.getLogger(__name__)

class AdminNotificationSystem:
    """管理者通知システム"""
    
    def __init__(self, line_bot_api):
        self.line_bot_api = line_bot_api
        self.pending_questions = {}
        self.admin_user_id = None
        self.admin_group_id = None
    
    def set_admin_contacts(self, admin_user_id: str, admin_group_id: str = None):
        """管理者の連絡先を設定"""
        self.admin_user_id = admin_user_id
        self.admin_group_id = admin_group_id
    
    def send_admin_notification(self, user_message: str, customer_info: Dict[str, Any]) -> Tuple[bool, str]:
        """管理者に未回答質問を通知"""
        try:
            question_id = str(uuid.uuid4())[:8]
            
            # 質問を保存
            self.pending_questions[question_id] = {
                'message': user_message,
                'customer_info': customer_info,
                'timestamp': datetime.now().isoformat(),
                'status': 'pending'
            }
            
            # 通知メッセージ作成
            notification = self._create_notification_message(question_id, user_message, customer_info)
            
            # 管理者に送信
            if self.admin_user_id and self.line_bot_api:
                try:
                    from linebot.models import TextSendMessage
                    self.line_bot_api.push_message(
                        self.admin_user_id,
                        TextSendMessage(text=notification)
                    )
                    
                    # グループにも送信
                    if self.admin_group_id:
                        self.line_bot_api.push_message(
                            self.admin_group_id,
                            TextSendMessage(text=notification)
                        )
                    
                    return True, question_id
                except Exception as e:
                    logger.error(f"LINE送信エラー: {e}")
                    return False, question_id
            
            return False, question_id
            
        except Exception as e:
            logger.error(f"管理者通知エラー: {e}")
            return False, None
    
    def _create_notification_message(self, question_id: str, user_message: str, customer_info: Dict[str, Any]) -> str:
        """通知メッセージを作成"""
        return f"""🔔 未回答の質問

ID: {question_id}
顧客: {customer_info.get('company_name', '不明')}
場所: {customer_info.get('group_name', 'DM')}
時刻: {datetime.now().strftime('%H:%M')}

質問内容:
{user_message}

回答するには:
#回答 {question_id} [回答内容]"""
    
    def process_admin_response(self, admin_message: str, admin_user_id: str) -> str:
        """管理者からの回答を処理"""
        try:
            if not admin_message.startswith('#'):
                return None
            
            parts = admin_message.split(' ', 2)
            if len(parts) < 3:
                return "形式: #回答 [質問ID] [回答内容]"
            
            command = parts[0]
            question_id = parts[1]
            answer = parts[2]
            
            if command == '#回答':
                if question_id in self.pending_questions:
                    question_data = self.pending_questions[question_id]
                    question_data['status'] = 'answered'
                    question_data['answer'] = answer
                    question_data['answered_at'] = datetime.now().isoformat()
                    
                    return f"✅ 質問 {question_id} に回答しました。"
                else:
                    return f"❌ 質問ID {question_id} が見つかりません。"
            
            elif command == '#一覧':
                return self._list_pending_questions()
            
            return None
            
        except Exception as e:
            logger.error(f"管理者応答処理エラー: {e}")
            return "処理中にエラーが発生しました。"
    
    def _list_pending_questions(self) -> str:
        """未回答質問一覧を表示"""
        pending = [q for q in self.pending_questions.items() if q[1]['status'] == 'pending']
        
        if not pending:
            return "未回答の質問はありません。"
        
        message = "📋 未回答の質問一覧\n\n"
        for qid, data in pending[:5]:
            message += f"ID: {qid}\n"
            message += f"時刻: {data['timestamp'][:16]}\n"
            message += f"質問: {data['message'][:50]}...\n\n"
        
        if len(pending) > 5:
            message += f"他 {len(pending) - 5} 件"
        
        return message
