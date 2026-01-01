from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
from contextlib import contextmanager
import json
from datetime import datetime
import time
from collections import defaultdict
import hashlib

# Try to import Google Generative AI (optional)
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except (ImportError, TypeError) as e:
    print(f"Warning: Google Generative AI not available: {e}")
    print("AI features will be disabled. Consider using Python 3.11 or 3.12 for full compatibility.")
    GEMINI_AVAILABLE = False
    genai = None

# Load environment variables
load_dotenv('ai_apis.env')

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'adet_rentease'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': int(os.getenv('DB_PORT', 3306))
}



# Configure Gemini AI
ai_model = None
GEMINI_API_KEY = os.getenv('GOOGLE_API_KEY')
if GEMINI_AVAILABLE and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        ai_model = genai.GenerativeModel('gemini-2.0-flash')
    except Exception as e:
        print(f"Warning: Failed to configure Gemini AI: {e}")
        ai_model = None

# Rate limiting for AI requests
class RateLimiter:
    def __init__(self, max_requests=10, time_window=60, min_delay=2):
        """
        Rate limiter for AI API requests
        max_requests: Maximum requests per time_window (seconds)
        time_window: Time window in seconds
        min_delay: Minimum delay between requests in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.min_delay = min_delay
        self.request_times = defaultdict(list)  # Track requests per user/IP
        self.last_request_time = {}  # Track last request time per user/IP
        self.cache = {}  # Simple cache for responses
        self.cache_ttl = 300  # Cache TTL in seconds (5 minutes)
    
    def get_user_id(self, request):
        """Get unique identifier for rate limiting (user_id or IP)"""
        if session.get('user_id'):
            return f"user_{session.get('user_id')}"
        return f"ip_{request.remote_addr}"
    
    def is_allowed(self, user_id):
        """Check if request is allowed based on rate limits"""
        now = time.time()
        
        # Check minimum delay between requests
        if user_id in self.last_request_time:
            time_since_last = now - self.last_request_time[user_id]
            if time_since_last < self.min_delay:
                return False, f"Please wait {self.min_delay - int(time_since_last)} seconds before making another request."
        
        # Clean old requests outside time window
        cutoff = now - self.time_window
        self.request_times[user_id] = [t for t in self.request_times[user_id] if t > cutoff]
        
        # Check if under rate limit
        if len(self.request_times[user_id]) >= self.max_requests:
            oldest_request = min(self.request_times[user_id])
            wait_time = int(self.time_window - (now - oldest_request))
            return False, f"Rate limit exceeded. Please wait {wait_time} seconds before making another request."
        
        # Record this request
        self.request_times[user_id].append(now)
        self.last_request_time[user_id] = now
        return True, None
    
    def get_cache_key(self, message):
        """Generate cache key from message"""
        return hashlib.md5(message.lower().strip().encode()).hexdigest()
    
    def get_cached(self, cache_key):
        """Get cached response if available and not expired"""
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                return cached_data
            else:
                # Expired, remove from cache
                del self.cache[cache_key]
        return None
    
    def set_cached(self, cache_key, response):
        """Cache a response"""
        self.cache[cache_key] = (response, time.time())
        # Clean old cache entries (keep only last 100)
        if len(self.cache) > 100:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]

# Initialize rate limiter: 10 requests per 60 seconds, minimum 2 seconds between requests
ai_rate_limiter = RateLimiter(max_requests=10, time_window=60, min_delay=2)

# Database connection context manager
@contextmanager
def get_db_cursor():
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        yield cursor
        conn.commit()
    except Error as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Authentication decorators
def require_owner(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or session.get('role') != 'owner':
            return jsonify({'error': 'Unauthorized. Owner access required.'}), 403
        return f(*args, **kwargs)
    return decorated_function

def require_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'error': 'Unauthorized. Please login.'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Utility functions
def format_query_response(results):
    if not results:
        return "No results found."
    
    if len(results) == 1:
        result = results[0]
        formatted = []
        for key, value in result.items():
            formatted.append(f"{key}: {value}")
        return "\n".join(formatted)
    
    # Multiple results - format as list
    formatted = []
    for i, result in enumerate(results[:10], 1):  # Limit to 10 results
        item = []
        for key, value in result.items():
            item.append(f"{key}: {value}")
        formatted.append(f"{i}. " + " | ".join(item))
    
    if len(results) > 10:
        formatted.append(f"\n... and {len(results) - 10} more results")
    
    return "\n".join(formatted)

def get_minimal_schema():
    """Returns minimal database schema for AI"""
    return """users(user_id, full_name, email, phone_number, role, date_registered)
properties(property_id, owner_id, property_name, description, location, available_rooms, date_posted)
rooms(room_id, property_id, room_type, available_tenants, monthly_rate, description, total_tenants, current_tenants, house_rules)
bookings(booking_id, tenant_id, room_id, start_date, end_date, status, created_at)
payments(payment_id, booking_id, tenant_id, room_id, amount_paid, payment_date, payment_method, status)
reviews(review_id, tenant_id, room_id, rating, comment, date_posted)"""

def replace_ids_with_names(results):
    """Replace IDs with human-readable names"""
    if not results:
        return results
    
    with get_db_cursor() as cursor:
        # Get all unique IDs
        user_ids = set()
        property_ids = set()
        room_ids = set()
        
        for result in results:
            if 'user_id' in result:
                user_ids.add(result['user_id'])
            if 'owner_id' in result:
                user_ids.add(result['owner_id'])
            if 'tenant_id' in result:
                user_ids.add(result['tenant_id'])
            if 'property_id' in result:
                property_ids.add(result['property_id'])
            if 'room_id' in result:
                room_ids.add(result['room_id'])
        
        # Fetch names
        user_names = {}
        if user_ids:
            placeholders = ','.join(['%s'] * len(user_ids))
            cursor.execute(f"SELECT user_id, full_name FROM users WHERE user_id IN ({placeholders})", list(user_ids))
            for row in cursor.fetchall():
                user_names[row['user_id']] = row['full_name']
        
        property_names = {}
        if property_ids:
            placeholders = ','.join(['%s'] * len(property_ids))
            cursor.execute(f"SELECT property_id, property_name FROM properties WHERE property_id IN ({placeholders})", list(property_ids))
            for row in cursor.fetchall():
                property_names[row['property_id']] = row['property_name']
        
        room_info = {}
        if room_ids:
            placeholders = ','.join(['%s'] * len(room_ids))
            cursor.execute(f"""
                SELECT r.room_id, r.room_type, p.property_name 
                FROM rooms r 
                JOIN properties p ON r.property_id = p.property_id 
                WHERE r.room_id IN ({placeholders})
            """, list(room_ids))
            for row in cursor.fetchall():
                room_info[row['room_id']] = f"{row['property_name']} - {row['room_type']}"
        
        # Replace in results
        for result in results:
            if 'user_id' in result and result['user_id'] in user_names:
                result['user_name'] = user_names[result['user_id']]
            if 'owner_id' in result and result['owner_id'] in user_names:
                result['owner_name'] = user_names[result['owner_id']]
            if 'tenant_id' in result and result['tenant_id'] in user_names:
                result['tenant_name'] = user_names[result['tenant_id']]
            if 'property_id' in result and result['property_id'] in property_names:
                result['property_name'] = property_names[result['property_id']]
            if 'room_id' in result and result['room_id'] in room_info:
                result['room_name'] = room_info[result['room_id']]
    
    return results

# ==================== PUBLIC ROUTES ====================

@app.route('/')
@app.route('/browse')
def browse():
    return render_template('browse.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/property/<int:property_id>')
def property_details(property_id):
    return render_template('property-details.html', property_id=property_id)

# ==================== API ROUTES ====================

# Public API Routes
@app.route('/api/properties', methods=['GET'])
def get_properties():
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT p.*, u.full_name as owner_name
                FROM properties p
                JOIN users u ON p.owner_id = u.user_id
                WHERE p.deleted_at IS NULL
                ORDER BY p.date_posted DESC
            """)
            properties = cursor.fetchall()
            
            # Get room counts for each property
            for prop in properties:
                cursor.execute("""
                    SELECT COUNT(*) as room_count
                    FROM rooms
                    WHERE property_id = %s AND deleted_at IS NULL AND available_tenants > 0
                """, (prop['property_id'],))
                room_result = cursor.fetchone()
                prop['available_rooms'] = room_result['room_count'] if room_result else 0
            
            return jsonify(properties)
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/properties/<int:property_id>', methods=['GET'])
def get_property(property_id):
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT p.*, u.full_name as owner_name, u.email as owner_email, u.phone_number as owner_phone
                FROM properties p
                JOIN users u ON p.owner_id = u.user_id
                WHERE p.property_id = %s AND p.deleted_at IS NULL
            """, (property_id,))
            property = cursor.fetchone()
            if not property:
                return jsonify({'error': 'Property not found'}), 404
            return jsonify(property)
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/properties/<int:property_id>/rooms', methods=['GET'])
def get_property_rooms(property_id):
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM rooms
                WHERE property_id = %s AND deleted_at IS NULL
                ORDER BY room_type, monthly_rate
            """, (property_id,))
            rooms = cursor.fetchall()
            return jsonify(rooms)
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/properties/<int:property_id>/amenities', methods=['GET'])
def get_property_amenities(property_id):
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT amenity_name FROM property_amenities
                WHERE property_id = %s
                ORDER BY amenity_name
            """, (property_id,))
            amenities = cursor.fetchall()
            return jsonify([a['amenity_name'] for a in amenities])
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/properties/<int:property_id>/images', methods=['GET'])
def get_property_images(property_id):
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT image_url, is_primary FROM property_images
                WHERE property_id = %s
                ORDER BY is_primary DESC, uploaded_at
            """, (property_id,))
            images = cursor.fetchall()
            return jsonify(images)
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rooms/<int:room_id>/images', methods=['GET'])
def get_room_images(room_id):
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT image_url, is_primary FROM room_images
                WHERE room_id = %s
                ORDER BY is_primary DESC, uploaded_at
            """, (room_id,))
            images = cursor.fetchall()
            return jsonify(images)
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Check for identity questions (no rate limit for these)
        identity_keywords = ['who are you', 'what are you', 'your name', 'your purpose']
        if any(keyword in message.lower() for keyword in identity_keywords):
            return jsonify({
                'response': "I'm RentEase AI Assistant. I help you find rental properties and answer questions about available rooms, bookings, and more. How can I assist you today?",
                'timestamp': None
            })
        
        # Check if Gemini API is configured
        if not ai_model:
            return jsonify({
                'response': 'AI service is not configured. Please contact the administrator.',
                'timestamp': None
            })
        
        # Rate limiting check
        user_id = ai_rate_limiter.get_user_id(request)
        allowed, error_msg = ai_rate_limiter.is_allowed(user_id)
        if not allowed:
            return jsonify({
                'response': error_msg,
                'timestamp': None
            })
        
        # Check cache first
        cache_key = ai_rate_limiter.get_cache_key(message)
        cached_response = ai_rate_limiter.get_cached(cache_key)
        if cached_response:
            return jsonify(cached_response)
        
        # Get minimal schema
        schema = get_minimal_schema()
        
        # Generate SQL query using AI
        prompt = f"""You are a SQL query generator for a rental property management system.

Database Schema:
{schema}

User Question: {message}

Generate a SQL SELECT query to answer this question. Important rules:
1. Only generate SELECT queries (no INSERT, UPDATE, DELETE)
2. Always filter out deleted records using: WHERE deleted_at IS NULL
3. Use proper JOINs when needed
4. Return only the SQL query, nothing else

SQL Query:"""
        
        try:
            # Single attempt with proper error handling
            response = ai_model.generate_content(prompt)
            sql_query = response.text.strip()
            
            # Remove markdown code blocks if present
            if sql_query.startswith('```'):
                sql_query = sql_query.split('```')[1]
                if sql_query.startswith('sql'):
                    sql_query = sql_query[3:]
                sql_query = sql_query.strip()
            
            # Validate query (SELECT only)
            if not sql_query.upper().startswith('SELECT'):
                return jsonify({
                    'response': 'I can only generate SELECT queries. Please ask about viewing data.',
                    'timestamp': None
                })
            
            # Execute query
            with get_db_cursor() as cursor:
                cursor.execute(sql_query)
                results = cursor.fetchall()
            
            # Replace IDs with names
            results = replace_ids_with_names(results)
            
            # Format response
            formatted_response = format_query_response(results)
            
            response_data = {
                'response': formatted_response,
                'timestamp': None
            }
            
            # Cache the response
            ai_rate_limiter.set_cached(cache_key, response_data)
            
            return jsonify(response_data)
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Handle rate limit errors specifically
            if '429' in error_str or 'quota' in error_str or 'rate limit' in error_str:
                return jsonify({
                    'response': 'The AI service is currently rate-limited. Please wait a few moments before trying again. You may have reached your API quota limit.',
                    'timestamp': None
                })
            
            # Fallback to local formatting if AI fails
            return jsonify({
                'response': f'I encountered an error processing your request: {str(e)}. Please try rephrasing your question.',
                'timestamp': None
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user-status', methods=['GET'])
def user_status():
    if session.get('logged_in'):
        return jsonify({
            'logged_in': True,
            'user': {
                'user_id': session.get('user_id'),
                'full_name': session.get('full_name'),
                'email': session.get('email'),
                'role': session.get('role')
            }
        })
    return jsonify({'logged_in': False})

@app.route('/api/schema', methods=['GET'])
def get_schema():
    return jsonify({'schema': get_minimal_schema()})

@app.route('/api/query', methods=['POST'])
def execute_query():
    """Execute SELECT queries only (for debugging/admin)"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query.upper().startswith('SELECT'):
            return jsonify({'error': 'Only SELECT queries are allowed'}), 400
        
        with get_db_cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
            return jsonify(results)
    except Error as e:
        return jsonify({'error': str(e)}), 500

# Authentication Routes
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT user_id, full_name, email, role
                FROM users
                WHERE email = %s AND password = %s
                AND role IN ('tenant', 'owner')
                AND deleted_at IS NULL
            """, (email, password))
            user = cursor.fetchone()
            
            if user:
                session['logged_in'] = True
                session['user_id'] = user['user_id']
                session['full_name'] = user['full_name']
                session['email'] = user['email']
                session['role'] = user['role']
                
                return jsonify({
                    'success': True,
                    'user': {
                        'user_id': user['user_id'],
                        'full_name': user['full_name'],
                        'email': user['email'],
                        'role': user['role']
                    }
                })
            else:
                return jsonify({'error': 'Invalid credentials'}), 401
    
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

# Owner-Only Routes
@app.route('/owner-dashboard')
def owner_dashboard():
    if not session.get('logged_in') or session.get('role') != 'owner':
        return redirect(url_for('login_page'))
    return render_template('owner-dashboard.html')

@app.route('/api/owner/properties', methods=['GET'])
@require_owner
def get_owner_properties():
    try:
        owner_id = session.get('user_id')
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT p.*, 
                       (SELECT COUNT(*) FROM rooms r 
                        WHERE r.property_id = p.property_id AND r.deleted_at IS NULL) as total_rooms,
                       (SELECT COUNT(*) FROM rooms r 
                        WHERE r.property_id = p.property_id AND r.deleted_at IS NULL AND r.available_tenants > 0) as available_rooms
                FROM properties p
                WHERE p.owner_id = %s AND p.deleted_at IS NULL
                ORDER BY p.date_posted DESC
            """, (owner_id,))
            properties = cursor.fetchall()
            return jsonify(properties)
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/owner/bookings', methods=['GET'])
@require_owner
def get_owner_bookings():
    try:
        owner_id = session.get('user_id')
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT b.*, 
                       u.full_name as tenant_name, 
                       u.email as tenant_email,
                       u.phone_number as tenant_phone,
                       r.room_type, r.monthly_rate,
                       p.property_name, p.location
                FROM bookings b
                JOIN rooms r ON b.room_id = r.room_id
                JOIN properties p ON r.property_id = p.property_id
                JOIN users u ON b.tenant_id = u.user_id
                WHERE p.owner_id = %s AND b.deleted_at IS NULL
                ORDER BY b.created_at DESC
            """, (owner_id,))
            bookings = cursor.fetchall()
            return jsonify(bookings)
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/owner/tenants', methods=['GET'])
@require_owner
def get_owner_tenants():
    try:
        owner_id = session.get('user_id')
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT
                    u.user_id as tenant_id,
                    u.full_name,
                    u.email,
                    u.phone_number,
                    COUNT(DISTINCT b.booking_id) as total_bookings,
                    COUNT(DISTINCT CASE WHEN b.status = 'approved' THEN b.booking_id END) as active_bookings,
                    GROUP_CONCAT(DISTINCT p.property_name SEPARATOR ', ') as properties_rented,
                    GROUP_CONCAT(DISTINCT r.room_type SEPARATOR ', ') as room_types
                FROM users u
                JOIN bookings b ON u.user_id = b.tenant_id
                JOIN rooms r ON b.room_id = r.room_id
                JOIN properties p ON r.property_id = p.property_id
                WHERE p.owner_id = %s AND b.deleted_at IS NULL AND u.deleted_at IS NULL
                GROUP BY u.user_id, u.full_name, u.email, u.phone_number
                ORDER BY u.full_name
            """, (owner_id,))
            tenants = cursor.fetchall()
            return jsonify(tenants)
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/owner/tenant-chat', methods=['POST'])
@require_owner
def owner_tenant_chat():
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        if not ai_model:
            return jsonify({
                'response': 'AI service is not configured.',
                'timestamp': None
            })
        
        # Rate limiting check
        user_id = ai_rate_limiter.get_user_id(request)
        allowed, error_msg = ai_rate_limiter.is_allowed(user_id)
        if not allowed:
            return jsonify({
                'response': error_msg,
                'timestamp': None
            })
        
        owner_id = session.get('user_id')
        
        # Fetch tenant data
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT
                    u.user_id as tenant_id,
                    u.full_name,
                    u.email,
                    u.phone_number,
                    COUNT(DISTINCT b.booking_id) as total_bookings,
                    COUNT(DISTINCT CASE WHEN b.status = 'approved' THEN b.booking_id END) as active_bookings,
                    GROUP_CONCAT(DISTINCT p.property_name SEPARATOR ', ') as properties_rented,
                    GROUP_CONCAT(DISTINCT r.room_type SEPARATOR ', ') as room_types,
                    AVG(r.monthly_rate) as avg_monthly_rate
                FROM users u
                JOIN bookings b ON u.user_id = b.tenant_id
                JOIN rooms r ON b.room_id = r.room_id
                JOIN properties p ON r.property_id = p.property_id
                WHERE p.owner_id = %s AND b.deleted_at IS NULL AND u.deleted_at IS NULL
                GROUP BY u.user_id, u.full_name, u.email, u.phone_number
            """, (owner_id,))
            tenants = cursor.fetchall()
        
        if not tenants:
            return jsonify({
                'response': 'You don\'t have any tenants yet.',
                'timestamp': None
            })
        
        # Format tenant data for AI
        tenant_data = json.dumps(tenants, indent=2, default=str)
        
        prompt = f"""You are an AI assistant helping a property owner understand their tenants.

Tenant Data (JSON):
{tenant_data}

Owner's Question: {message}

Answer the question using the tenant data provided. Use tenant names, provide statistics, and be helpful and concise.

Answer:"""
        
        try:
            response = ai_model.generate_content(prompt)
            answer = response.text.strip()
            
            return jsonify({
                'response': answer,
                'timestamp': None
            })
        except Exception as e:
            error_str = str(e).lower()
            
            # Handle rate limit errors specifically
            if '429' in error_str or 'quota' in error_str or 'rate limit' in error_str:
                return jsonify({
                    'response': 'The AI service is currently rate-limited. Please wait a few moments before trying again.',
                    'timestamp': None
                })
            
            return jsonify({
                'response': f'I encountered an error: {str(e)}',
                'timestamp': None
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/owner/property-stats', methods=['GET'])
@require_owner
def get_property_stats():
    try:
        owner_id = session.get('user_id')
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM vw_property_stats
                WHERE owner_id = %s
                ORDER BY property_name
            """, (owner_id,))
            stats = cursor.fetchall()
            return jsonify(stats)
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/owner/metrics', methods=['GET'])
@require_owner
def get_owner_metrics():
    """Get key metrics for owner dashboard"""
    try:
        owner_id = session.get('user_id')
        with get_db_cursor() as cursor:
            # Total properties
            cursor.execute("""
                SELECT COUNT(*) as count FROM properties 
                WHERE owner_id = %s AND deleted_at IS NULL
            """, (owner_id,))
            total_properties = cursor.fetchone()['count']
            
            # Total rooms
            cursor.execute("""
                SELECT COUNT(*) as count FROM rooms r
                JOIN properties p ON r.property_id = p.property_id
                WHERE p.owner_id = %s AND r.deleted_at IS NULL
            """, (owner_id,))
            total_rooms = cursor.fetchone()['count']
            
            # Available rooms
            cursor.execute("""
                SELECT COUNT(*) as count FROM rooms r
                JOIN properties p ON r.property_id = p.property_id
                WHERE p.owner_id = %s AND r.deleted_at IS NULL AND r.available_tenants > 0
            """, (owner_id,))
            available_rooms = cursor.fetchone()['count']
            
            # Total bookings
            cursor.execute("""
                SELECT COUNT(*) as count FROM bookings b
                JOIN rooms r ON b.room_id = r.room_id
                JOIN properties p ON r.property_id = p.property_id
                WHERE p.owner_id = %s AND b.deleted_at IS NULL
            """, (owner_id,))
            total_bookings = cursor.fetchone()['count']
            
            # Active bookings (approved)
            cursor.execute("""
                SELECT COUNT(*) as count FROM bookings b
                JOIN rooms r ON b.room_id = r.room_id
                JOIN properties p ON r.property_id = p.property_id
                WHERE p.owner_id = %s AND b.deleted_at IS NULL AND b.status = 'approved'
            """, (owner_id,))
            active_bookings = cursor.fetchone()['count']
            
            # Pending bookings
            cursor.execute("""
                SELECT COUNT(*) as count FROM bookings b
                JOIN rooms r ON b.room_id = r.room_id
                JOIN properties p ON r.property_id = p.property_id
                WHERE p.owner_id = %s AND b.deleted_at IS NULL AND b.status = 'pending'
            """, (owner_id,))
            pending_bookings = cursor.fetchone()['count']
            
            # Total tenants (unique)
            cursor.execute("""
                SELECT COUNT(DISTINCT b.tenant_id) as count FROM bookings b
                JOIN rooms r ON b.room_id = r.room_id
                JOIN properties p ON r.property_id = p.property_id
                WHERE p.owner_id = %s AND b.deleted_at IS NULL
            """, (owner_id,))
            total_tenants = cursor.fetchone()['count']
            
            # Occupancy rate
            occupancy_rate = (total_rooms - available_rooms) / total_rooms * 100 if total_rooms > 0 else 0
            
            return jsonify({
                'total_properties': total_properties,
                'total_rooms': total_rooms,
                'available_rooms': available_rooms,
                'occupied_rooms': total_rooms - available_rooms,
                'occupancy_rate': round(occupancy_rate, 1),
                'total_bookings': total_bookings,
                'active_bookings': active_bookings,
                'pending_bookings': pending_bookings,
                'total_tenants': total_tenants
            })
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/owner/financial-overview', methods=['GET'])
@require_owner
def get_financial_overview():
    """Get financial overview data for charts"""
    try:
        owner_id = session.get('user_id')
        with get_db_cursor() as cursor:
            # Total revenue (from payments)
            cursor.execute("""
                SELECT COALESCE(SUM(amount_paid), 0) as total_revenue,
                       COUNT(*) as total_payments
                FROM payments p
                JOIN bookings b ON p.booking_id = b.booking_id
                JOIN rooms r ON b.room_id = r.room_id
                JOIN properties prop ON r.property_id = prop.property_id
                WHERE prop.owner_id = %s AND p.status = 'confirmed'
            """, (owner_id,))
            revenue_data = cursor.fetchone()
            total_revenue = float(revenue_data['total_revenue']) if revenue_data['total_revenue'] else 0
            
            # Monthly revenue (last 6 months)
            cursor.execute("""
                SELECT DATE_FORMAT(payment_date, '%Y-%m') as month,
                       SUM(amount_paid) as revenue
                FROM payments p
                JOIN bookings b ON p.booking_id = b.booking_id
                JOIN rooms r ON b.room_id = r.room_id
                JOIN properties prop ON r.property_id = prop.property_id
                WHERE prop.owner_id = %s 
                  AND p.status = 'confirmed'
                  AND p.payment_date >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
                GROUP BY DATE_FORMAT(payment_date, '%Y-%m')
                ORDER BY month
            """, (owner_id,))
            monthly_revenue = cursor.fetchall()
            
            # Expected monthly revenue (from active bookings)
            cursor.execute("""
                SELECT COALESCE(SUM(r.monthly_rate), 0) as expected_revenue
                FROM bookings b
                JOIN rooms r ON b.room_id = r.room_id
                JOIN properties p ON r.property_id = p.property_id
                WHERE p.owner_id = %s 
                  AND b.status = 'approved'
                  AND b.deleted_at IS NULL
            """, (owner_id,))
            expected_revenue = cursor.fetchone()
            monthly_expected = float(expected_revenue['expected_revenue']) if expected_revenue['expected_revenue'] else 0
            
            # Revenue by property
            cursor.execute("""
                SELECT p.property_name,
                       COALESCE(SUM(pay.amount_paid), 0) as revenue
                FROM properties p
                LEFT JOIN rooms r ON p.property_id = r.property_id
                LEFT JOIN bookings b ON r.room_id = b.room_id
                LEFT JOIN payments pay ON b.booking_id = pay.booking_id AND pay.status = 'confirmed'
                WHERE p.owner_id = %s AND p.deleted_at IS NULL
                GROUP BY p.property_id, p.property_name
                ORDER BY revenue DESC
            """, (owner_id,))
            revenue_by_property = cursor.fetchall()
            
            # Pending payments
            cursor.execute("""
                SELECT COALESCE(SUM(ps.amount_due), 0) as pending_amount,
                       COUNT(*) as pending_count
                FROM payment_schedules ps
                JOIN bookings b ON ps.booking_id = b.booking_id
                JOIN rooms r ON b.room_id = r.room_id
                JOIN properties p ON r.property_id = p.property_id
                WHERE p.owner_id = %s 
                  AND ps.status = 'pending'
                  AND ps.due_date <= CURDATE()
            """, (owner_id,))
            pending_payments = cursor.fetchone()
            
            return jsonify({
                'total_revenue': total_revenue,
                'total_payments': revenue_data['total_payments'],
                'monthly_expected': monthly_expected,
                'monthly_revenue': monthly_revenue,
                'revenue_by_property': revenue_by_property,
                'pending_amount': float(pending_payments['pending_amount']) if pending_payments['pending_amount'] else 0,
                'pending_count': pending_payments['pending_count']
            })
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/owner/property-status', methods=['GET'])
@require_owner
def get_property_status():
    """Get property status table data"""
    try:
        owner_id = session.get('user_id')
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    p.property_id,
                    p.property_name,
                    p.location,
                    COUNT(DISTINCT r.room_id) as total_rooms,
                    COUNT(DISTINCT CASE WHEN r.available_tenants > 0 THEN r.room_id END) as available_rooms,
                    COUNT(DISTINCT CASE WHEN r.available_tenants = 0 THEN r.room_id END) as occupied_rooms,
                    COUNT(DISTINCT b.booking_id) as total_bookings,
                    COUNT(DISTINCT CASE WHEN b.status = 'approved' THEN b.booking_id END) as active_bookings,
                    COUNT(DISTINCT CASE WHEN b.status = 'pending' THEN b.booking_id END) as pending_bookings,
                    COALESCE(AVG(rev.rating), 0) as avg_rating,
                    COUNT(DISTINCT rev.review_id) as total_reviews,
                    p.date_posted
                FROM properties p
                LEFT JOIN rooms r ON p.property_id = r.property_id AND r.deleted_at IS NULL
                LEFT JOIN bookings b ON r.room_id = b.room_id AND b.deleted_at IS NULL
                LEFT JOIN reviews rev ON r.room_id = rev.room_id
                WHERE p.owner_id = %s AND p.deleted_at IS NULL
                GROUP BY p.property_id, p.property_name, p.location, p.date_posted
                ORDER BY p.property_name
            """, (owner_id,))
            properties = cursor.fetchall()
            
            # Calculate occupancy rate for each property
            for prop in properties:
                if prop['total_rooms'] > 0:
                    prop['occupancy_rate'] = round((prop['occupied_rooms'] / prop['total_rooms']) * 100, 1)
                else:
                    prop['occupancy_rate'] = 0
                prop['avg_rating'] = round(float(prop['avg_rating']), 1) if prop['avg_rating'] else 0
            
            return jsonify(properties)
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/owner/todos', methods=['GET'])
@require_owner
def get_todos():
    """Get to-do list for owner"""
    try:
        owner_id = session.get('user_id')
        # For now, we'll use a simple in-memory storage
        # In production, you'd want to store this in the database
        todos = session.get('todos', [])
        return jsonify(todos)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/owner/todos', methods=['POST'])
@require_owner
def create_todo():
    """Create a new to-do item"""
    try:
        data = request.get_json()
        todo = {
            'id': int(time.time() * 1000),  # Simple ID generation
            'title': data.get('title', ''),
            'description': data.get('description', ''),
            'priority': data.get('priority', 'medium'),
            'completed': False,
            'created_at': datetime.now().isoformat()
        }
        
        todos = session.get('todos', [])
        todos.append(todo)
        session['todos'] = todos
        
        return jsonify(todo)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/owner/todos/<int:todo_id>', methods=['PUT'])
@require_owner
def update_todo(todo_id):
    """Update a to-do item"""
    try:
        data = request.get_json()
        todos = session.get('todos', [])
        
        for i, todo in enumerate(todos):
            if todo['id'] == todo_id:
                todos[i].update({
                    'title': data.get('title', todo['title']),
                    'description': data.get('description', todo.get('description', '')),
                    'priority': data.get('priority', todo['priority']),
                    'completed': data.get('completed', todo['completed'])
                })
                session['todos'] = todos
                return jsonify(todos[i])
        
        return jsonify({'error': 'Todo not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/owner/todos/<int:todo_id>', methods=['DELETE'])
@require_owner
def delete_todo(todo_id):
    """Delete a to-do item"""
    try:
        todos = session.get('todos', [])
        todos = [t for t in todos if t['id'] != todo_id]
        session['todos'] = todos
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
