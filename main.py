#!/usr/bin/env python3
"""
Manual Bot AI - Complete Enterprise Edition
Version: 6.0.0
Last Updated: 2025-08-05
"""

from flask import Flask, request, jsonify, render_template, render_template_string, redirect, url_for, session, send_file, flash, abort
from functools import wraps
import os
import sqlite3

# Supabase (optional)
USE_SUPABASE = False
supabase_client = None

try:
    from supabase import create_client, Client
    SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
    SUPABASE_KEY = os.environ.get('SUPABASE_ANON_KEY', '')
    
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            USE_SUPABASE = True
            print("✅ Supabase接続成功")
        except Exception as e:
            print(f"⚠️ Supabase接続失敗: {e}")
            USE_SUPABASE = False
    else:
        print("⚠️ SQLiteモードで動作")
except ImportError:
    print("⚠️ Supabase未インストール - SQLiteモードで動作")


import hashlib
from datetime import datetime, timedelta
import logging
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import openai
import time
import json
import io
import csv
import docx
import PyPDF2
import secrets
import bcrypt
import tempfile

# Optional custom modules with error handling
try:
    from pdf_converter import PDFConverter
except ImportError:
    PDFConverter = None

try:
    from rag_system import RAGSystem
except ImportError:
    RAGSystem = None

try:
    from email_notifier import EmailNotifier
except ImportError:
    EmailNotifier = None

try:
    from multi_tenant import MultiTenantManager
except ImportError:
    MultiTenantManager = None

# Optional scheduler
try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ImportError:
    BackgroundScheduler = None

try:
    import pytz
except ImportError:
    pytz = None
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import stripe
import requests
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import jwt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import re
import uuid
from io import BytesIO
import base64

# Optional reportlab imports
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    colors = None
    letter = None
    A4 = None
    SimpleDocTemplate = None
    Table = None
    TableStyle = None
    Paragraph = None
    Spacer = None
    getSampleStyleSheet = None
    pdfmetrics = None
    UnicodeCIDFont = None

# Optional qrcode
try:
    import qrcode
except ImportError:
    qrcode = None
from collections import defaultdict
import threading
import queue
import random
import string
import chardet
from typing import Dict, List, Optional, Tuple, Any

# Import custom modules
try:
    from simple_search import SimpleSearch
    from safe_customer_response import SafeCustomerBot
    from admin_notification import AdminNotificationSystem
    from language_handler import LanguageHandler
except ImportError as e:
    logging.warning(f"Custom module import failed: {e}")
    SimpleSearch = None
    SafeCustomerBot = None
    AdminNotificationSystem = None
    LanguageHandler = None

# Initialize Flask app
app = Flask(__name__)
app.static_folder = 'static'
app.static_url_path = '/static'
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# PDF変換エンジン初期化
pdf_converter = None
if PDFConverter:
    try:
        pdf_converter = PDFConverter()
        logger.info("✅ PDF変換エンジン初期化成功")
    except Exception as e:
        logger.error(f"❌ PDF変換エンジン初期化失敗: {e}")
        pdf_converter = None
else:
    logger.warning("⚠️ PDFConverter module not available")

# メール通知システム初期化
email_notifier = None
if EmailNotifier:
    try:
        email_notifier = EmailNotifier()
        logger.info("✅ メール通知システム初期化成功")
    except Exception as e:
        logger.error(f"❌ メール通知システム初期化失敗: {e}")
        email_notifier = None
else:
    logger.warning("⚠️ EmailNotifier module not available")

# マルチテナント管理システム初期化
multi_tenant = None
if MultiTenantManager:
    try:
        multi_tenant = MultiTenantManager()
        logger.info("✅ マルチテナント管理システム初期化成功")
    except Exception as e:
        logger.error(f"❌ マルチテナント管理システム初期化失敗: {e}")
        multi_tenant = None
else:
    logger.warning("⚠️ MultiTenantManager module not available")

# Environment variables
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
ADMIN_USER_ID = os.environ.get('ADMIN_LINE_USER_ID', '')
ADMIN_GROUP_ID = os.environ.get('ADMIN_LINE_GROUP_ID', '')
DATABASE_PATH = os.environ.get('DATABASE_PATH', 'manual_bot.db')

# Stripe configuration
stripe.api_key = STRIPE_SECRET_KEY

# OpenAI configuration - require environment variable
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY not set in environment variables")

# Initialize OpenAI client with error handling
import openai
openai_client = None
try:
    if OPENAI_API_KEY:
        openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
        logger.info("✅ OpenAI client initialized successfully")
    else:
        logger.warning("⚠️ OpenAI API key not set - AI features disabled")
except Exception as e:
    logger.error(f"❌ OpenAI client initialization failed: {e}")
    openai_client = None

# LINE Bot configuration - require environment variables
if not LINE_CHANNEL_ACCESS_TOKEN:
    logger.warning("LINE_CHANNEL_ACCESS_TOKEN not set in environment variables")

if not LINE_CHANNEL_SECRET:
    logger.warning("LINE_CHANNEL_SECRET not set in environment variables")

print(f"Initializing LINE Bot - ACCESS_TOKEN: {bool(LINE_CHANNEL_ACCESS_TOKEN)}, SECRET: {bool(LINE_CHANNEL_SECRET)}")
line_bot_api = None
handler = None
try:
    if LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET:
        line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
        handler = WebhookHandler(LINE_CHANNEL_SECRET)
        logger.info("✅ LINE Bot initialized successfully")
    else:
        logger.warning("⚠️ LINE Bot credentials not set")
except Exception as e:
    logger.error(f"❌ LINE Bot initialization failed: {e}")
    line_bot_api = None
    handler = None

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per hour", "100 per minute"],
    storage_uri="memory://"
)

# Initialize custom modules if available
search_engine = SimpleSearch() if SimpleSearch else None
safe_response = SafeCustomerBot() if SafeCustomerBot else None
admin_notifier = AdminNotificationSystem(line_bot_api) if AdminNotificationSystem else None
language_handler = LanguageHandler() if LanguageHandler else None
# Admin notification setup
if admin_notifier and ADMIN_USER_ID:
    admin_notifier.set_admin_contacts(ADMIN_USER_ID, ADMIN_GROUP_ID)


# Plan configuration
PLANS = {
    'starter': {
        'name': 'スターター',
        'price': 9800,
        'files': 5,
        'api_calls': 1000,
        'messages': 5000,
        'file_size': 10 * 1024 * 1024,
        'features': ['基本的なQ&A', 'ファイルアップロード', 'LINE連携']
    },
    'pro': {
        'name': 'プロフェッショナル',
        'price': 19800,
        'files': 20,
        'api_calls': 5000,
        'messages': 20000,
        'file_size': 25 * 1024 * 1024,
        'features': ['高度な分析', 'APIアクセス', '優先サポート', 'カスタマイズ']
    },
    'enterprise': {
        'name': 'エンタープライズ',
        'price': 49800,
        'files': -1,  # Unlimited
        'api_calls': -1,
        'messages': -1,
        'file_size': 50 * 1024 * 1024,
        'features': ['無制限利用', 'チーム管理', '専用サポート', 'SLA保証', 'カスタム開発']
    }
}

# Database initialization
def init_db():
    """Initialize database with all required tables."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        stripe_customer_id TEXT,
        subscription_status TEXT DEFAULT 'inactive',
        plan TEXT DEFAULT 'starter',
        is_admin BOOLEAN DEFAULT 0,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Files table
    cursor.execute('''CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        file_path TEXT,
        file_size INTEGER,
        content TEXT,
        tenant_id INTEGER,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # LINE accounts table
    cursor.execute('''CREATE TABLE IF NOT EXISTS line_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        line_user_id TEXT UNIQUE NOT NULL,
        display_name TEXT,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # Conversations table
    cursor.execute('''CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        line_user_id TEXT,
        message TEXT NOT NULL,
        response TEXT,
        is_answered BOOLEAN DEFAULT 0,
        language TEXT DEFAULT 'ja',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # Usage tracking table
    cursor.execute('''CREATE TABLE IF NOT EXISTS usage_tracking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        month TEXT NOT NULL,
        files_uploaded INTEGER DEFAULT 0,
        api_calls_made INTEGER DEFAULT 0,
        messages_sent INTEGER DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        UNIQUE(user_id, month)
    )''')
    
    # API keys table
    cursor.execute('''CREATE TABLE IF NOT EXISTS api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        key_hash TEXT NOT NULL,
        name TEXT,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_used_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # Audit logs table
    cursor.execute('''CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT,
        ip_address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # Support tickets table
    cursor.execute('''CREATE TABLE IF NOT EXISTS support_tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        subject TEXT NOT NULL,
        status TEXT DEFAULT 'open',
        priority TEXT DEFAULT 'normal',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # Ticket messages table
    cursor.execute('''CREATE TABLE IF NOT EXISTS ticket_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER NOT NULL,
        user_id INTEGER,
        message TEXT NOT NULL,
        is_staff BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (ticket_id) REFERENCES support_tickets (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # LINE link codes table
    cursor.execute('''CREATE TABLE IF NOT EXISTS line_link_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # Pending questions table
    cursor.execute('''CREATE TABLE IF NOT EXISTS pending_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id TEXT UNIQUE NOT NULL,
        user_id INTEGER,
        line_user_id TEXT,
        message TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        answer TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        answered_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_line_accounts_line_user_id ON line_accounts(line_user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_tracking_user_month ON usage_tracking(user_id, month)')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('ログインが必要です。', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('ログインが必要です。', 'warning')
            return redirect(url_for('login'))
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT is_admin FROM users WHERE id = ?', (session['user_id'],))
        user = cursor.fetchone()
        conn.close()
        
        if not user or not user[0]:
            flash('管理者権限が必要です。', 'danger')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

# Utility functions
def get_db_connection():
    """Get database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def generate_link_code():
    """Generate 4-digit link code."""
    return ''.join(random.choices(string.digits, k=4))

def allowed_file(filename):
    """Check if file extension is allowed."""
    ALLOWED_EXTENSIONS = {'pdf', 'txt', 'doc', 'docx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(file_path, file_type):
    """Extract text from various file types."""
    try:
        if file_type == 'pdf':
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        
        elif file_type in ['doc', 'docx']:
            doc = docx.Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text.strip()
        
        elif file_type == 'txt':
            # Detect encoding
            with open(file_path, 'rb') as file:
                raw_data = file.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding'] or 'utf-8'
            
            with open(file_path, 'r', encoding=encoding) as file:
                return file.read().strip()
        
        else:
            return ""
    
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
        return ""

def check_usage_limit(user_id, limit_type='files'):
    """Check if user has exceeded their plan limits."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get user plan
    cursor.execute('SELECT plan FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return False
    
    plan = user['plan']
    limits = PLANS[plan]
    
    # Check unlimited
    if limits[limit_type] == -1:
        conn.close()
        return True
    
    # Get current month usage
    current_month = datetime.now().strftime('%Y-%m')
    cursor.execute('''
        SELECT files_uploaded, api_calls_made, messages_sent
        FROM usage_tracking
        WHERE user_id = ? AND month = ?
    ''', (user_id, current_month))
    
    usage = cursor.fetchone()
    conn.close()
    
    if not usage:
        return True
    
    if limit_type == 'files':
        return usage['files_uploaded'] < limits['files']
    elif limit_type == 'api_calls':
        return usage['api_calls_made'] < limits['api_calls']
    elif limit_type == 'messages':
        return usage['messages_sent'] < limits['messages']
    
    return False

def update_usage(user_id, usage_type='files', amount=1):
    """Update user usage statistics."""
    conn = get_db_connection()
    cursor = conn.cursor()
    current_month = datetime.now().strftime('%Y-%m')
    
    if usage_type == 'files':
        cursor.execute('''
            INSERT INTO usage_tracking (user_id, month, files_uploaded)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, month) DO UPDATE SET
            files_uploaded = files_uploaded + ?,
            updated_at = CURRENT_TIMESTAMP
        ''', (user_id, current_month, amount, amount))
    elif usage_type == 'api_calls':
        cursor.execute('''
            INSERT INTO usage_tracking (user_id, month, api_calls_made)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, month) DO UPDATE SET
            api_calls_made = api_calls_made + ?,
            updated_at = CURRENT_TIMESTAMP
        ''', (user_id, current_month, amount, amount))
    elif usage_type == 'messages':
        cursor.execute('''
            INSERT INTO usage_tracking (user_id, month, messages_sent)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, month) DO UPDATE SET
            messages_sent = messages_sent + ?,
            updated_at = CURRENT_TIMESTAMP
        ''', (user_id, current_month, amount, amount))
    
    conn.commit()
    conn.close()

def log_audit(user_id, action, details=None, ip_address=None):
    """Log user actions for audit trail."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO audit_logs (user_id, action, details, ip_address)
        VALUES (?, ?, ?, ?)
    ''', (user_id, action, details, ip_address))
    conn.commit()
    conn.close()

# Routes
@app.route('/')
def index():
    """Redirect to landing page."""
    return redirect('/landing')

@app.route('/health')
def health():
    """Health check endpoint."""
    try:
        # Check database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        conn.close()
        
        # Check external services
        services_status = {
            'database': 'healthy',
            'line_api': 'healthy' if LINE_CHANNEL_ACCESS_TOKEN else 'unhealthy',
            'openai_api': 'healthy' if (OPENAI_API_KEY and 'openai_client' in globals()) else 'unhealthy',
            'stripe_api': 'healthy' if STRIPE_SECRET_KEY else 'unhealthy'
        }
        
        overall_status = 'healthy' if all(s == 'healthy' for s in services_status.values()) else 'degraded'
        
        return jsonify({
            'status': overall_status,
            'timestamp': datetime.utcnow().isoformat(),
            'services': services_status,
            'version': '6.0.0'
        }), 200 if overall_status == 'healthy' else 503
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('メールアドレスとパスワードは必須です。', 'danger')
            return render_template('register.html')
        
        if len(password) < 8:
            flash('パスワードは8文字以上である必要があります。', 'danger')
            return render_template('register.html')
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            if cursor.fetchone():
                flash('このメールアドレスは既に登録されています。', 'danger')
                return render_template('register.html')
            
            # Hash password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # Create Stripe customer
            try:
                customer = stripe.Customer.create(
                    email=email,
                    metadata={'source': 'web_registration'}
                )
                stripe_customer_id = customer.id
            except Exception as e:
                logger.error(f"Stripe customer creation failed: {e}")
                stripe_customer_id = None
            
            # Insert user
            cursor.execute('''
                INSERT INTO users (email, password_hash, stripe_customer_id)
                VALUES (?, ?, ?)
            ''', (email, password_hash, stripe_customer_id))
            
            user_id = cursor.lastrowid
            
            # Initialize usage tracking
            current_month = datetime.now().strftime('%Y-%m')
            cursor.execute('''
                INSERT INTO usage_tracking (user_id, month)
                VALUES (?, ?)
            ''', (user_id, current_month))
            
            conn.commit()
            conn.close()
            
            # Log registration
            log_audit(user_id, 'user_registered', f'Email: {email}', request.remote_addr)
            
            flash('登録が完了しました。ログインしてください。', 'success')
            return redirect(url_for('login'))
        
        except Exception as e:
            logger.error(f"Registration error: {e}")
            flash('登録中にエラーが発生しました。', 'danger')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('メールアドレスとパスワードを入力してください。', 'danger')
            return render_template('login.html')
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, password_hash, plan, subscription_status, tenant_id
                FROM users WHERE email = ?
            ''', (email,))
            
            user = cursor.fetchone()
            conn.close()
            
            if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash']):
                # Set session
                session['user_id'] = user['id']
                session['email'] = email
                session['plan'] = user['plan']
                session['subscription_status'] = user['subscription_status']
                session['is_admin'] = 0  # Default to non-admin
                session.permanent = True
                
                # Log login
                log_audit(user['id'], 'user_login', None, request.remote_addr)
                
                flash('ログインしました。', 'success')
                # return redirect('http://localhost:8501')  # 一時的にコメントアウト
                return redirect('/dashboard')
            else:
                flash('メールアドレスまたはパスワードが正しくありません。', 'danger')
        
        except Exception as e:
            logger.error(f"Login error: {e}")
            flash('ログイン中にエラーが発生しました。', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout."""
    if 'user_id' in session:
        log_audit(session['user_id'], 'user_logout', None, request.remote_addr)
    
    session.clear()
    flash('ログアウトしました。', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        user_id = session['user_id']
        
        # Get user info
        cursor.execute('''
            SELECT email, plan, subscription_status, created_at
            FROM users WHERE id = ?
        ''', (user_id,))
        user = cursor.fetchone()
        
        # Get usage stats
        current_month = datetime.now().strftime('%Y-%m')
        cursor.execute('''
            SELECT files_uploaded, api_calls_made, messages_sent
            FROM usage_tracking
            WHERE user_id = ? AND month = ?
        ''', (user_id, current_month))
        usage = cursor.fetchone() or {'files_uploaded': 0, 'api_calls_made': 0, 'messages_sent': 0}
        
        # Get recent files
        cursor.execute('''
            SELECT filename, file_size, uploaded_at
            FROM files
            WHERE user_id = ?
            ORDER BY uploaded_at DESC
            LIMIT 10
        ''', (user_id,))
        recent_files = cursor.fetchall()
        
        # Get LINE account status
        cursor.execute('''
            SELECT line_user_id, display_name, is_active
            FROM line_accounts
            WHERE user_id = ? AND is_active = 1
        ''', (user_id,))
        line_accounts = cursor.fetchall()
        
        # Get plan limits
        plan_limits = PLANS[user['plan']]
        
        conn.close()
        
        return render_template('dashboard.html',
            user=user,
            usage=usage,
            files=recent_files,
            line_accounts=line_accounts,
            plan_limits=plan_limits,
            current_month=current_month
        )
    
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        flash('ダッシュボードの読み込み中にエラーが発生しました。', 'danger')
        return redirect(url_for('index'))

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """Handle LINE webhook events."""
    # Handle GET request (for webhook verification)
    if request.method == 'GET':
        logger.info("Webhook GET verification request received")
        return 'OK', 200

    # Get request body and signature
    try:
        body = request.get_data(as_text=True)
        signature = request.headers.get('X-Line-Signature', '')
    except Exception as e:
        logger.error(f"Error reading webhook request: {e}")
        return 'OK', 200  # Return 200 to prevent LINE from retrying

    # Handle empty body (verification request)
    if not body or body.strip() == '' or body == '{}':
        logger.info("Empty webhook body received (verification request)")
        return 'OK', 200

    # Debug logging
    logger.info(f"Webhook received - Body length: {len(body)}, Signature: {signature[:20] if signature else 'None'}...")
    logger.info(f"LINE_CHANNEL_SECRET available: {bool(LINE_CHANNEL_SECRET)}, Handler available: {bool(handler)}")

    # Verify signature and process webhook
    try:
        # Check if handler is available
        if not handler:
            logger.warning("Handler is None - LINE Bot not properly initialized")
            return 'OK', 200  # Return 200 to avoid 400 errors
        
        # Check if signature is present (required for security)
        if not signature or len(signature) < 10:
            logger.warning("No valid signature in webhook request")
            # For verification, return 200 even without signature
            if not body or body.strip() == '' or body == '{}':
                return 'OK', 200
            # For actual messages without signature, return 400 for security
            abort(400)
        
        # Process webhook with handler
        try:
            handler.handle(body, signature)
            logger.info("Webhook processed successfully by handler")
        except Exception as handler_error:
            logger.error(f"Handler processing error: {str(handler_error)}")
            import traceback
            traceback.print_exc()
            # Try manual processing as fallback
            try:
                import json
                json_body = json.loads(body)
                events = json_body.get('events', [])
                logger.info(f"Attempting manual processing for {len(events)} events")
                
                for event in events:
                    if event.get('type') == 'message' and event.get('message', {}).get('type') == 'text':
                        line_user_id = event.get('source', {}).get('userId')
                        message_text = event.get('message', {}).get('text')
                        reply_token = event.get('replyToken')

                        if message_text and reply_token:
                            logger.info(f"Manual processing message from {line_user_id}: {message_text}")
                            handle_text_message_manual(line_user_id, message_text, reply_token)
            except Exception as manual_error:
                logger.error(f"Manual processing also failed: {str(manual_error)}")

    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return 200 for verification requests, 500 for actual errors
        if not body or body.strip() == '' or body == '{}':
            return 'OK', 200
        abort(500)
    
    return 'OK', 200

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """Handle LINE text messages."""
    try:
        line_user_id = event.source.user_id
        message_text = event.message.text
        reply_token = event.reply_token
        
        # Check if it's a group message
        is_group = event.source.type == 'group'
        group_id = event.source.group_id if is_group else None
        
        # Admin commands
        if line_user_id == ADMIN_USER_ID:
            if message_text.startswith('#回答'):
                handle_admin_answer(event)
                return
            elif message_text == '#一覧':
                handle_admin_list(event)
                return
        
        # Link code handling
        if re.match(r'^\d{4}$', message_text):
            handle_link_code(event)
            return
        
        # Find linked user
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id FROM line_accounts
            WHERE line_user_id = ? AND is_active = 1
        ''', (line_user_id,))
        
        line_account = cursor.fetchone()
        
        if not line_account:
            # Not linked
            line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text="このアカウントはまだ連携されていません。\nWebサイトから連携コードを生成してください。")
            )
            conn.close()
            return
        
        user_id = line_account['user_id']
        
        # Check usage limits
        if not check_usage_limit(user_id, 'messages'):
            line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text="メッセージ送信数の上限に達しました。プランをアップグレードしてください。")
            )
            conn.close()
            return
        
        # Detect language
        detected_language = 'ja'
        if language_handler:
            detected_language = language_handler.detect_language(message_text)
        
        # Search for relevant content
        cursor.execute('''
            SELECT content FROM files
            WHERE user_id = ?
            ORDER BY uploaded_at DESC
            LIMIT 5
        ''', (user_id,))
        
        files = cursor.fetchall()
        context = "\n".join([f['content'][:500] for f in files if f['content']])
        
        # Search using search engine
        if search_engine:
            search_results = search_engine.search(message_text, user_id)
            if search_results:
                context = "\n".join([result['content'][:500] for result in search_results[:3]])
        
        # Generate AI response with user_id
        ai_response = generate_ai_response(message_text, context, detected_language, user_id=user_id)
        logger.info(f"AI response generated for user {user_id}: {ai_response[:100]}...")
        
        # Apply safety filters
        if safe_response:
            ai_response = safe_response.filter_response(ai_response)
        
        # Save conversation
        cursor.execute('''
            INSERT INTO conversations (user_id, line_user_id, message, response, is_answered, language)
            VALUES (?, ?, ?, ?, 1, ?)
        ''', (user_id, line_user_id, message_text, ai_response, detected_language))
        
        conversation_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Update usage
        update_usage(user_id, 'messages', 1)
        update_usage(user_id, 'api_calls', 1)
        
        # Send response
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=ai_response)
        )
        
        # Check for urgent keywords
        urgent_keywords = ['緊急', '至急', '大至急', 'urgent', 'emergency', '紧急']
        if any(keyword in message_text.lower() for keyword in urgent_keywords):
            if admin_notifier:
                admin_notifier.notify_urgent_message(line_user_id, message_text, conversation_id)
    
    except Exception as e:
        logger.error(f"Message handling error: {e}")
        try:
            line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text="申し訳ございません。エラーが発生しました。しばらく経ってから再度お試しください。")
            )
        except:
            pass

def handle_text_message_manual(line_user_id, message_text, reply_token):
    """Handle LINE text messages manually (for webhook testing)."""
    try:
        # Check if it's a group message (simplified)
        is_group = False  # Manual processing doesn't have group info

        # Admin commands
        if line_user_id == ADMIN_USER_ID:
            if message_text.startswith('#回答'):
                # Handle admin answer (simplified)
                line_bot_api.reply_message(
                    reply_token,
                    TextSendMessage(text="管理者コマンドはWebhook経由ではサポートされていません。")
                )
                return
            elif message_text == '#一覧':
                # Handle admin list (simplified)
                line_bot_api.reply_message(
                    reply_token,
                    TextSendMessage(text="管理者コマンドはWebhook経由ではサポートされていません。")
                )
                return

        # Link code handling
        if re.match(r'^\d{4}$', message_text):
            handle_link_code_manual(line_user_id, message_text, reply_token)
            return

        # Find linked user
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id FROM line_accounts
            WHERE line_user_id = ? AND is_active = 1
        ''', (line_user_id,))

        line_account = cursor.fetchone()

        if not line_account:
            # Not linked
            line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text="このアカウントはまだ連携されていません。\nWebサイトから連携コードを生成してください。")
            )
            conn.close()
            return

        user_id = line_account['user_id']

        # Check usage limits
        if not check_usage_limit(user_id, 'messages'):
            line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text="メッセージ送信数の上限に達しました。プランをアップグレードしてください。")
            )
            conn.close()
            return

        # Generate AI response
        ai_response = generate_ai_response(message_text, user_id=user_id)
        logger.info(f"AI response generated successfully for user {user_id}: {ai_response[:100]}...")

        # Send response
        try:
            line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text=ai_response)
            )
            logger.info(f"✅ Successfully sent AI response to LINE user: {line_user_id}")
        except Exception as reply_error:
            logger.warning(f"Failed to send reply to LINE (AI response was generated): {reply_error}")
            # AI response was generated successfully, just couldn't send to LINE
            # This is normal for test webhooks with invalid reply_token

        # Update usage
        update_usage(user_id, 'messages', 1)

        # Log message
        log_audit(user_id, 'message_sent', f'LINE User: {line_user_id}, Response: {ai_response[:50]}', None)

        conn.close()

    except Exception as e:
        logger.error(f"Manual message handling error: {e}")
        import traceback
        traceback.print_exc()
        try:
            line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text="申し訳ございません。エラーが発生しました。しばらく経ってから再度お試しください。")
            )
        except:
            logger.warning("Failed to send error message to LINE (invalid reply_token)")

def handle_link_code_manual(line_user_id, code, reply_token):
    """Handle LINE account linking with 4-digit code (manual processing)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Find active code
        cursor.execute('''
            SELECT user_id FROM line_link_codes
            WHERE code = ? AND is_active = 1 AND expires_at > CURRENT_TIMESTAMP
        ''', (code,))

        link_code = cursor.fetchone()

        if not link_code:
            line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text="無効または期限切れの連携コードです。")
            )
            conn.close()
            return

        user_id = link_code['user_id']

        # Check if already linked
        cursor.execute('''
            SELECT id FROM line_accounts
            WHERE line_user_id = ?
        ''', (line_user_id,))

        if cursor.fetchone():
            line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text="このLINEアカウントは既に連携されています。")
            )
            conn.close()
            return

        # Create link
        cursor.execute('''
            INSERT INTO line_accounts (user_id, line_user_id, display_name)
            VALUES (?, ?, ?)
        ''', (user_id, line_user_id, "Unknown"))

        # Deactivate code
        cursor.execute('''
            UPDATE line_link_codes
            SET is_active = 0
            WHERE code = ?
        ''', (code,))

        conn.commit()
        conn.close()

        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=f"連携が完了しました！\n\nこれからマニュアルに関する質問をお送りください。")
        )

        # Log the linking
        log_audit(user_id, 'line_account_linked', f'LINE User ID: {line_user_id}')

    except Exception as e:
        logger.error(f"Manual link code error: {e}")
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text="連携処理中にエラーが発生しました。")
        )

def handle_link_code(event):
    """Handle LINE account linking with 4-digit code."""
    code = event.message.text
    line_user_id = event.source.user_id
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Find active code
        cursor.execute('''
            SELECT user_id FROM line_link_codes
            WHERE code = ? AND is_active = 1 AND expires_at > CURRENT_TIMESTAMP
        ''', (code,))
        
        link_code = cursor.fetchone()
        
        if not link_code:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="無効または期限切れの連携コードです。")
            )
            conn.close()
            return
        
        user_id = link_code['user_id']
        
        # Get LINE profile
        try:
            profile = line_bot_api.get_profile(line_user_id)
            display_name = profile.display_name
        except:
            display_name = "Unknown"
        
        # Check if already linked
        cursor.execute('''
            SELECT id FROM line_accounts
            WHERE line_user_id = ?
        ''', (line_user_id,))
        
        if cursor.fetchone():
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="このLINEアカウントは既に連携されています。")
            )
            conn.close()
            return
        
        # Create link
        cursor.execute('''
            INSERT INTO line_accounts (user_id, line_user_id, display_name)
            VALUES (?, ?, ?)
        ''', (user_id, line_user_id, display_name))
        
        # Deactivate code
        cursor.execute('''
            UPDATE line_link_codes
            SET is_active = 0
            WHERE code = ?
        ''', (code,))
        
        conn.commit()
        conn.close()
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"連携が完了しました！\n\nこれからマニュアルに関する質問をお送りください。")
        )
        
        # Log the linking
        log_audit(user_id, 'line_account_linked', f'LINE User ID: {line_user_id}')
    
    except Exception as e:
        logger.error(f"Link code error: {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="連携処理中にエラーが発生しました。")
        )

def handle_admin_answer(event):
    """Handle admin answer command."""
    message_text = event.message.text
    match = re.match(r'#回答\s+(\w{8})\s+(.+)', message_text, re.DOTALL)
    
    if not match:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="形式: #回答 [質問ID] [回答内容]")
        )
        return
    
    question_id = match.group(1)
    answer = match.group(2).strip()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get pending question
        cursor.execute('''
            SELECT line_user_id, message, user_id
            FROM pending_questions
            WHERE question_id = ? AND status = 'pending'
        ''', (question_id,))
        
        question = cursor.fetchone()
        
        if not question:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="該当する未回答の質問が見つかりません。")
            )
            conn.close()
            return
        
        # Update question status
        cursor.execute('''
            UPDATE pending_questions
            SET status = 'answered', answer = ?, answered_at = CURRENT_TIMESTAMP
            WHERE question_id = ?
        ''', (answer, question_id))
        
        # Save to conversations
        cursor.execute('''
            INSERT INTO conversations (user_id, line_user_id, message, response, is_answered)
            VALUES (?, ?, ?, ?, 1)
        ''', (question['user_id'], question['line_user_id'], question['message'], answer))
        
        conn.commit()
        conn.close()
        
        # Send answer to user
        line_bot_api.push_message(
            question['line_user_id'],
            TextSendMessage(text=f"【回答】\n{answer}")
        )
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"質問ID {question_id} に回答しました。")
        )
    
    except Exception as e:
        logger.error(f"Admin answer error: {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="回答処理中にエラーが発生しました。")
        )

def handle_admin_list(event):
    """Handle admin list command."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT question_id, message, created_at
            FROM pending_questions
            WHERE status = 'pending'
            ORDER BY created_at DESC
            LIMIT 10
        ''')
        
        questions = cursor.fetchall()
        conn.close()
        
        if not questions:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="未回答の質問はありません。")
            )
            return
        
        message = "【未回答の質問一覧】\n\n"
        for q in questions:
            created_at = datetime.fromisoformat(q['created_at']).strftime('%m/%d %H:%M')
            message += f"ID: {q['question_id']}\n"
            message += f"日時: {created_at}\n"
            message += f"質問: {q['message'][:50]}...\n\n"
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=message)
        )
    
    except Exception as e:
        logger.error(f"Admin list error: {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="一覧取得中にエラーが発生しました。")
        )

def generate_ai_response(query, context="", language="ja", user_id=None):
    """Generate AI response using OpenAI API - STRICTLY RAG SYSTEM."""
    try:
        # Get user's uploaded documents first
        manual_content = ""
        has_manual = False
        
        if user_id:
            try:
                # Get user's uploaded files
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT content, filename FROM files
                    WHERE user_id = ? AND content IS NOT NULL AND content != ''
                    ORDER BY uploaded_at DESC
                    LIMIT 5
                ''', (user_id,))

                user_files = cursor.fetchall()
                conn.close()

                if user_files:
                    has_manual = True
                    manual_content = "\n\n【アップロードされたマニュアル情報】\n"
                    for content, filename in user_files:
                        if content and len(content.strip()) > 0:
                            # Limit content length to avoid token limits
                            truncated_content = content[:3000] + "..." if len(content) > 3000 else content
                            manual_content += f"\n=== {filename} ===\n{truncated_content}\n"

            except Exception as e:
                logger.warning(f"Failed to load user documents: {e}")
        
        # If no manual is uploaded, return error message
        if not has_manual:
            fallback_messages = {
                'ja': "申し訳ございません。現在、参照できるマニュアルがアップロードされていません。先にマニュアルファイルをアップロードしてください。",
                'en': "I apologize, but there are no manuals uploaded for reference. Please upload a manual file first.",
                'zh': "很抱歉，目前没有上传可参考的手册。请先上传手册文件。"
            }
            return fallback_messages.get(language, fallback_messages['ja'])
        
        # STRICT RAG SYSTEM PROMPT - Only answer from manual
        system_prompts = {
            'ja': f"""あなたは厳密なRAGシステムです。以下のマニュアル情報のみを参照して回答してください。

{manual_content}

【重要なルール】
1. 上記のマニュアル情報に関連する質問には、マニュアルの内容を引用して回答してください
2. マニュアルに関係ない質問（例: 子育て相談、一般的なアドバイス、マニュアル外の話題）には、必ず以下のように回答してください：
   「申し訳ございません。その質問はアップロードされたマニュアルの内容とは関係がありません。マニュアルに関するご質問をお願いいたします。」
3. 一般知識や常識で回答してはいけません
4. マニュアルに明確に書かれていることだけを答えてください

【判断基準】
- マニュアル関連の質問: マニュアルの内容、説明、詳細などについての質問
- マニュアル外の質問: 子育て、人間関係、健康、料理、旅行など、マニュアルと無関係な話題""",
            
            'en': f"""You are a STRICT RAG system. Only refer to the following manual information to answer questions.

{manual_content}

【IMPORTANT RULES】
1. For questions related to the manual above, quote and answer from the manual content
2. For questions unrelated to the manual (e.g., parenting advice, general advice, off-topic questions), ALWAYS respond:
   "I apologize, but that question is not related to the uploaded manual content. Please ask questions about the manual."
3. Do NOT use general knowledge or common sense
4. ONLY answer what is explicitly written in the manual

【Judgment Criteria】
- Manual-related: Questions about the manual content, explanations, details
- Non-manual: Parenting, relationships, health, cooking, travel, etc.""",
            
            'zh': f"""您是严格的RAG系统。仅参考以下手册信息回答问题。

{manual_content}

【重要规则】
1. 对于与上述手册相关的问题，引用手册内容回答
2. 对于与手册无关的问题（如：育儿咨询、一般建议、无关话题），必须回答：
   "很抱歉，该问题与上传的手册内容无关。请询问与手册相关的问题。"
3. 不要使用常识或一般知识
4. 仅回答手册中明确写明的内容

【判断标准】
- 手册相关: 关于手册内容、说明、详情的问题
- 手册无关: 育儿、人际关系、健康、烹饪、旅行等与手册无关的话题"""
        }
        
        system_prompt = system_prompts.get(language, system_prompts['ja'])
        
        # Generate response
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            max_tokens=1000,
            temperature=0.7
        )

        return response.choices[0].message.content
    
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        # Fallback response
        fallback_messages = {
            'ja': "申し訳ございません。現在システムに問題が発生しています。しばらく経ってから再度お試しください。",
            'en': "We apologize for the inconvenience. The system is currently experiencing issues. Please try again later.",
            'zh': "很抱歉给您带来不便。系统目前出现问题。请稍后再试。"
        }
        return fallback_messages.get(language, fallback_messages['ja'])

@app.route('/api/generate_link_code', methods=['POST'])
@login_required
def generate_link_code_api():
    """Generate LINE linking code."""
    try:
        user_id = session['user_id']
        
        # Generate 4-digit code
        code = generate_link_code()
        expires_at = datetime.now() + timedelta(minutes=10)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Deactivate old codes
        cursor.execute('''
            UPDATE line_link_codes
            SET is_active = 0
            WHERE user_id = ?
        ''', (user_id,))
        
        # Insert new code
        cursor.execute('''
            INSERT INTO line_link_codes (user_id, code, expires_at)
            VALUES (?, ?, ?)
        ''', (user_id, code, expires_at))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'code': code,
            'expires_at': expires_at.isoformat()
        })
    
    except Exception as e:
        logger.error(f"Link code generation error: {e}")
        return jsonify({'error': 'コード生成中にエラーが発生しました。'}), 500

@app.route('/api/check_linking_status', methods=['GET'])
@login_required
def check_linking_status():
    """Check if LINE account has been linked."""
    try:
        user_id = session['user_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id FROM line_accounts
            WHERE user_id = ? AND is_active = 1
        ''', (user_id,))
        
        line_account = cursor.fetchone()
        conn.close()
        
        return jsonify({
            'linked': line_account is not None
        })
    
    except Exception as e:
        logger.error(f"Linking status check error: {e}")
        return jsonify({'linked': False}), 500

@app.route('/upload', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def upload_file():
    """Handle file upload."""
    if 'file' not in request.files:
        return jsonify({'error': 'ファイルが選択されていません。'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'ファイルが選択されていません。'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': '許可されていないファイル形式です。'}), 400
    
    user_id = session['user_id']
    
    # Check file upload limit
    if not check_usage_limit(user_id, 'files'):
        return jsonify({'error': 'ファイルアップロード数の上限に達しました。'}), 403
    
    # Check file size
    plan = session.get('plan', 'starter')
    max_size = PLANS[plan]['file_size']
    
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > max_size:
        return jsonify({'error': f'ファイルサイズが上限（{max_size // (1024*1024)}MB）を超えています。'}), 400
    
    try:
        # Save file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        
        # Create upload directory if not exists
        upload_dir = app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)
        
        # Extract text
        file_type = filename.rsplit('.', 1)[1].lower()
        content = extract_text_from_file(file_path, file_type)
        
        # Save to database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO files (user_id, filename, file_path, file_size, content, tenant_id)
            VALUES (?, ?, ?, ?, ?, NULL)
        ''', (user_id, filename, file_path, file_size, content))
        
        file_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Update usage
        update_usage(user_id, 'files', 1)
        
        # Update search index
        if search_engine:
            search_engine.add_document(str(file_id), content)
        
        # Log upload
        log_audit(user_id, 'file_uploaded', f'File: {filename}, Size: {file_size}', request.remote_addr)
        
        return jsonify({
            'success': True,
            'message': 'ファイルがアップロードされました。',
            'file_id': file_id,
            'extracted_length': len(content)
        })
    
    except Exception as e:
        logger.error(f"File upload error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'ファイルのアップロード中にエラーが発生しました: {str(e)}'}), 500

@app.route('/delete/<int:file_id>')
@login_required
def delete_file(file_id):
    """Delete uploaded file."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check file ownership
        cursor.execute('SELECT file_path FROM files WHERE id = ? AND user_id = ?', 
                      (file_id, session['user_id']))
        file = cursor.fetchone()
        
        if not file:
            flash('ファイルが見つかりません。', 'danger')
            return redirect(url_for('dashboard'))
        
        # Delete file from filesystem
        if file['file_path'] and os.path.exists(file['file_path']):
            os.remove(file['file_path'])
        
        # Delete from database
        cursor.execute('DELETE FROM files WHERE id = ?', (file_id,))
        conn.commit()
        conn.close()
        
        # Log deletion
        log_audit(session['user_id'], 'file_deleted', f'File ID: {file_id}', request.remote_addr)
        
        flash('ファイルが削除されました。', 'success')
        return redirect(url_for('dashboard'))
    
    except Exception as e:
        logger.error(f"File deletion error: {e}")
        flash('ファイルの削除中にエラーが発生しました。', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/download/<int:file_id>')
@login_required
def download_file(file_id):
    """Download uploaded file."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check file ownership
        cursor.execute('SELECT filename, file_path FROM files WHERE id = ? AND user_id = ?', 
                      (file_id, session['user_id']))
        file = cursor.fetchone()
        conn.close()
        
        if not file or not file['file_path'] or not os.path.exists(file['file_path']):
            flash('ファイルが見つかりません。', 'danger')
            return redirect(url_for('dashboard'))
        
        return send_file(file['file_path'], as_attachment=True, download_name=file['filename'])
    
    except Exception as e:
        logger.error(f"File download error: {e}")
        flash('ファイルのダウンロード中にエラーが発生しました。', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/landing')
def landing():
    """Landing page."""
    return render_template('landing.html')

@app.route('/pricing')
def pricing():
    """Pricing page with proper plan structure."""
    # 環境変数から価格IDを取得
    price_ids = {
        'starter': os.environ.get('STRIPE_PRICE_STARTER', 'price_1RqRVKJK1oCPIfH05pNIKXDY'),
        'pro': os.environ.get('STRIPE_PRICE_PRO', 'price_1RtPxZJK1oCPIfH0yQdTdGgK'),
        'enterprise': os.environ.get('STRIPE_PRICE_ENTERPRISE', 'price_1RtPxaJK1oCPIfH0mnGKNOvJ')
    }
    
    # テンプレート用のプラン構造
    template_plans = []
    
    for key, plan_data in PLANS.items():
        template_plans.append({
            'id': key,
            'name': plan_data['name'],
            'price': f"¥{plan_data['price']:,}",
            'price_id': price_ids[key],
            'features': plan_data['features'],
            'recommended': key == 'pro'  # Proプランをおすすめに
        })
    
    return render_template('pricing.html', plans=template_plans)

@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """Create Stripe checkout session."""
    try:
        plan = request.json.get('plan')
        
        if plan not in PLANS:
            return jsonify({'error': '無効なプランです。'}), 400
        
        user_id = session['user_id']
        
        # Get user's Stripe customer ID
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT stripe_customer_id FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        # Price IDs from environment variables
        price_ids = {
            'starter': os.environ.get('STRIPE_PRICE_STARTER'),
            'pro': os.environ.get('STRIPE_PRICE_PRO'),
            'enterprise': os.environ.get('STRIPE_PRICE_ENTERPRISE')
        }
        
        if not price_ids[plan]:
            return jsonify({'error': '価格設定が見つかりません。'}), 500
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=user['stripe_customer_id'],
            payment_method_types=['card'],
            line_items=[{
                'price': price_ids[plan],
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('pricing', _external=True),
            metadata={
                'user_id': str(user_id),
                'plan': plan
            },
            subscription_data={
                'trial_period_days': 7,
                'metadata': {
                    'user_id': str(user_id),
                    'plan': plan
                }
            }
        )
        
        return jsonify({'checkout_url': checkout_session.url})
    
    except Exception as e:
        logger.error(f"Checkout session error: {e}")
        return jsonify({'error': '決済処理中にエラーが発生しました。'}), 500

@app.route('/success')
@login_required
def success():
    """Handle successful subscription."""
    session_id = request.args.get('session_id')
    
    if not session_id:
        flash('無効なセッションです。', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        # Retrieve session from Stripe
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        
        if checkout_session.payment_status == 'paid':
            flash('サブスクリプションが開始されました！', 'success')
        else:
            flash('決済処理中です。完了後にメールでお知らせします。', 'info')
        
        return redirect(url_for('dashboard'))
    
    except Exception as e:
        logger.error(f"Success page error: {e}")
        flash('エラーが発生しました。', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/billing-portal', methods=['POST'])
@login_required
def billing_portal():
    """Redirect to Stripe customer portal."""
    try:
        user_id = session['user_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT stripe_customer_id FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if not user['stripe_customer_id']:
            return jsonify({'error': '顧客情報が見つかりません。'}), 400
        
        # Create portal session
        portal_session = stripe.billing_portal.Session.create(
            customer=user['stripe_customer_id'],
            return_url=url_for('dashboard', _external=True)
        )
        
        return jsonify({'url': portal_session.url})
    
    except Exception as e:
        logger.error(f"Billing portal error: {e}")
        return jsonify({'error': 'カスタマーポータルへのアクセス中にエラーが発生しました。'}), 500

@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events."""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        logger.error("Invalid Stripe payload")
        return '', 400
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid Stripe signature")
        return '', 400
    
    # Handle events
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_completed(session)
    
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        handle_subscription_updated(subscription)
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        handle_subscription_deleted(subscription)
    
    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        handle_payment_failed(invoice)
    
    return '', 200

def handle_checkout_completed(session):
    """Handle completed checkout session."""
    try:
        user_id = int(session['metadata']['user_id'])
        plan = session['metadata']['plan']
        subscription_id = session['subscription']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users
            SET subscription_status = 'active',
                plan = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (plan, user_id))
        conn.commit()
        conn.close()
        
        logger.info(f"Subscription activated for user {user_id}, plan: {plan}")
    
    except Exception as e:
        logger.error(f"Checkout completed handler error: {e}")

def handle_subscription_updated(subscription):
    """Handle subscription update."""
    try:
        user_id = int(subscription['metadata'].get('user_id', 0))
        status = subscription['status']
        
        if user_id:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users
                SET subscription_status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, user_id))
            conn.commit()
            conn.close()
        
        logger.info(f"Subscription updated for user {user_id}, status: {status}")
    
    except Exception as e:
        logger.error(f"Subscription update handler error: {e}")

def handle_subscription_deleted(subscription):
    """Handle subscription cancellation."""
    try:
        user_id = int(subscription['metadata'].get('user_id', 0))
        
        if user_id:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users
                SET subscription_status = 'cancelled',
                    plan = 'starter',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (user_id,))
            conn.commit()
            conn.close()
        
        logger.info(f"Subscription cancelled for user {user_id}")
    
    except Exception as e:
        logger.error(f"Subscription deletion handler error: {e}")

def handle_payment_failed(invoice):
    """Handle failed payment."""
    try:
        customer_id = invoice['customer']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, email FROM users
            WHERE stripe_customer_id = ?
        ''', (customer_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            # Log payment failure
            logger.warning(f"Payment failed for user {user['id']} ({user['email']})")
            
            # Could send notification email here
    
    except Exception as e:
        logger.error(f"Payment failed handler error: {e}")

@app.route('/analytics/basic')
@login_required
def basic_analytics():
    """Basic analytics dashboard."""
    try:
        user_id = session['user_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get conversation stats
        cursor.execute('''
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as message_count,
                SUM(CASE WHEN is_answered = 1 THEN 1 ELSE 0 END) as answered_count
            FROM conversations
            WHERE user_id = ?
            GROUP BY DATE(created_at)
            ORDER BY date DESC
            LIMIT 30
        ''', (user_id,))
        
        daily_stats = cursor.fetchall()
        
        # Get top questions
        cursor.execute('''
            SELECT 
                message,
                COUNT(*) as count
            FROM conversations
            WHERE user_id = ?
            GROUP BY message
            ORDER BY count DESC
            LIMIT 10
        ''', (user_id,))
        
        top_questions = cursor.fetchall()
        
        conn.close()
        
        return render_template('analytics_basic.html',
            daily_stats=daily_stats,
            top_questions=top_questions
        )
    
    except Exception as e:
        logger.error(f"Basic analytics error: {e}")
        flash('分析データの読み込み中にエラーが発生しました。', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/analytics/advanced')
@login_required
def advanced_analytics():
    """Advanced analytics dashboard (Pro/Enterprise only)."""
    if session.get('plan') not in ['pro', 'enterprise']:
        flash('この機能はプロフェッショナルプラン以上で利用可能です。', 'warning')
        return redirect(url_for('dashboard'))
    
    try:
        user_id = session['user_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get language distribution
        cursor.execute('''
            SELECT 
                language,
                COUNT(*) as count
            FROM conversations
            WHERE user_id = ? AND language IS NOT NULL
            GROUP BY language
        ''', (user_id,))
        
        language_stats = cursor.fetchall()
        
        # Get hourly distribution
        cursor.execute('''
            SELECT 
                strftime('%H', created_at) as hour,
                COUNT(*) as count
            FROM conversations
            WHERE user_id = ?
            GROUP BY hour
            ORDER BY hour
        ''', (user_id,))
        
        hourly_stats = cursor.fetchall()
        
        # Get response time stats
        cursor.execute('''
            SELECT 
                AVG(CASE WHEN is_answered = 1 THEN 1 ELSE 0 END) * 100 as response_rate,
                COUNT(*) as total_messages,
                COUNT(DISTINCT line_user_id) as unique_users
            FROM conversations
            WHERE user_id = ?
        ''', (user_id,))
        
        overall_stats = cursor.fetchone()
        
        conn.close()
        
        return render_template('analytics_advanced.html',
            language_stats=language_stats,
            hourly_stats=hourly_stats,
            overall_stats=overall_stats
        )
    
    except Exception as e:
        logger.error(f"Advanced analytics error: {e}")
        flash('分析データの読み込み中にエラーが発生しました。', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/export/analytics')
@login_required
def export_analytics():
    """Export analytics data as CSV."""
    try:
        user_id = session['user_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                created_at,
                message,
                response,
                is_answered,
                language
            FROM conversations
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        
        conversations = cursor.fetchall()
        conn.close()
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Date', 'Question', 'Response', 'Answered', 'Language'])
        
        for conv in conversations:
            writer.writerow([
                conv['created_at'],
                conv['message'],
                conv['response'] or 'N/A',
                'Yes' if conv['is_answered'] else 'No',
                conv['language'] or 'ja'
            ])
        
        # Create response
        output.seek(0)
        response = app.response_class(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=analytics_{datetime.now().strftime("%Y%m%d")}.csv'
            }
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Export error: {e}")
        flash('エクスポート中にエラーが発生しました。', 'danger')
        return redirect(url_for('basic_analytics'))

@app.route('/admin')
@admin_required
def admin():
    """Admin dashboard."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get system stats
        cursor.execute('SELECT COUNT(*) as count FROM users')
        total_users = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM users WHERE subscription_status = "active"')
        active_subscriptions = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM conversations WHERE DATE(created_at) = DATE("now")')
        today_messages = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM files')
        total_files = cursor.fetchone()['count']
        
        # Get recent users
        cursor.execute('''
            SELECT id, email, plan, subscription_status, created_at
            FROM users
            ORDER BY created_at DESC
            LIMIT 10
        ''')
        recent_users = cursor.fetchall()
        
        # Get recent activity
        cursor.execute('''
            SELECT user_id, action, details, created_at
            FROM audit_logs
            ORDER BY created_at DESC
            LIMIT 20
        ''')
        recent_activity = cursor.fetchall()
        
        conn.close()
        
        return render_template('admin.html',
            total_users=total_users,
            active_subscriptions=active_subscriptions,
            today_messages=today_messages,
            total_files=total_files,
            recent_users=recent_users,
            recent_activity=recent_activity
        )
    
    except Exception as e:
        logger.error(f"Admin dashboard error: {e}")
        flash('管理画面の読み込み中にエラーが発生しました。', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/settings')
@login_required
def settings():
    """User settings page."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get user info
        cursor.execute('''
            SELECT email, plan, subscription_status, created_at
            FROM users
            WHERE id = ?
        ''', (session['user_id'],))
        user = cursor.fetchone()
        
        # Get LINE accounts
        cursor.execute('''
            SELECT id, line_user_id, display_name, is_active, created_at
            FROM line_accounts
            WHERE user_id = ?
        ''', (session['user_id'],))
        line_accounts = cursor.fetchall()
        
        # Get API keys
        cursor.execute('''
            SELECT id, name, created_at, last_used_at
            FROM api_keys
            WHERE user_id = ? AND is_active = 1
        ''', (session['user_id'],))
        api_keys = cursor.fetchall()
        
        conn.close()
        
        return render_template('settings.html',
            user=user,
            line_accounts=line_accounts,
            api_keys=api_keys
        )
    
    except Exception as e:
        logger.error(f"Settings error: {e}")
        flash('設定の読み込み中にエラーが発生しました。', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/support')
@login_required
def support():
    """Support ticket system."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get user's tickets
        cursor.execute('''
            SELECT id, subject, status, priority, created_at, updated_at
            FROM support_tickets
            WHERE user_id = ?
            ORDER BY updated_at DESC
        ''', (session['user_id'],))
        tickets = cursor.fetchall()
        
        conn.close()
        
        return render_template('support.html', tickets=tickets)
    
    except Exception as e:
        logger.error(f"Support page error: {e}")
        flash('サポートページの読み込み中にエラーが発生しました。', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/terms')
def terms():
    """Terms of service page."""
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    """Privacy policy page."""
    return render_template('privacy.html')

# ========================================
# PDF変換機能統合（Doclingから）
# ========================================

@app.route('/api/convert-pdf', methods=['POST'])
@login_required
def convert_pdf():
    """PDFをMarkdownに変換（API）"""
    try:
        if not pdf_converter:
            return jsonify({'error': 'PDF変換エンジンが利用できません'}), 500
        
        if 'file' not in request.files:
            return jsonify({'error': 'ファイルがありません'}), 400
        
        file = request.files['file']
        
        if not file.filename.endswith('.pdf'):
            return jsonify({'error': 'PDFファイルのみ対応しています'}), 400
        
        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            file.save(tmp_file.name)
            tmp_path = tmp_file.name
        
        # 変換実行
        result = pdf_converter.convert_to_markdown(tmp_path)
        
        # ファイルをDBに保存
        user_id = session.get('user_id')
        cursor = get_db().cursor()
        cursor.execute(
            'INSERT INTO files (user_id, filename, content, file_size) VALUES (?, ?, ?, ?)',
            (user_id, file.filename, result['markdown'], len(result['markdown']))
        )
        get_db().commit()
        
        # 一時ファイル削除
        os.unlink(tmp_path)
        
        # 使用量追跡
        track_usage(user_id, 'files_uploaded')
        
        return jsonify({
            'success': True,
            'pages': result['pages'],
            'cost': result['cost'],
            'file_id': cursor.lastrowid
        })
    
    except Exception as e:
        logger.error(f"PDF変換エラー: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/dashboard/upload-pdf')
@login_required
def upload_pdf_page():
    """PDFアップロードページ"""
    return render_template('upload_pdf.html')

# ========================================
# RAGシステム統合
# ========================================

@app.route('/api/rag/add', methods=['POST'])
@login_required
def rag_add_document():
    """RAGシステムにドキュメントを追加"""
    try:
        data = request.json
        file_id = data.get('file_id')
        
        if not file_id:
            return jsonify({'error': 'file_idが必要です'}), 400
        
        user_id = session.get('user_id')
        
        # ファイル取得
        cursor = get_db().cursor()
        cursor.execute('SELECT filename, content FROM files WHERE id = ? AND user_id = ?', (file_id, user_id))
        row = cursor.fetchone()
        
        if not row:
            return jsonify({'error': 'ファイルが見つかりません'}), 404
        
        filename, content = row
        
        # RAGに追加
        rag = RAGSystem(user_id=user_id)
        chunks = rag.add_document(
            markdown_text=content,
            metadata={"filename": filename, "file_id": file_id}
        )
        
        return jsonify({
            'success': True,
            'chunks': chunks,
            'message': f'{chunks}チャンクをRAGに追加しました'
        })
    
    except Exception as e:
        logger.error(f"RAG追加エラー: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/rag/search', methods=['POST'])
@login_required
def rag_search():
    """RAG検索"""
    try:
        data = request.json
        query = data.get('query')
        
        if not query:
            return jsonify({'error': 'queryが必要です'}), 400
        
        user_id = session.get('user_id')
        
        # RAG検索
        rag = RAGSystem(user_id=user_id)
        result = rag.qa(query)
        
        # 使用量追跡
        track_usage(user_id, 'api_calls_made')
        
        return jsonify({
            'success': True,
            'answer': result['answer'],
            'sources': result['sources'],
            'cost': result['cost']
        })
    
    except Exception as e:
        logger.error(f"RAG検索エラー: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/rag/documents', methods=['GET'])
@login_required
def rag_list_documents():
    """RAGに登録されているドキュメント一覧"""
    try:
        user_id = session.get('user_id')
        rag = RAGSystem(user_id=user_id)
        documents = rag.get_all_documents()
        
        return jsonify({
            'success': True,
            'documents': documents
        })
    
    except Exception as e:
        logger.error(f"RAGドキュメント一覧エラー: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ========================================
# メール通知システム統合
# ========================================

@app.route('/api/notify/question', methods=['POST'])
@login_required
def notify_question():
    """質問通知メール送信（管理者向け）"""
    try:
        if not email_notifier:
            return jsonify({'error': 'メール通知システムが利用できません'}), 500
        
        data = request.json
        question = data.get('question')
        
        if not question:
            return jsonify({'error': 'questionが必要です'}), 400
        
        user_id = session.get('user_id')
        
        # ユーザー情報取得
        cursor = get_db().cursor()
        cursor.execute('SELECT email FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        
        if not row:
            return jsonify({'error': 'ユーザーが見つかりません'}), 404
        
        user_email = row[0]
        admin_email = os.getenv('SUPER_ADMIN_EMAIL', 'admin@manualbotai.com')
        
        # 管理者に通知
        success = email_notifier.send_question_notification(admin_email, question, user_email)
        
        return jsonify({
            'success': success,
            'message': '管理者に通知しました' if success else '通知に失敗しました'
        })
    
    except Exception as e:
        logger.error(f"質問通知エラー: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/notify/answer', methods=['POST'])
def notify_answer():
    """回答通知メール送信（ユーザー向け）"""
    try:
        if not email_notifier:
            return jsonify({'error': 'メール通知システムが利用できません'}), 500
        
        data = request.json
        user_email = data.get('user_email')
        question = data.get('question')
        answer = data.get('answer')
        
        if not all([user_email, question, answer]):
            return jsonify({'error': '必須パラメータが不足しています'}), 400
        
        # ユーザーに回答通知
        success = email_notifier.send_answer_notification(user_email, question, answer)
        
        return jsonify({
            'success': success,
            'message': 'ユーザーに通知しました' if success else '通知に失敗しました'
        })
    
    except Exception as e:
        logger.error(f"回答通知エラー: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ========================================
# マルチテナント対応
# ========================================

@app.route('/api/tenant/info')
@login_required
def tenant_info():
    """テナント情報取得"""
    try:
        if not multi_tenant:
            return jsonify({'error': 'マルチテナントシステムが利用できません'}), 500
        
        user_id = session.get('user_id')
        
        # ユーザーのtenant_id取得
        cursor = get_db().cursor()
        cursor.execute('SELECT tenant_id FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        
        if not row or not row[0]:
            return jsonify({'error': 'テナント情報がありません'}), 404
        
        tenant_id = row[0]
        
        # テナント情報取得
        cursor.execute('SELECT * FROM tenants WHERE id = ?', (tenant_id,))
        tenant = cursor.fetchone()
        
        if not tenant:
            return jsonify({'error': 'テナントが見つかりません'}), 404
        
        # 使用量取得
        usage = multi_tenant.get_tenant_usage(tenant_id)
        settings = multi_tenant.get_tenant_settings(tenant_id)
        limits_check = multi_tenant.check_usage_limits(tenant_id)
        
        return jsonify({
            'success': True,
            'tenant': dict(tenant),
            'usage': usage,
            'settings': settings,
            'limits_check': limits_check
        })
    
    except Exception as e:
        logger.error(f"テナント情報取得エラー: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tenant/settings', methods=['POST'])
@login_required
def update_tenant_settings():
    """テナント設定更新"""
    try:
        if not multi_tenant:
            return jsonify({'error': 'マルチテナントシステムが利用できません'}), 500
        
        user_id = session.get('user_id')
        data = request.json
        
        # テナントID取得
        cursor = get_db().cursor()
        cursor.execute('SELECT tenant_id FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        
        if not row or not row[0]:
            return jsonify({'error': 'テナント情報がありません'}), 404
        
        tenant_id = row[0]
        
        # 設定更新
        multi_tenant.update_tenant_settings(tenant_id, data)
        
        return jsonify({
            'success': True,
            'message': '設定を更新しました'
        })
    
    except Exception as e:
        logger.error(f"テナント設定更新エラー: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    """404 error handler."""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """500 error handler."""
    logger.error(f"Internal server error: {error}")
    return render_template('500.html'), 500

# Initialize database on startup with error handling
try:
    init_db()
    print("✅ Database initialized successfully")
except Exception as e:
    print(f"⚠️ Database initialization warning: {e}")
    # Continue anyway - database will be created on first use

# Root route for healthcheck
@app.route('/')
def root():
    """Root route for healthcheck."""
    return jsonify({'status': 'ok', 'service': 'Manual Bot AI'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

