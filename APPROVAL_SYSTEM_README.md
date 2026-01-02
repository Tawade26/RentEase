# Account Approval System - Implementation Guide

## Database Schema Update Required

**IMPORTANT:** You must run the database migration script before using the new approval features.

### Migration Script
Run the SQL script: `database_migration_approval.sql`

This adds the following columns to the `users` table:
- `status` - ENUM('pending', 'approved', 'rejected') - Account approval status
- `role_change_request` - ENUM('tenant', 'owner', NULL) - Pending role change request
- `approved_by` - INT(11) - Admin who approved the account
- `approved_at` - DATETIME - When the account was approved

### To Apply Migration:
```bash
mysql -u root -p adet_rentease < database_migration_approval.sql
```

## New Features

### 1. Registration System
- **Default Role**: All new accounts are created as **Tenant** by default
- **Approval Required**: All accounts require admin approval before login
- **Registration Endpoint**: `POST /api/register`
- **Registration Page**: `/register`

### 2. Account Approval Flow
1. User registers → Account created with `status='pending'`
2. Admin reviews pending accounts in Admin Dashboard
3. Admin approves/rejects → Account `status` updated to 'approved' or 'rejected'
4. User can now login (if approved)

### 3. Role Change Request
- **Tenants** can request to become **Owners**
- Request stored in `role_change_request` field
- Admin must approve the role change
- **Endpoint**: `POST /api/request-role-change`

### 4. Admin Dashboard
- **Route**: `/admin-dashboard`
- **Features**:
  - View pending user registrations
  - Approve/Reject new accounts
  - View role change requests
  - Approve/Reject role changes
  - View statistics

### 5. Updated Login
- Login now checks `status='approved'`
- Pending accounts cannot login
- Rejected accounts cannot login
- Admin accounts bypass approval check

## API Endpoints

### Registration
```
POST /api/register
Body: {
  "full_name": "John Doe",
  "email": "john@example.com",
  "password": "password123",
  "phone_number": "09171234567",
  "role": "tenant"  // Optional, defaults to "tenant"
}
```

### Request Role Change (Tenant → Owner)
```
POST /api/request-role-change
Headers: { Session required }
Body: {
  "role": "owner"
}
```

### Admin Endpoints (Require Admin Role)
```
GET /api/admin/pending-users - Get all pending registrations
GET /api/admin/role-change-requests - Get all role change requests
POST /api/admin/approve-user/<user_id> - Approve user account
POST /api/admin/reject-user/<user_id> - Reject user account
POST /api/admin/approve-role-change/<user_id> - Approve role change
POST /api/admin/reject-role-change/<user_id> - Reject role change
GET /api/admin/stats - Get admin dashboard statistics
```

## User Flow

### New User Registration
1. Visit `/register`
2. Fill in registration form (defaults to Tenant)
3. Submit → Account created with `status='pending'`
4. Wait for admin approval
5. Once approved, can login

### Tenant Requesting Owner Role
1. Login as approved tenant
2. Call `/api/request-role-change` with `role: "owner"`
3. Wait for admin approval
4. Admin approves → Role changed to Owner

### Admin Workflow
1. Login as admin
2. Visit `/admin-dashboard`
3. View pending users in "Pending Approvals" tab
4. Approve/Reject accounts
5. View role change requests in "Role Change Requests" tab
6. Approve/Reject role changes

## Security Notes

- All new accounts require approval
- Only approved accounts can login
- Admin accounts are automatically approved
- Role changes require admin approval
- Admin actions are logged (approved_by field)

## Testing

### Test Accounts
After migration, existing accounts are set to `status='approved'` automatically.

### Create Test Admin
```sql
INSERT INTO users (full_name, email, password, role, status) 
VALUES ('Test Admin', 'admin@test.com', 'admin123', 'admin', 'approved');
```

### Test Registration Flow
1. Register new account at `/register`
2. Try to login → Should show "pending approval" message
3. Login as admin
4. Go to Admin Dashboard
5. Approve the new account
6. Login with new account → Should work

## Files Modified/Created

### New Files
- `database_migration_approval.sql` - Database migration script
- `templates/register.html` - Registration page
- `templates/admin-dashboard.html` - Admin dashboard

### Modified Files
- `app.py` - Added approval system, registration, admin routes
- `templates/login.html` - Added register link
- `templates/base.html` - Added admin dashboard link

