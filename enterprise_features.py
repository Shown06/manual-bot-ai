from flask import Blueprint, request, jsonify, redirect
import xml.etree.ElementTree as ET
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.utils import OneLogin_Saml2_Utils
import ldap
import jwt
from datetime import datetime, timedelta
import json
import uuid

enterprise_bp = Blueprint('enterprise', __name__)

SAML_SETTINGS = {
    "sp": {
        "entityId": "https://api.manualbotai.com",
        "assertionConsumerService": {
            "url": "https://api.manualbotai.com/saml/acs",
            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
        },
        "singleLogoutService": {
            "url": "https://api.manualbotai.com/saml/sls",
            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
        },
        "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
        "x509cert": "",
        "privateKey": ""
    },
    "idp": {
        "entityId": "",
        "singleSignOnService": {
            "url": "",
            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
        },
        "singleLogoutService": {
            "url": "",
            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
        },
        "x509cert": ""
    }
}

def init_saml_auth(req):
    auth = OneLogin_Saml2_Auth(req, SAML_SETTINGS)
    return auth

def prepare_flask_request(request):
    url_data = urlparse(request.url)
    return {
        'https': 'on' if request.scheme == 'https' else 'off',
        'http_host': request.headers.get('HTTP_HOST'),
        'server_port': url_data.port,
        'script_name': request.path,
        'get_data': request.args.copy(),
        'post_data': request.form.copy()
    }

@enterprise_bp.route('/saml/sso', methods=['GET'])
def saml_sso():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    return redirect(auth.login())

@enterprise_bp.route('/saml/acs', methods=['POST'])
def saml_acs():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    auth.process_response()
    
    errors = auth.get_errors()
    
    if not errors:
        session['samlUserdata'] = auth.get_attributes()
        session['samlNameId'] = auth.get_nameid()
        session['samlNameIdFormat'] = auth.get_nameid_format()
        session['samlNameIdNameQualifier'] = auth.get_nameid_nq()
        session['samlNameIdSPNameQualifier'] = auth.get_nameid_spnq()
        session['samlSessionIndex'] = auth.get_session_index()
        
        email = auth.get_nameid()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        
        if not user:
            cursor.execute('''
                INSERT INTO users (email, name, auth_provider, created_at)
                VALUES (?, ?, ?, ?)
            ''', (
                email,
                session['samlUserdata'].get('displayName', [email])[0],
                'saml',
                datetime.now()
            ))
            user_id = cursor.lastrowid
        else:
            user_id = user['id']
        
        session['user_id'] = user_id
        session['logged_in'] = True
        
        conn.commit()
        conn.close()
        
        return redirect('/dashboard')
    else:
        return jsonify({'errors': errors, 'last_error_reason': auth.get_last_error_reason()}), 400

@enterprise_bp.route('/ldap/auth', methods=['POST'])
def ldap_auth():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    ldap_server = os.environ.get('LDAP_SERVER', 'ldap://localhost:389')
    ldap_base_dn = os.environ.get('LDAP_BASE_DN', 'dc=example,dc=com')
    
    try:
        conn = ldap.initialize(ldap_server)
        conn.protocol_version = ldap.VERSION3
        
        user_dn = f"uid={username},{ldap_base_dn}"
        
        conn.simple_bind_s(user_dn, password)
        
        search_filter = f"(uid={username})"
        attrs = ['mail', 'cn', 'department', 'title']
        
        result = conn.search_s(ldap_base_dn, ldap.SCOPE_SUBTREE, search_filter, attrs)
        
        if result:
            user_data = result[0][1]
            email = user_data.get('mail', [b''])[0].decode()
            name = user_data.get('cn', [b''])[0].decode()
            department = user_data.get('department', [b''])[0].decode()
            
            db_conn = get_db_connection()
            cursor = db_conn.cursor()
            
            cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
            user = cursor.fetchone()
            
            if not user:
                cursor.execute('''
                    INSERT INTO users (email, name, department, auth_provider, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (email, name, department, 'ldap', datetime.now()))
                user_id = cursor.lastrowid
            else:
                user_id = user['id']
            
            access_token, refresh_token = generate_tokens(user_id)
            
            db_conn.commit()
            db_conn.close()
            
            return jsonify({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': {
                    'id': user_id,
                    'email': email,
                    'name': name,
                    'department': department
                }
            })
        
        conn.unbind()
        
    except ldap.INVALID_CREDENTIALS:
        return jsonify({'error': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

class RBAC:
    def __init__(self):
        self.roles = {
            'super_admin': {
                'permissions': ['*'],
                'description': 'Full system access'
            },
            'admin': {
                'permissions': [
                    'users.read', 'users.write', 'users.delete',
                    'billing.read', 'billing.write',
                    'analytics.read',
                    'settings.read', 'settings.write'
                ],
                'description': 'Administrative access'
            },
            'manager': {
                'permissions': [
                    'users.read', 'users.write',
                    'analytics.read',
                    'files.read', 'files.write'
                ],
                'description': 'Team management access'
            },
            'user': {
                'permissions': [
                    'profile.read', 'profile.write',
                    'files.read', 'files.write',
                    'conversations.read', 'conversations.write'
                ],
                'description': 'Standard user access'
            },
            'viewer': {
                'permissions': [
                    'profile.read',
                    'files.read',
                    'conversations.read',
                    'analytics.read'
                ],
                'description': 'Read-only access'
            }
        }
    
    def check_permission(self, user_role, required_permission):
        if user_role not in self.roles:
            return False
        
        role_permissions = self.roles[user_role]['permissions']
        
        if '*' in role_permissions:
            return True
        
        if required_permission in role_permissions:
            return True
        
        permission_parts = required_permission.split('.')
        for i in range(len(permission_parts)):
            wildcard_permission = '.'.join(permission_parts[:i+1]) + '.*'
            if wildcard_permission in role_permissions:
                return True
        
        return False
    
    def get_user_permissions(self, user_role):
        if user_role not in self.roles:
            return []
        
        return self.roles[user_role]['permissions']

rbac = RBAC()

def require_permission(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id')
            
            if not user_id:
                return jsonify({'error': 'Authentication required'}), 401
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT role FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            conn.close()
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            if not rbac.check_permission(user['role'], permission):
                return jsonify({'error': f'Permission denied: {permission} required'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

@enterprise_bp.route('/api/v1/<path:endpoint>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@limiter.limit("1000 per hour")
def api_gateway(endpoint):
    api_key = request.headers.get('X-API-Key')
    
    if not api_key:
        return jsonify({'error': 'API key required'}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM api_keys 
        WHERE key_hash = ? AND status = 'active'
    ''', (hashlib.sha256(api_key.encode()).hexdigest(),))
    
    key_data = cursor.fetchone()
    
    if not key_data:
        return jsonify({'error': 'Invalid API key'}), 401
    
    if key_data['expires_at'] and datetime.fromisoformat(key_data['expires_at']) < datetime.now():
        return jsonify({'error': 'API key expired'}), 401
    
    cursor.execute('''
        SELECT COUNT(*) as count 
        FROM api_usage 
        WHERE api_key_id = ? 
        AND timestamp >= datetime('now', '-1 hour')
    ''', (key_data['id'],))
    
    usage = cursor.fetchone()
    
    if usage['count'] >= key_data['rate_limit']:
        return jsonify({'error': 'Rate limit exceeded'}), 429
    
    cursor.execute('''
        INSERT INTO api_usage (api_key_id, endpoint, method, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (key_data['id'], endpoint, request.method, datetime.now()))
    
    conn.commit()
    conn.close()
    
    return handle_api_request(endpoint, request.method, key_data)

@enterprise_bp.route('/custom-domain/verify', methods=['POST'])
@require_permission('settings.write')
def verify_custom_domain():
    data = request.json
    domain = data.get('domain')
    
    if not domain:
        return jsonify({'error': 'Domain required'}), 400
    
    verification_token = f"manual-bot-ai-verify={uuid.uuid4()}"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO custom_domains (user_id, domain, verification_token, status)
        VALUES (?, ?, ?, ?)
    ''', (session.get('user_id'), domain, verification_token, 'pending'))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'domain': domain,
        'verification_token': verification_token,
        'dns_records': [
            {
                'type': 'TXT',
                'name': '_manualbotai',
                'value': verification_token
            },
            {
                'type': 'CNAME',
                'name': 'api',
                'value': 'custom.manualbotai.com'
            }
        ]
    })

@enterprise_bp.route('/sla/status', methods=['GET'])
@require_permission('analytics.read')
def sla_status():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            COUNT(CASE WHEN response_time < 200 THEN 1 END) * 100.0 / COUNT(*) as uptime_percentage,
            AVG(response_time) as avg_response_time,
            MAX(response_time) as max_response_time,
            COUNT(CASE WHEN status_code >= 500 THEN 1 END) as error_count
        FROM health_checks
        WHERE timestamp >= datetime('now', '-30 days')
    ''')
    
    sla_data = dict(cursor.fetchone())
    
    sla_data['sla_target'] = 99.9
    sla_data['sla_met'] = sla_data['uptime_percentage'] >= 99.9
    
    cursor.execute('''
        SELECT 
            DATE(timestamp) as date,
            COUNT(CASE WHEN response_time < 200 THEN 1 END) * 100.0 / COUNT(*) as daily_uptime
        FROM health_checks
        WHERE timestamp >= datetime('now', '-30 days')
        GROUP BY DATE(timestamp)
    ''')
    
    sla_data['daily_uptime'] = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify(sla_data)
