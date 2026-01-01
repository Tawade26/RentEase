
# **RentEase - Complete System Flow Documentation**

## **1. SYSTEM OVERVIEW**

RentEase is a rental property management system with an AI assistant. It helps tenants find properties and helps owners manage properties, bookings, and tenants.

### **1.1 Technology Stack**
- **Backend**: Flask (Python)
- **Database**: MySQL/MariaDB
- **AI Integration**: Google Gemini 2.5 Flash
- **Frontend**: HTML, JavaScript, Bootstrap 5
- **Authentication**: Session-based

### **1.2 Core Features**
- Property browsing and search
- AI chat assistant for property queries
- User authentication (Tenant/Owner)
- Property management (Owner)
- Booking management
- Tenant management (Owner)
- Payment tracking
- Reviews and ratings

---

## **2. USER ROLES & PERMISSIONS**

### **2.1 Guest User (Not Logged In)**
- Browse properties
- View property details
- Use AI chat for property queries
- Cannot book rooms
- Cannot access owner features

### **2.2 Tenant**
- All guest permissions
- Book rooms
- View own bookings
- Submit reviews
- Cannot access owner dashboard

### **2.3 Owner**
- All tenant permissions
- Access owner dashboard
- Manage properties
- View/manage bookings
- View tenant information
- Use tenant-specific AI chat
- View property statistics

### **2.4 Admin**
- Full system access (not fully implemented in current version)

---

## **3. DATABASE SCHEMA**

### **3.1 Core Tables**

**users**
- `user_id` (PK), `full_name`, `email`, `password`, `phone_number`, `role` (tenant/owner/admin), `date_registered`, `deleted_at`

**properties**
- `property_id` (PK), `owner_id` (FK → users), `property_name`, `description`, `location`, `available_rooms`, `date_posted`, `deleted_at`

**rooms**
- `room_id` (PK), `property_id` (FK → properties), `room_type` (Single/Shared), `available_tenants`, `monthly_rate`, `description`, `total_tenants`, `current_tenants`, `house_rules`, `created_at`, `deleted_at`

**bookings**
- `booking_id` (PK), `tenant_id` (FK → users), `room_id` (FK → rooms), `start_date`, `end_date`, `status` (pending/approved/rejected/cancelled/completed), `created_at`, `deleted_at`

**payments**
- `payment_id` (PK), `booking_id` (FK → bookings), `tenant_id` (FK → users), `room_id` (FK → rooms), `amount_paid`, `payment_date`, `payment_method`, `status` (pending/confirmed/failed/refunded)

**reviews**
- `review_id` (PK), `tenant_id` (FK → users), `room_id` (FK → rooms), `rating` (1-5), `comment`, `date_posted`

### **3.2 Supporting Tables**

**property_amenities**: Property features (WiFi, Parking, etc.)  
**property_images**: Property photos  
**room_images**: Room photos  
**room_availability**: Calendar-based availability  
**booking_history**: Audit trail for booking status changes  
**lease_agreements**: Lease documents  
**payment_schedules**: Recurring payment tracking  
**payment_receipts**: Payment receipts  
**notifications**: User notifications  
**maintenance_requests**: Maintenance tracking  
**messages**: User-to-user messaging  
**user_profiles**: Extended user information  
**analytics_events**: User behavior tracking  
**audit_logs**: System-wide audit trail

### **3.3 Database Views**

**vw_active_bookings**: Active bookings with tenant and property details  
**vw_property_stats**: Property statistics (rooms, bookings, ratings)  
**vw_tenant_dashboard**: Tenant dashboard data (bookings, payments)

---

## **4. API ENDPOINTS & ROUTES**

### **4.1 Public Routes (No Authentication)**

| Route | Method | Description | Response |
|-------|--------|-------------|----------|
| `/` | GET | Browse page | HTML |
| `/browse` | GET | Browse page (alias) | HTML |
| `/login` | GET | Login page | HTML |
| `/property/<id>` | GET | Property details page | HTML |
| `/api/properties` | GET | Get all properties | JSON |
| `/api/properties/<id>` | GET | Get property by ID | JSON |
| `/api/properties/<id>/rooms` | GET | Get rooms for property | JSON |
| `/api/properties/<id>/amenities` | GET | Get property amenities | JSON |
| `/api/properties/<id>/images` | GET | Get property images | JSON |
| `/api/rooms/<id>/images` | GET | Get room images | JSON |
| `/api/chat` | POST | AI chat (public) | JSON |
| `/api/user-status` | GET | Check login status | JSON |
| `/api/schema` | GET | Get database schema | JSON |
| `/api/query` | POST | Execute SELECT query | JSON |

### **4.2 Authentication Routes**

| Route | Method | Description | Request Body | Response |
|-------|--------|-------------|--------------|----------|
| `/api/login` | POST | User login | `{email, password}` | `{success, user}` or `{error}` |
| `/api/logout` | POST | User logout | None | `{success, message}` |

### **4.3 Owner-Only Routes (Requires Owner Role)**

| Route | Method | Description | Response |
|-------|--------|-------------|----------|
| `/owner-dashboard` | GET | Owner dashboard page | HTML |
| `/api/owner/properties` | GET | Get owner's properties | JSON |
| `/api/owner/bookings` | GET | Get owner's bookings | JSON |
| `/api/owner/tenants` | GET | Get owner's tenants | JSON |
| `/api/owner/tenant-chat` | POST | AI chat about tenants | JSON |
| `/api/owner/property-stats` | GET | Get property statistics | JSON |

---

## **5. USER FLOWS**

### **5.1 Guest User Flow**

```
1. User visits homepage (/)
   └─> Renders browse.html
   └─> Shows property listing
   └─> AI chat sidebar available

2. User searches for properties
   └─> Types in search box
   └─> Filters properties client-side
   └─> Can click property cards

3. User views property details
   └─> Clicks property card
   └─> Navigates to /property/<id>
   └─> Renders property-details.html
   └─> Fetches: /api/properties/<id>
   └─> Fetches: /api/properties/<id>/rooms
   └─> Fetches: /api/properties/<id>/amenities
   └─> Fetches: /api/properties/<id>/images

4. User uses AI chat
   └─> Types question in chat input
   └─> Sends POST to /api/chat
   └─> AI generates SQL query
   └─> Executes query on database
   └─> Formats response
   └─> Displays in chat interface

5. User attempts to book
   └─> Clicks "Book Room" button
   └─> System checks login status
   └─> If not logged in: Redirects to /login
   └─> If logged in: Shows booking form (placeholder)

6. User logs in
   └─> Clicks "Sign In" button
   └─> Navigates to /login
   └─> Enters email and password
   └─> POST to /api/login
   └─> On success: Session created, redirects to browse
   └─> On failure: Shows error message
```

### **5.2 Tenant Flow**

```
1. Tenant logs in
   └─> Same as Guest User Flow #6
   └─> Session stores: user_id, full_name, email, role='tenant'

2. Tenant browses properties
   └─> Same as Guest User Flow #1-3
   └─> Can now book rooms

3. Tenant books a room
   └─> Views property details
   └─> Selects room
   └─> Clicks "Book Room"
   └─> (Booking functionality placeholder - not fully implemented)
   └─> Would create booking with status='pending'

4. Tenant uses AI chat
   └─> Same as Guest User Flow #4
   └─> Can ask about own bookings, payments, etc.

5. Tenant views own bookings
   └─> (Feature not fully implemented in UI)
   └─> Would query bookings WHERE tenant_id = session.user_id

6. Tenant submits review
   └─> (Feature not fully implemented in UI)
   └─> Would POST to /api/reviews
```

### **5.3 Owner Flow**

```
1. Owner logs in
   └─> Same as Guest User Flow #6
   └─> Session stores: user_id, full_name, email, role='owner'

2. Owner accesses dashboard
   └─> Navigates to /owner-dashboard
   └─> Renders owner_dashboard.html
   └─> Fetches: /api/owner/properties
   └─> Fetches: /api/owner/bookings
   └─> Fetches: /api/owner/tenants
   └─> Displays in dashboard sections

3. Owner views properties
   └─> Dashboard shows property cards
   └─> Each card shows: name, location, available rooms, date posted
   └─> Can click to view details

4. Owner views bookings
   └─> Dashboard shows booking list
   └─> Shows: tenant name, property, room type, dates, status
   └─> Can filter by status (pending/approved/rejected)
   └─> Can approve/reject bookings (UI placeholder)

5. Owner views tenants
   └─> Dashboard shows tenant grid
   └─> Shows: name, email, phone, booking stats
   └─> Shows: properties rented, room types, booking history

6. Owner uses tenant AI chat
   └─> Specialized AI chat in dashboard
   └─> POST to /api/owner/tenant-chat
   └─> AI has context of owner's tenants
   └─> Can answer questions about tenant statistics, history, etc.

7. Owner manages properties
   └─> (Add/Edit/Delete properties - UI placeholder)
   └─> Would use: POST /api/owner/properties (create)
   └─> Would use: PUT /api/owner/properties/<id> (update)
   └─> Would use: DELETE /api/owner/properties/<id> (soft delete)

8. Owner views property statistics
   └─> Fetches: /api/owner/property-stats
   └─> Uses database view: vw_property_stats
   └─> Shows: total rooms, available rooms, bookings, ratings
```

---

## **6. AI CHAT FLOW (DETAILED)**

### **6.1 Public AI Chat (`/api/chat`)**

```
1. User sends message
   └─> POST /api/chat
   └─> Body: {message: "user question"}

2. System processes message
   ├─> Checks for identity questions (who are you, etc.)
   │   └─> Returns predefined response
   ├─> Validates Gemini API is configured
   │   └─> Returns error if not configured
   └─> Gets minimal database schema
       └─> Only essential tables: users, properties, rooms, bookings, payments, reviews
       └─> Compact format: table_name(column1, column2, ...)

3. AI generates SQL query
   └─> Sends to Gemini API:
       ├─> Schema information (minimal)
       ├─> User question
       └─> Instructions: Generate SELECT query, filter deleted records
   └─> Receives SQL query from AI

4. System executes SQL
   └─> Validates query (SELECT only)
   └─> Executes on database
   └─> Returns query results

5. System processes results
   └─> Replaces IDs with names:
       ├─> user_id → full_name
       ├─> property_id → property_name
       └─> room_id → "property_name - room_type"
   └─> Formats response locally (if possible)
       └─> Uses format_query_response() function
       └─> Only uses AI for complex formatting if needed

6. System returns response
   └─> JSON: {response: "formatted answer", timestamp: null}
   └─> Frontend displays in chat interface
```

### **6.2 Owner Tenant Chat (`/api/owner/tenant-chat`)**

```
1. Owner sends message about tenants
   └─> POST /api/owner/tenant-chat
   └─> Body: {message: "question about tenants"}

2. System fetches tenant data
   └─> Queries database for owner's tenants
   └─> Includes: bookings, properties, room types, rates
   └─> Aggregates statistics per tenant

3. AI processes with tenant context
   └─> Sends to Gemini API:
       ├─> Tenant data (JSON)
       ├─> Owner's question
       └─> Instructions: Answer using tenant names, provide statistics
   └─> Receives formatted answer

4. System returns response
   └─> JSON: {response: "answer", timestamp: null}
   └─> Owner dashboard displays answer
```

---

## **7. AUTHENTICATION FLOW**

```
1. User clicks "Sign In"
   └─> Navigates to /login
   └─> Renders login.html

2. User enters credentials
   └─> Email and password
   └─> Submits form

3. System validates
   └─> POST /api/login
   └─> Body: {email, password}
   └─> Queries database:
       SELECT user_id, full_name, email, role 
       FROM users 
       WHERE email = ? AND password = ? 
       AND role IN ('tenant', 'owner') 
       AND deleted_at IS NULL

4. On success
   └─> Creates session:
       ├─> user_id
       ├─> full_name
       ├─> email
       ├─> role
       └─> logged_in = True
   └─> Returns: {success: true, user: {...}}
   └─> Frontend redirects to /browse or /owner-dashboard

5. On failure
   └─> Returns: {error: "Invalid credentials"}
   └─> Frontend displays error message

6. Session management
   └─> GET /api/user-status checks session
   └─> POST /api/logout clears session
   └─> @require_owner decorator checks role
```

---

## **8. PROPERTY BROWSING FLOW**

```
1. Page load (/browse)
   └─> Fetches: GET /api/properties
   └─> Receives: Array of property objects
   └─> Displays property cards in grid

2. Property card structure
   ├─> Property image (placeholder or from property_images)
   ├─> Property name
   ├─> Location
   ├─> Description (truncated)
   ├─> Available rooms count
   ├─> Owner name
   └─> Date posted

3. User clicks property card
   └─> Navigates to /property/<property_id>
   └─> Renders property-details.html

4. Property details page loads
   └─> Fetches multiple endpoints:
       ├─> GET /api/properties/<id> (property info)
       ├─> GET /api/properties/<id>/rooms (room list)
       ├─> GET /api/properties/<id>/amenities (amenities list)
       └─> GET /api/properties/<id>/images (images)

5. Displays property information
   ├─> Property header (name, location, owner)
   ├─> Property description
   ├─> Amenities list
   ├─> Room cards:
       │   ├─> Room type (Single/Shared)
       │   ├─> Monthly rate
       │   ├─> Available spots
       │   ├─> House rules
       │   └─> "Book Room" button
   └─> Property images gallery

6. User searches properties
   └─> Types in search box
   └─> Client-side filtering:
       ├─> Filters by property name
       ├─> Filters by location
       └─> Updates display in real-time
```

---

## **9. BOOKING FLOW (Conceptual - Not Fully Implemented)**

```
1. Tenant selects room
   └─> Clicks "Book Room" on property details page
   └─> System checks authentication

2. Booking form (would be implemented)
   └─> Select start date
   └─> Select end date (optional)
   └─> Review room details
   └─> Submit booking

3. Create booking
   └─> POST /api/bookings (would be implemented)
   └─> Body: {room_id, start_date, end_date}
   └─> Creates record:
       ├─> tenant_id = session.user_id
       ├─> room_id = selected room
       ├─> status = 'pending'
       └─> created_at = NOW()

4. Database triggers
   └─> Trigger: log_booking_status_change
       └─> Logs status change to booking_history
   └─> (Room availability not updated until approved)

5. Owner receives notification
   └─> (Would create notification record)
   └─> Owner sees in dashboard bookings section

6. Owner approves/rejects
   └─> PUT /api/bookings/<id> (would be implemented)
   └─> Body: {status: 'approved' or 'rejected'}
   └─> Trigger: update_room_tenants_on_approval
       └─> If approved: current_tenants++, available_tenants--
       └─> If rejected/cancelled: current_tenants--, available_tenants++

7. Tenant receives notification
   └─> (Would create notification record)
   └─> Tenant sees booking status updated
```

---

## **10. PAYMENT FLOW (Conceptual - Not Fully Implemented)**

```
1. Booking approved
   └─> System creates payment schedule
   └─> POST /api/payment-schedules
   └─> Creates recurring payment entries

2. Payment due
   └─> Tenant receives notification
   └─> Tenant makes payment

3. Record payment
   └─> POST /api/payments
   └─> Body: {booking_id, amount_paid, payment_method}
   └─> Creates payment record
   └─> Updates payment_schedule status to 'paid'

4. Generate receipt
   └─> POST /api/payment-receipts
   └─> Creates receipt record
   └─> Returns receipt_number and receipt_url

5. Payment confirmation
   └─> Owner receives notification
   └─> Payment status updated to 'confirmed'
```

---

## **11. TECHNICAL ARCHITECTURE**

### **11.1 Request Flow**

```
Client (Browser)
    │
    ├─> HTTP Request
    │
    └─> Flask App (app.py)
        │
        ├─> Route Handler
        │   │
        │   ├─> Authentication Check (@require_owner)
        │   │
        │   ├─> Database Query (get_db_cursor)
        │   │   └─> MySQL Connection
        │   │       └─> Execute SQL
        │   │       └─> Return Results
        │   │
        │   ├─> AI Processing (if needed)
        │   │   └─> Gemini API Call
        │   │       └─> Generate SQL/Response
        │   │
        │   └─> Format Response
        │       └─> JSON/HTML
        │
        └─> Response to Client
```

### **11.2 Database Connection Management**

```
get_db_cursor() Context Manager
    │
    ├─> Creates MySQL connection
    ├─> Yields cursor
    ├─> Commits on success
    ├─> Rollbacks on error
    └─> Closes connection (finally)
```

### **11.3 AI Integration**

```
Gemini API Integration
    │
    ├─> Model: gemini-2.0-flash
    ├─> API Key: From ai_apis.env
    ├─> Usage:
    │   ├─> SQL Generation (minimal schema)
    │   ├─> Response Formatting (if needed)
    │   └─> Tenant Chat (with tenant data)
    │
    └─> Error Handling:
        ├─> Quota errors (429)
        ├─> API errors
        └─> Fallback to local formatting
```

---

## **12. DATA FLOW EXAMPLES**

### **12.1 Example: User Asks "Show me properties in Manila"**

```
1. User: Types "Show me properties in Manila" in AI chat
2. Frontend: POST /api/chat {message: "Show me properties in Manila"}
3. Backend: 
   ├─> Gets minimal schema
   ├─> Sends to Gemini: Schema + Question
   └─> Gemini returns: "SELECT * FROM properties WHERE location LIKE '%Manila%' AND deleted_at IS NULL"
4. Backend:
   ├─> Executes SQL query
   ├─> Gets results
   ├─> Replaces property_id with property_name
   └─> Formats response locally
5. Response: "I found 2 properties in Manila:
   • Santos Boarding House
     Location: Manila, Metro Manila
   • Dela Cruz Dormitory
     Location: Quezon City, Metro Manila"
6. Frontend: Displays formatted response in chat
```

### **12.2 Example: Owner Views Dashboard**

```
1. Owner: Navigates to /owner-dashboard
2. Frontend: Loads owner_dashboard.html
3. Frontend: Makes parallel requests:
   ├─> GET /api/owner/properties
   ├─> GET /api/owner/bookings
   └─> GET /api/owner/tenants
4. Backend: Each endpoint:
   ├─> Checks @require_owner decorator
   ├─> Queries database with owner_id filter
   └─> Returns JSON data
5. Frontend: Renders data in dashboard sections
   ├─> Properties grid
   ├─> Bookings table
   └─> Tenants grid
```

---

## **13. SECURITY FEATURES**

### **13.1 Authentication**
- Session-based authentication
- Password stored in plain text (should be hashed in production)
- Role-based access control (@require_owner decorator)

### **13.2 Database Security**
- Soft deletes (deleted_at) instead of hard deletes
- All queries filter deleted records
- SQL injection prevention (parameterized queries)
- Only SELECT queries allowed in /api/query

### **13.3 API Security**
- CORS not explicitly configured (default Flask settings)
- No rate limiting (should be added)
- API key stored in environment file

---

## **14. ERROR HANDLING**

### **14.1 Database Errors**
- Try-catch blocks around database operations
- Rollback on errors
- Returns user-friendly error messages

### **14.2 AI API Errors**
- Quota errors (429) handled with retry logic
- API failures fallback to local formatting
- Error messages displayed to user

### **14.3 Frontend Errors**
- Try-catch in async functions
- Error messages displayed in UI
- Console logging for debugging

---

## **15. FUTURE ENHANCEMENTS (Not Yet Implemented)**

1. Booking creation/management endpoints
2. Payment processing endpoints
3. Review submission endpoints
4. Property CRUD operations for owners
5. Image upload functionality
6. Notification system
7. Maintenance request system
8. Lease agreement management
9. Advanced search and filtering
10. Email notifications
11. Password hashing (bcrypt)
12. Rate limiting
13. CORS configuration
14. API versioning

---


This document covers the system flow. Developers can use it to understand the architecture, implement new features, or extend the system.

