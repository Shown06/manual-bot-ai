from flask import Blueprint, request, jsonify
import os
import json
import sqlite3
import gzip
import shutil
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from google.cloud import storage
import hashlib
import logging
from apscheduler.schedulers.background import BackgroundScheduler

data_protection_bp = Blueprint('data_protection', __name__)
logger = logging.getLogger(__name__)

ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', Fernet.generate_key())
cipher_suite = Fernet(ENCRYPTION_KEY)

GCS_BUCKET = os.environ.get('GCS_BUCKET', 'manual-bot-backups')
storage_client = storage.Client()
bucket = storage_client.bucket(GCS_BUCKET)

DATA_RETENTION_DAYS = {
    'conversations': 90,
    'logs': 30,
    'analytics': 365,
    'backups': 30
}

def encrypt_data(data):
    if isinstance(data, str):
        data = data.encode()
    return cipher_suite.encrypt(data).decode()

def decrypt_data(encrypted_data):
    if isinstance(encrypted_data, str):
        encrypted_data = encrypted_data.encode()
    return cipher_suite.decrypt(encrypted_data).decode()

def hash_pii(data):
    return hashlib.sha256(data.encode()).hexdigest()

def anonymize_user_data(user_data):
    anonymized = user_data.copy()
    
    pii_fields = ['email', 'phone', 'address', 'credit_card']
    
    for field in pii_fields:
        if field in anonymized:
            anonymized[field] = hash_pii(anonymized[field])
    
    if 'name' in anonymized:
        anonymized['name'] = 'User_' + hash_pii(anonymized['name'])[:8]
    
    return anonymized

def create_backup():
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'backup_{timestamp}.db.gz'
        
        db_path = 'manual_bot.db'
        backup_path = f'/tmp/{backup_name}'
        
        with open(db_path, 'rb') as f_in:
            with gzip.open(backup_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        encrypted_backup_path = backup_path + '.enc'
        
        with open(backup_path, 'rb') as f:
            encrypted_data = cipher_suite.encrypt(f.read())
            
        with open(encrypted_backup_path, 'wb') as f:
            f.write(encrypted_data)
        
        blob = bucket.blob(f'backups/{backup_name}.enc')
        blob.upload_from_filename(encrypted_backup_path)
        
        blob.metadata = {
            'created_at': timestamp,
            'encryption': 'AES-256',
            'checksum': hashlib.md5(open(encrypted_backup_path, 'rb').read()).hexdigest()
        }
        blob.patch()
        
        os.remove(backup_path)
        os.remove(encrypted_backup_path)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO backups (filename, size, checksum, location, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            backup_name,
            os.path.getsize(db_path),
            blob.metadata['checksum'],
            f'gs://{GCS_BUCKET}/backups/{backup_name}.enc',
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Backup created successfully: {backup_name}")
        
        cleanup_old_backups()
        
        return True
        
    except Exception as e:
        logger.error(f"Backup failed: {str(e)}")
        return False

def cleanup_old_backups():
    cutoff_date = datetime.now() - timedelta(days=DATA_RETENTION_DAYS['backups'])
    
    blobs = bucket.list_blobs(prefix='backups/')
    
    for blob in blobs:
        if blob.time_created < cutoff_date:
            blob.delete()
            logger.info(f"Deleted old backup: {blob.name}")

def restore_backup(backup_name):
    try:
        blob = bucket.blob(f'backups/{backup_name}.enc')
        
        encrypted_backup_path = f'/tmp/{backup_name}.enc'
        blob.download_to_filename(encrypted_backup_path)
        
        with open(encrypted_backup_path, 'rb') as f:
            decrypted_data = cipher_suite.decrypt(f.read())
        
        backup_path = f'/tmp/{backup_name}'
        with open(backup_path, 'wb') as f:
            f.write(decrypted_data)
        
        restore_path = f'/tmp/restored_{backup_name}.db'
        
        with gzip.open(backup_path, 'rb') as f_in:
            with open(restore_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        os.remove(encrypted_backup_path)
        os.remove(backup_path)
        
        return restore_path
        
    except Exception as e:
        logger.error(f"Restore failed: {str(e)}")
        return None

@data_protection_bp.route('/gdpr/export', methods=['POST'])
@require_auth
def gdpr_export_data():
    user_id = session.get('user_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    user_data = {}
    
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user_data['profile'] = dict(cursor.fetchone())
    
    cursor.execute('SELECT * FROM conversations WHERE user_id = ?', (user_id,))
    user_data['conversations'] = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute('SELECT * FROM files WHERE user_id = ?', (user_id,))
    user_data['files'] = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute('SELECT * FROM payment_history WHERE user_id = ?', (user_id,))
    user_data['payments'] = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    export_data = json.dumps(user_data, indent=2, default=str)
    
    response = make_response(export_data)
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = f'attachment; filename=gdpr_export_{user_id}.json'
    
    cursor.execute('''
        INSERT INTO audit_logs (user_id, action, details)
        VALUES (?, ?, ?)
    ''', (user_id, 'gdpr_export', 'User data exported'))
    
    return response

@data_protection_bp.route('/gdpr/delete', methods=['POST'])
@require_auth
def gdpr_delete_data():
    user_id = session.get('user_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = dict(cursor.fetchone())
    
    anonymized_user = anonymize_user_data(user)
    
    cursor.execute('''
        UPDATE users 
        SET email = ?, name = ?, phone = ?, 
            address = ?, deleted_at = ?, is_deleted = 1
        WHERE id = ?
    ''', (
        anonymized_user['email'],
        anonymized_user['name'],
        anonymized_user.get('phone', ''),
        anonymized_user.get('address', ''),
        datetime.now(),
        user_id
    ))
    
    cursor.execute('''
        UPDATE conversations 
        SET message = '[DELETED]', response = '[DELETED]'
        WHERE user_id = ?
    ''', (user_id,))
    
    cursor.execute('DELETE FROM files WHERE user_id = ?', (user_id,))
    
    cursor.execute('''
        INSERT INTO audit_logs (user_id, action, details)
        VALUES (?, ?, ?)
    ''', (user_id, 'gdpr_delete', 'User data anonymized and deleted'))
    
    conn.commit()
    conn.close()
    
    session.clear()
    
    return jsonify({'message': 'Your data has been deleted according to GDPR requirements'})

def apply_retention_policy():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for data_type, days in DATA_RETENTION_DAYS.items():
        if data_type == 'conversations':
            cutoff_date = datetime.now() - timedelta(days=days)
            cursor.execute('''
                DELETE FROM conversations 
                WHERE created_at < ? AND user_id IN (
                    SELECT id FROM users WHERE plan_id = 'free'
                )
            ''', (cutoff_date,))
        
        elif data_type == 'logs':
            cutoff_date = datetime.now() - timedelta(days=days)
            cursor.execute('''
                DELETE FROM system_logs WHERE created_at < ?
            ''', (cutoff_date,))
    
    conn.commit()
    conn.close()
    
    logger.info("Data retention policy applied")

scheduler = BackgroundScheduler(timezone='Asia/Tokyo')

scheduler.add_job(
    func=create_backup,
    trigger='cron',
    hour=3,
    minute=0,
    id='daily_backup',
    replace_existing=True
)

scheduler.add_job(
    func=apply_retention_policy,
    trigger='cron',
    hour=4,
    minute=0,
    id='retention_policy',
    replace_existing=True
)

scheduler.start()

@data_protection_bp.route('/compliance/audit-trail', methods=['GET'])
@require_admin
def get_audit_trail():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM audit_logs 
        ORDER BY created_at DESC 
        LIMIT 1000
    ''', (user_id,))
    
    audit_logs = [dict(row) for row in cursor.fetchall()]
    
    for log in audit_logs:
        log['checksum'] = hashlib.sha256(
            f"{log['id']}{log['user_id']}{log['action']}{log['created_at']}".encode()
        ).hexdigest()
    
    conn.close()
    
    return jsonify({'audit_logs': audit_logs})
