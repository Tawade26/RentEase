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
    from google import genai
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
ai_client = None
GEMINI_API_KEY = os.getenv('GOOGLE_API_KEY')
if GEMINI_AVAILABLE and GEMINI_API_KEY:
    try:
        ai_client = genai.Client(api_key=GEMINI_API_KEY)
        print(f"✓ Gemini AI client initialized successfully (API key length: {len(GEMINI_API_KEY) if GEMINI_API_KEY else 0})")
    except Exception as e:
        print(f"✗ Warning: Failed to configure Gemini AI: {e}")
        ai_client = None
else:
    if not GEMINI_AVAILABLE:
        print("✗ Gemini AI not available - library import failed")
    if not GEMINI_API_KEY:
        print("✗ Gemini AI not configured - GOOGLE_API_KEY not found in environment")

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

def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or session.get('role') != 'admin':
            return jsonify({'error': 'Unauthorized. Admin access required.'}), 403
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

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('logged_in') or session.get('role') != 'admin':
        return redirect(url_for('login_page'))
    return render_template('admin-dashboard.html')

@app.route('/property/<int:property_id>')
def property_details(property_id):
    return render_template('property-details.html', property_id=property_id)

@app.route('/messaging')
@require_login
def messaging_page():
    """Messaging page for tenants"""
    if session.get('role') != 'tenant':
        return redirect('/browse')
    return render_template('messaging.html')

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
                AND p.status = 'approved'
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
                SELECT p.*, p.owner_id, u.full_name as owner_name, u.email as owner_email, u.phone_number as owner_phone
                FROM properties p
                JOIN users u ON p.owner_id = u.user_id
                WHERE p.property_id = %s AND p.deleted_at IS NULL
            """, (property_id,))
            property = cursor.fetchone()
            if not property:
                return jsonify({'error': 'Property not found'}), 404
            
            # Calculate available rooms count
            cursor.execute("""
                SELECT COUNT(*) as room_count
                FROM rooms
                WHERE property_id = %s AND deleted_at IS NULL AND available_tenants > 0
            """, (property_id,))
            room_result = cursor.fetchone()
            property['available_rooms'] = room_result['room_count'] if room_result else 0
            
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
        if not ai_client:
            print("[AI] Chat request received but ai_client is None - AI not configured")
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
            # Use string directly for contents parameter
            print(f"[AI] Making API call to Gemini for chat query: {message[:50]}...")
            response = ai_client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            print(f"[AI] API call successful, response received")
            # Access response text - the response object has a .text attribute
            sql_query = response.text.strip() if hasattr(response, 'text') and response.text else str(response).strip()
            
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

@app.route('/api/user-profile', methods=['GET'])
@require_login
def get_user_profile():
    """Get current user's profile information"""
    try:
        user_id = session.get('user_id')
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT user_id, full_name, email, phone_number, role, 
                       status, role_change_request, date_registered
                FROM users
                WHERE user_id = %s AND deleted_at IS NULL
            """, (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            return jsonify({
                'user_id': user['user_id'],
                'full_name': user['full_name'],
                'email': user['email'],
                'phone_number': user['phone_number'],
                'role': user['role'],
                'status': user['status'],
                'role_change_request': user['role_change_request'],
                'date_registered': user['date_registered'].isoformat() if user['date_registered'] else None
            })
    except Error as e:
        return jsonify({'error': str(e)}), 500

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
                SELECT user_id, full_name, email, role, status, role_change_request
                FROM users
                WHERE email = %s AND password = %s
                AND deleted_at IS NULL
            """, (email, password))
            user = cursor.fetchone()
            
            if user:
                # Check if account is approved
                if user['status'] != 'approved':
                    if user['status'] == 'pending':
                        return jsonify({
                            'error': 'Your account is pending approval. Please wait for admin approval.',
                            'status': 'pending'
                        }), 403
                    elif user['status'] == 'rejected':
                        return jsonify({
                            'error': 'Your account has been rejected. Please contact administrator.',
                            'status': 'rejected'
                        }), 403
                
                # Allow admin, approved tenants, and approved owners
                if user['role'] == 'admin' or user['status'] == 'approved':
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
                    return jsonify({'error': 'Account not approved'}), 403
            else:
                return jsonify({'error': 'Invalid credentials'}), 401
    
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/tenant/active-booking', methods=['GET'])
@require_login 
def get_tenant_active_booking():
    """Check if tenant has an active booking"""
    try:
        tenant_id = session.get('user_id')
        role = session.get('role')
        
        if role != 'tenant':
            return jsonify({'error': 'Only tenants can check active bookings'}), 403
        
        with get_db_cursor() as cursor:
            # Check for approved bookings
            cursor.execute("""
                SELECT b.*, 
                       p.property_name, p.location,
                       r.room_type, r.monthly_rate
                FROM bookings b
                JOIN rooms r ON b.room_id = r.room_id
                JOIN properties p ON r.property_id = p.property_id
                WHERE b.tenant_id = %s 
                  AND b.status = 'approved'
                  AND b.deleted_at IS NULL
                ORDER BY b.created_at DESC
                LIMIT 1
            """, (tenant_id,))
            booking = cursor.fetchone()
            
            if booking:
                return jsonify({
                    'has_active_booking': True,
                    'booking': booking
                })
            else:
                return jsonify({
                    'has_active_booking': False,
                    'booking': None
                })
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bookings', methods=['POST'])
@require_login
def create_booking():
    """Create a booking request (tenant only)"""
    try:
        tenant_id = session.get('user_id')
        role = session.get('role')
        
        if role != 'tenant':
            return jsonify({'error': 'Only tenants can create bookings'}), 403
        
        # Check if tenant already has an active booking
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT booking_id FROM bookings
                WHERE tenant_id = %s 
                  AND status = 'approved'
                  AND deleted_at IS NULL
                LIMIT 1
            """, (tenant_id,))
            existing_booking = cursor.fetchone()
            
            if existing_booking:
                return jsonify({
                    'error': 'You already have an active booking. Please cancel your current booking before creating a new one.'
                }), 400
        
        data = request.get_json()
        room_id = data.get('room_id')
        start_date = data.get('start_date')
        end_date = data.get('end_date')  # Optional
        
        if not room_id or not start_date:
            return jsonify({'error': 'Room ID and start date are required'}), 400
        
        with get_db_cursor() as cursor:
            # Verify room exists and has availability
            cursor.execute("""
                SELECT r.room_id, r.available_tenants, r.property_id, p.owner_id
                FROM rooms r
                JOIN properties p ON r.property_id = p.property_id
                WHERE r.room_id = %s AND r.deleted_at IS NULL AND p.deleted_at IS NULL
            """, (room_id,))
            room = cursor.fetchone()
            
            if not room:
                return jsonify({'error': 'Room not found'}), 404
            
            if room['available_tenants'] <= 0:
                return jsonify({'error': 'Room is fully booked'}), 400
            
            # Create booking with pending status
            cursor.execute("""
                INSERT INTO bookings (tenant_id, room_id, start_date, end_date, status)
                VALUES (%s, %s, %s, %s, 'pending')
            """, (tenant_id, room_id, start_date, end_date if end_date else None))
            
            booking_id = cursor.lastrowid
            
            return jsonify({
                'success': True,
                'message': 'Booking request submitted successfully! Waiting for owner approval.',
                'booking_id': booking_id
            })
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user (defaults to tenant, requires approval)"""
    try:
        data = request.get_json()
        full_name = data.get('full_name', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        phone_number = data.get('phone_number', '').strip()
        role = data.get('role', 'tenant').strip().lower()  # Default to tenant
        
        # Validate role
        if role not in ['tenant', 'owner']:
            role = 'tenant'
        
        # Validate required fields
        if not full_name or not email or not password:
            return jsonify({'error': 'Full name, email, and password are required'}), 400
        
        # Validate email format
        if '@' not in email:
            return jsonify({'error': 'Invalid email format'}), 400
        
        with get_db_cursor() as cursor:
            # Check if email already exists
            cursor.execute("""
                SELECT user_id FROM users WHERE email = %s AND deleted_at IS NULL
            """, (email,))
            if cursor.fetchone():
                return jsonify({'error': 'Email already registered'}), 400
            
            # Create new user with pending status
            cursor.execute("""
                INSERT INTO users (full_name, email, password, phone_number, role, status)
                VALUES (%s, %s, %s, %s, %s, 'pending')
            """, (full_name, email, password, phone_number if phone_number else None, role))
            
            user_id = cursor.lastrowid
            
            return jsonify({
                'success': True,
                'message': 'Registration successful! Your account is pending approval. You will be notified once approved.',
                'user_id': user_id,
                'status': 'pending'
            })
    
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/request-role-change', methods=['POST'])
@require_login
def request_role_change():
    """Request to change role (tenant to owner)"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        new_role = data.get('role', 'owner').strip().lower()
        
        if new_role not in ['owner']:
            return jsonify({'error': 'Invalid role. Can only request owner role.'}), 400
        
        with get_db_cursor() as cursor:
            # Check current role
            cursor.execute("""
                SELECT role, status FROM users WHERE user_id = %s
            """, (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            if user['role'] == 'owner':
                return jsonify({'error': 'You are already an owner'}), 400
            
            if user['role'] != 'tenant':
                return jsonify({'error': 'Only tenants can request owner role'}), 400
            
            # Update role change request
            cursor.execute("""
                UPDATE users 
                SET role_change_request = %s
                WHERE user_id = %s
            """, (new_role, user_id))
            
            return jsonify({
                'success': True,
                'message': 'Role change request submitted. Waiting for admin approval.'
            })
    
    except Error as e:
        return jsonify({'error': str(e)}), 500

# Owner-Only Routes
@app.route('/owner-dashboard')
def owner_dashboard():
    if not session.get('logged_in') or session.get('role') != 'owner':
        return redirect(url_for('login_page'))
    return render_template('owner-dashboard.html')

@app.route('/upload-property')
def upload_property_page():
    if not session.get('logged_in') or session.get('role') != 'owner':
        return redirect(url_for('login_page'))
    return render_template('upload-property.html')

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
                ORDER BY 
                    CASE p.status 
                        WHEN 'pending' THEN 1 
                        WHEN 'approved' THEN 2 
                        WHEN 'rejected' THEN 3 
                    END,
                    p.date_posted DESC
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

@app.route('/api/owner/bookings/<int:booking_id>/status', methods=['PUT'])
@require_owner
def update_booking_status(booking_id):
    try:
        owner_id = session.get('user_id')
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['pending', 'approved', 'rejected', 'cancelled', 'completed']:
            return jsonify({'error': 'Invalid status'}), 400
        
        with get_db_cursor() as cursor:
            # Verify the booking belongs to this owner
            cursor.execute("""
                SELECT b.booking_id
                FROM bookings b
                JOIN rooms r ON b.room_id = r.room_id
                JOIN properties p ON r.property_id = p.property_id
                WHERE b.booking_id = %s AND p.owner_id = %s AND b.deleted_at IS NULL
            """, (booking_id, owner_id))
            
            booking = cursor.fetchone()
            if not booking:
                return jsonify({'error': 'Booking not found or unauthorized'}), 404
            
            # Get old status for trigger logic
            cursor.execute("""
                SELECT status FROM bookings WHERE booking_id = %s
            """, (booking_id,))
            old_booking = cursor.fetchone()
            old_status = old_booking['status'] if old_booking else None
            
            # Update booking status (removed updated_at as it doesn't exist in schema)
            cursor.execute("""
                UPDATE bookings
                SET status = %s
                WHERE booking_id = %s
            """, (new_status, booking_id))
            
            # The database trigger will automatically:
            # 1. Log the status change to booking_history
            # 2. Update room availability (available_tenants, current_tenants) if approved/rejected
            
            return jsonify({
                'success': True, 
                'message': f'Booking status updated to {new_status}',
                'old_status': old_status,
                'new_status': new_status
            })
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
        
        if not ai_client:
            print("[AI] Owner tenant chat request received but ai_client is None - AI not configured")
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
            # Use string directly for contents parameter
            print(f"[AI] Making API call to Gemini for owner tenant chat: {message[:50]}...")
            response = ai_client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            print(f"[AI] API call successful, response received")
            # Access response text - the response object has a .text attribute
            answer = response.text.strip() if hasattr(response, 'text') and response.text else str(response).strip()
            
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

# Admin Routes
@app.route('/api/admin/pending-users', methods=['GET'])
@require_admin
def get_pending_users():
    """Get all pending user registrations"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT user_id, full_name, email, phone_number, role, status, 
                       role_change_request, date_registered
                FROM users
                WHERE status = 'pending' AND deleted_at IS NULL
                ORDER BY date_registered DESC
            """)
            users = cursor.fetchall()
            return jsonify(users)
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/role-change-requests', methods=['GET'])
@require_admin
def get_role_change_requests():
    """Get all role change requests"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT user_id, full_name, email, phone_number, role, 
                       role_change_request, date_registered
                FROM users
                WHERE role_change_request IS NOT NULL 
                  AND status = 'approved'
                  AND deleted_at IS NULL
                ORDER BY date_registered DESC
            """)
            requests = cursor.fetchall()
            return jsonify(requests)
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/approve-user/<int:user_id>', methods=['POST'])
@require_admin
def approve_user(user_id):
    """Approve a user account"""
    try:
        admin_id = session.get('user_id')
        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE users 
                SET status = 'approved',
                    approved_by = %s,
                    approved_at = NOW()
                WHERE user_id = %s AND deleted_at IS NULL
            """, (admin_id, user_id))
            
            if cursor.rowcount == 0:
                return jsonify({'error': 'User not found'}), 404
            
            return jsonify({
                'success': True,
                'message': 'User approved successfully'
            })
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/reject-user/<int:user_id>', methods=['POST'])
@require_admin
def reject_user(user_id):
    """Reject a user account"""
    try:
        admin_id = session.get('user_id')
        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE users 
                SET status = 'rejected',
                    approved_by = %s,
                    approved_at = NOW()
                WHERE user_id = %s AND deleted_at IS NULL
            """, (admin_id, user_id))
            
            if cursor.rowcount == 0:
                return jsonify({'error': 'User not found'}), 404
            
            return jsonify({
                'success': True,
                'message': 'User rejected successfully'
            })
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/approve-role-change/<int:user_id>', methods=['POST'])
@require_admin
def approve_role_change(user_id):
    """Approve a role change request"""
    try:
        admin_id = session.get('user_id')
        with get_db_cursor() as cursor:
            # Get the requested role
            cursor.execute("""
                SELECT role_change_request FROM users 
                WHERE user_id = %s AND role_change_request IS NOT NULL
            """, (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'error': 'Role change request not found'}), 404
            
            new_role = user['role_change_request']
            
            # Update user role and clear request
            cursor.execute("""
                UPDATE users 
                SET role = %s,
                    role_change_request = NULL,
                    approved_by = %s
                WHERE user_id = %s AND deleted_at IS NULL
            """, (new_role, admin_id, user_id))
            
            return jsonify({
                'success': True,
                'message': f'Role changed to {new_role} successfully'
            })
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/reject-role-change/<int:user_id>', methods=['POST'])
@require_admin
def reject_role_change(user_id):
    """Reject a role change request"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE users 
                SET role_change_request = NULL
                WHERE user_id = %s AND deleted_at IS NULL
            """, (user_id,))
            
            if cursor.rowcount == 0:
                return jsonify({'error': 'User not found'}), 404
            
            return jsonify({
                'success': True,
                'message': 'Role change request rejected'
            })
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/stats', methods=['GET'])
@require_admin
def get_admin_stats():
    """Get admin dashboard statistics"""
    try:
        with get_db_cursor() as cursor:
            # Pending users count
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE status = 'pending' AND deleted_at IS NULL")
            pending_users = cursor.fetchone()['count']
            
            # Role change requests count
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE role_change_request IS NOT NULL AND status = 'approved'")
            role_requests = cursor.fetchone()['count']
            
            # Total users
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE deleted_at IS NULL")
            total_users = cursor.fetchone()['count']
            
            # Users by role
            cursor.execute("""
                SELECT role, COUNT(*) as count 
                FROM users 
                WHERE deleted_at IS NULL AND status = 'approved'
                GROUP BY role
            """)
            users_by_role = cursor.fetchall()
            
            # Pending properties count
            cursor.execute("SELECT COUNT(*) as count FROM properties WHERE status = 'pending' AND deleted_at IS NULL")
            pending_properties = cursor.fetchone()['count']
            
            return jsonify({
                'pending_users': pending_users,
                'role_requests': role_requests,
                'pending_properties': pending_properties,
                'total_users': total_users,
                'users_by_role': users_by_role
            })
    except Error as e:
        return jsonify({'error': str(e)}), 500

# Owner Property Management Routes
@app.route('/api/owner/create-property', methods=['POST'])
@require_owner
def create_property():
    """Create a new property (pending approval)"""
    try:
        owner_id = session.get('user_id')
        data = request.get_json()
        
        property_name = data.get('property_name', '').strip()
        description = data.get('description', '').strip()
        location = data.get('location', '').strip()
        amenities = data.get('amenities', [])  # Array of amenity names
        
        if not property_name or not location:
            return jsonify({'error': 'Property name and location are required'}), 400
        
        with get_db_cursor() as cursor:
            # Create property with pending status
            cursor.execute("""
                INSERT INTO properties (owner_id, property_name, description, location, status)
                VALUES (%s, %s, %s, %s, 'pending')
            """, (owner_id, property_name, description, location))
            
            property_id = cursor.lastrowid
            
            # Add amenities if provided
            if amenities and isinstance(amenities, list):
                for amenity in amenities:
                    if amenity.strip():
                        cursor.execute("""
                            INSERT INTO property_amenities (property_id, amenity_name)
                            VALUES (%s, %s)
                        """, (property_id, amenity.strip()))
            
            return jsonify({
                'success': True,
                'message': 'Property created successfully! Waiting for admin approval.',
                'property_id': property_id
            })
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/owner/add-room', methods=['POST'])
@require_owner
def add_room():
    """Add a room to a property"""
    try:
        owner_id = session.get('user_id')
        data = request.get_json()
        
        property_id = data.get('property_id')
        room_type = data.get('room_type', 'Single')
        monthly_rate = data.get('monthly_rate')
        description = data.get('description', '').strip()
        total_tenants = data.get('total_tenants', 1)
        house_rules = data.get('house_rules', '').strip()
        
        if not property_id or not monthly_rate:
            return jsonify({'error': 'Property ID and monthly rate are required'}), 400
        
        if room_type not in ['Single', 'Shared']:
            return jsonify({'error': 'Room type must be Single or Shared'}), 400
        
        # Verify property belongs to owner
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT property_id FROM properties 
                WHERE property_id = %s AND owner_id = %s AND deleted_at IS NULL
            """, (property_id, owner_id))
            if not cursor.fetchone():
                return jsonify({'error': 'Property not found or access denied'}), 403
            
            # Create room
            cursor.execute("""
                INSERT INTO rooms (property_id, room_type, monthly_rate, description, 
                                 total_tenants, available_tenants, house_rules)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (property_id, room_type, monthly_rate, description, 
                  total_tenants, total_tenants, house_rules))
            
            room_id = cursor.lastrowid
            
            return jsonify({
                'success': True,
                'message': 'Room added successfully',
                'room_id': room_id
            })
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/owner/pending-properties', methods=['GET'])
@require_owner
def get_pending_properties():
    """Get owner's pending properties"""
    try:
        owner_id = session.get('user_id')
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT p.*, 
                       (SELECT COUNT(*) FROM rooms r 
                        WHERE r.property_id = p.property_id AND r.deleted_at IS NULL) as total_rooms
                FROM properties p
                WHERE p.owner_id = %s 
                  AND p.status = 'pending'
                  AND p.deleted_at IS NULL
                ORDER BY p.date_posted DESC
            """, (owner_id,))
            properties = cursor.fetchall()
            return jsonify(properties)
    except Error as e:
        return jsonify({'error': str(e)}), 500

# Admin Property Approval Routes
@app.route('/api/admin/pending-properties', methods=['GET'])
@require_admin
def get_admin_pending_properties():
    """Get all pending properties for admin approval"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT p.*, u.full_name as owner_name, u.email as owner_email,
                       (SELECT COUNT(*) FROM rooms r 
                        WHERE r.property_id = p.property_id AND r.deleted_at IS NULL) as total_rooms
                FROM properties p
                JOIN users u ON p.owner_id = u.user_id
                WHERE p.status = 'pending' AND p.deleted_at IS NULL
                ORDER BY p.date_posted DESC
            """)
            properties = cursor.fetchall()
            return jsonify(properties)
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/approve-property/<int:property_id>', methods=['POST'])
@require_admin
def approve_property(property_id):
    """Approve a property"""
    try:
        admin_id = session.get('user_id')
        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE properties 
                SET status = 'approved',
                    approved_by = %s,
                    approved_at = NOW()
                WHERE property_id = %s AND deleted_at IS NULL
            """, (admin_id, property_id))
            
            if cursor.rowcount == 0:
                return jsonify({'error': 'Property not found'}), 404
            
            return jsonify({
                'success': True,
                'message': 'Property approved successfully'
            })
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/reject-property/<int:property_id>', methods=['POST'])
@require_admin
def reject_property(property_id):
    """Reject a property"""
    try:
        admin_id = session.get('user_id')
        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE properties 
                SET status = 'rejected',
                    approved_by = %s,
                    approved_at = NOW()
                WHERE property_id = %s AND deleted_at IS NULL
            """, (admin_id, property_id))
            
            if cursor.rowcount == 0:
                return jsonify({'error': 'Property not found'}), 404
            
            return jsonify({
                'success': True,
                'message': 'Property rejected'
            })
    except Error as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
