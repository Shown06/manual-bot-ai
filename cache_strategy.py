from flask import Blueprint, request, jsonify, make_response
import redis
import json
import hashlib
from functools import wraps
from datetime import datetime, timedelta
import pickle

cache_bp = Blueprint('cache', __name__)

redis_client = redis.StrictRedis(
    host=os.environ.get('REDIS_HOST', 'localhost'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    decode_responses=False
)

CACHE_DURATIONS = {
    'user_profile': 300,
    'conversation_history': 60,
    'analytics_data': 3600,
    'file_list': 120,
    'subscription_info': 600,
    'static_content': 86400
}

def generate_cache_key(prefix, *args, **kwargs):
    key_parts = [prefix]
    key_parts.extend(str(arg) for arg in args)
    key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
    
    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()

def cache_response(cache_type, duration=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method != 'GET':
                return f(*args, **kwargs)
            
            cache_duration = duration or CACHE_DURATIONS.get(cache_type, 60)
            cache_key = generate_cache_key(
                cache_type,
                request.path,
                request.args.to_dict(),
                session.get('user_id', 'anonymous')
            )
            
            cached_data = redis_client.get(cache_key)
            
            if cached_data:
                try:
                    data = pickle.loads(cached_data)
                    response = make_response(jsonify(data))
                    response.headers['X-Cache'] = 'HIT'
                    response.headers['Cache-Control'] = f'private, max-age={cache_duration}'
                    return response
                except:
                    pass
            
            result = f(*args, **kwargs)
            
            if result.status_code == 200:
                try:
                    data = result.get_json()
                    redis_client.setex(
                        cache_key,
                        cache_duration,
                        pickle.dumps(data)
                    )
                    result.headers['X-Cache'] = 'MISS'
                    result.headers['Cache-Control'] = f'private, max-age={cache_duration}'
                except:
                    pass
            
            return result
            
        return decorated_function
    return decorator

def invalidate_cache(cache_type, *args, **kwargs):
    pattern = f"{cache_type}:*"
    
    for key in redis_client.scan_iter(match=pattern):
        redis_client.delete(key)

def invalidate_user_cache(user_id):
    patterns = [
        f"*:user:{user_id}:*",
        f"user_profile:*:{user_id}",
        f"subscription_info:*:{user_id}"
    ]
    
    for pattern in patterns:
        for key in redis_client.scan_iter(match=pattern):
            redis_client.delete(key)

@cache_bp.route('/cache/stats', methods=['GET'])
@require_admin
def get_cache_stats():
    info = redis_client.info()
    
    stats = {
        'used_memory': info.get('used_memory_human'),
        'connected_clients': info.get('connected_clients'),
        'total_commands_processed': info.get('total_commands_processed'),
        'keyspace_hits': info.get('keyspace_hits', 0),
        'keyspace_misses': info.get('keyspace_misses', 0),
        'hit_rate': 0
    }
    
    if stats['keyspace_hits'] + stats['keyspace_misses'] > 0:
        stats['hit_rate'] = stats['keyspace_hits'] / (stats['keyspace_hits'] + stats['keyspace_misses']) * 100
    
    return jsonify(stats)

@cache_bp.route('/cache/flush', methods=['POST'])
@require_admin
def flush_cache():
    cache_type = request.json.get('cache_type', 'all')
    
    if cache_type == 'all':
        redis_client.flushdb()
        message = "All cache flushed"
    else:
        invalidate_cache(cache_type)
        message = f"{cache_type} cache flushed"
    
    return jsonify({'message': message})
