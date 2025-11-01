from flask import Blueprint, request, jsonify, g
from functools import wraps
import jwt
import redis
import hashlib
import hmac
import re
from datetime import datetime, timedelta
import secrets
import ipaddress
from werkzeug.security import generate_password_hash, check_password_hash
import bleach
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import pyotp
import qrcode
import io
import base64

security_bp = Blueprint('security', __name__)

redis_client = redis.StrictRedis(
    host=os.environ.get('REDIS_HOST', 'localhost'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    decode_responses=True
)

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=f"redis://{os.environ.get('REDIS_HOST', 'localhost')}:6379"
)

SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https:; font-src 'self' https://fonts.gstatic.com;",
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
}

JWT_ALGORITHM = 'HS256'
JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

SQL_INJECTION_PATTERNS = [
    r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)",
    r"(--|#|\/\*|\*\/)",
    r"(\bor\b\s*\d+\s*=\s*\d+)",
    r"(\band\b\s*\d+\s*=\s*\d+)",
    r"(';|';--|';#|';\/\*)",
    r"(\bwaitfor\s+delay\b)",
    r"(\bbenchmark\s*\()",
    r"(\bsleep\s*\()"
]

XSS_PATTERNS = [
    r"<script[^>]*>.*?</script>",
    r"javascript:",
    r"on\w+\s*=",
    r"<iframe[^>]*>",
    r"<object[^>]*>",
    r"<embed[^>]*>",
    r"<img[^>]*onerror\s*=",
    r"<svg[^>]*onload\s*="
]

@security_bp.before_app_request
def apply_security_headers():
    @after_this_request
    def set_security_headers(response):
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        return response

def validate_input(data, input_type='general'):
    if not data:
        return None
        
    if isinstance(data, str):
        for pattern in SQL_INJECTION_PATTERNS:
            if re.search(pattern, data, re.IGNORECASE):
                raise ValueError("Potential SQL injection detected")
        
        for pattern in XSS_PATTERNS:
            if re.search(pattern, data, re.IGNORECASE):
                raise ValueError("Potential XSS attack detected")
        
        if input_type == 'html':
            allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li']
            allowed_attributes = {'a': ['href', 'title']}
            data = bleach.clean(data, tags=allowed_tags, attributes=allowed_attributes)
        else:
            data = bleach.clean(data, tags=[], strip=True)
    
    return data

def generate_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return session['csrf_token']

def validate_csrf_token(token):
    return token and token == session.get('csrf_token')

@security_bp.route('/csrf-token', methods=['GET'])
def get_csrf_token():
    return jsonify({'csrf_token': generate_csrf_token()})

def require_csrf_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
            if not validate_csrf_token(token):
                return jsonify({'error': 'Invalid CSRF token'}), 403
        return f(*args, **kwargs)
    return decorated_function

def generate_tokens(user_id):
    access_payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + JWT_ACCESS_TOKEN_EXPIRES,
        'type': 'access'
    }
    refresh_payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + JWT_REFRESH_TOKEN_EXPIRES,
        'type': 'refresh'
    }
    
    access_token = jwt.encode(access_payload, app.config['SECRET_KEY'], algorithm=JWT_ALGORITHM)
    refresh_token = jwt.encode(refresh_payload, app.config['SECRET_KEY'], algorithm=JWT_ALGORITHM)
    
    redis_client.setex(
        f"refresh_token:{user_id}",
        JWT_REFRESH_TOKEN_EXPIRES,
        refresh_token
    )
    
    return access_token, refresh_token

@security_bp.route('/refresh-token', methods=['POST'])
def refresh_access_token():
    data = request.json
    refresh_token = data.get('refresh_token')
    
    if not refresh_token:
        return jsonify({'error': 'Refresh token required'}), 400
    
    try:
        payload = jwt.decode(refresh_token, app.config['SECRET_KEY'], algorithms=[JWT_ALGORITHM])
        
        if payload.get('type') != 'refresh':
            return jsonify({'error': 'Invalid token type'}), 401
        
        user_id = payload.get('user_id')
        stored_token = redis_client.get(f"refresh_token:{user_id}")
        
        if stored_token != refresh_token:
            return jsonify({'error': 'Invalid refresh token'}), 401
        
        access_token, new_refresh_token = generate_tokens(user_id)
        
        return jsonify({
            'access_token': access_token,
            'refresh_token': new_refresh_token
        })
        
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Refresh token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid refresh token'}), 401

def check_ip_whitelist(user_id, ip_address):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT ip_whitelist FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    if not user or not user['ip_whitelist']:
        return True
    
    whitelist = json.loads(user['ip_whitelist'])
    
    for allowed_ip in whitelist:
        if '/' in allowed_ip:
            if ipaddress.ip_address(ip_address) in ipaddress.ip_network(allowed_ip):
                return True
        elif allowed_ip == ip_address:
            return True
    
    return False

@security_bp.route('/2fa/enable', methods=['POST'])
@require_auth
def enable_2fa():
    user_id = session.get('user_id')
    
    secret = pyotp.random_base32()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE users SET two_factor_secret = ? WHERE id = ?
    ''', (secret, user_id))
    
    cursor.execute('SELECT email FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    conn.commit()
    conn.close()
    
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user['email'],
        issuer_name='Manual Bot AI'
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    
    qr_code = base64.b64encode(buf.getvalue()).decode()
    
    return jsonify({
        'secret': secret,
        'qr_code': f'data:image/png;base64,{qr_code}'
    })

@security_bp.route('/2fa/verify', methods=['POST'])
@require_auth
def verify_2fa():
    data = request.json
    code = data.get('code')
    
    if not code:
        return jsonify({'error': '2FA code required'}), 400
    
    user_id = session.get('user_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT two_factor_secret FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    if not user or not user['two_factor_secret']:
        return jsonify({'error': '2FA not enabled'}), 400
    
    totp = pyotp.TOTP(user['two_factor_secret'])
    
    if totp.verify(code, valid_window=1):
        cursor.execute('''
            UPDATE users SET two_factor_enabled = 1 WHERE id = ?
        ''', (user_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'message': '2FA enabled successfully'})
    else:
        conn.close()
        return jsonify({'error': 'Invalid 2FA code'}), 400

class WAF:
    def __init__(self):
        self.blocked_ips = set()
        self.rate_limits = {}
        
    def check_request(self, request):
        ip = request.remote_addr
        
        if ip in self.blocked_ips:
            return False, "IP blocked"
        
        if self.check_rate_limit(ip):
            return False, "Rate limit exceeded"
        
        if self.check_malicious_patterns(request):
            return False, "Malicious pattern detected"
        
        return True, None
    
    def check_rate_limit(self, ip):
        current_time = datetime.now()
        
        if ip not in self.rate_limits:
            self.rate_limits[ip] = []
        
        self.rate_limits[ip] = [
            t for t in self.rate_limits[ip] 
            if current_time - t < timedelta(minutes=1)
        ]
        
        self.rate_limits[ip].append(current_time)
        
        if len(self.rate_limits[ip]) > 100:
            self.blocked_ips.add(ip)
            return True
        
        return False
    
    def check_malicious_patterns(self, request):
        user_agent = request.headers.get('User-Agent', '')
        
        malicious_agents = [
            'sqlmap', 'nikto', 'scanner', 'havij', 'acunetix'
        ]
        
        for agent in malicious_agents:
            if agent.lower() in user_agent.lower():
                return True
        
        return False

waf = WAF()

@security_bp.before_app_request
def waf_check():
    allowed, reason = waf.check_request(request)
    if not allowed:
        abort(403, description=reason)
