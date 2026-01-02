# Property Upload & Approval System - Implementation Guide

## Database Schema Update Required

**IMPORTANT:** You must run the database migration script before using the property upload features.

### Migration Script
Run the SQL script: `database_migration_property_approval.sql`

This adds the following columns to the `properties` table:
- `status` - ENUM('pending', 'approved', 'rejected') - Property approval status
- `approved_by` - INT(11) - Admin who approved the property
- `approved_at` - DATETIME - When the property was approved

### To Apply Migration:
```bash
mysql -u root -p adet_rentease < database_migration_property_approval.sql
```

## New Features

### 1. Property Upload Page
- **Route**: `/upload-property` (Owner only)
- **Features**:
  - Property information form (name, location, description)
  - Dynamic amenities addition
  - Multiple room addition (Single/Shared)
  - Room details (rate, capacity, description, house rules)
  - Submit for admin approval

### 2. Property Approval Flow
1. Owner creates property → Property created with `status='pending'`
2. Owner adds rooms to the property
3. Admin reviews pending properties in Admin Dashboard
4. Admin approves/rejects → Property `status` updated
5. Approved properties appear on browsing page

### 3. Updated Browse Page
- Only shows properties with `status='approved'`
- Pending/rejected properties are hidden from public view

### 4. Owner Dashboard Updates
- Shows property status badges (pending/approved/rejected)
- Pending properties show "Waiting for admin approval" message
- Only approved properties have "View Details" link

### 5. Admin Dashboard Updates
- New "Pending Properties" tab
- View all pending property submissions
- Approve/Reject properties
- View property details before approval

## API Endpoints

### Owner Property Management
```
POST /api/owner/create-property
Body: {
  "property_name": "Property Name",
  "location": "Location",
  "description": "Description",
  "amenities": ["WiFi", "Parking", ...]
}

POST /api/owner/add-room
Body: {
  "property_id": 1,
  "room_type": "Single" or "Shared",
  "monthly_rate": 5000.00,
  "description": "Room description",
  "total_tenants": 1,
  "house_rules": "Rules..."
}

GET /api/owner/pending-properties - Get owner's pending properties
```

### Admin Property Approval
```
GET /api/admin/pending-properties - Get all pending properties
POST /api/admin/approve-property/<property_id> - Approve property
POST /api/admin/reject-property/<property_id> - Reject property
```

## User Flow

### Owner Uploading Property
1. Login as owner
2. Go to Owner Dashboard
3. Click "Upload New Property" button
4. Fill in property details
5. Add amenities (optional)
6. Add one or more rooms
7. Submit for approval
8. Property appears in "Pending Properties" sidebar
9. Wait for admin approval

### Admin Approving Property
1. Login as admin
2. Go to Admin Dashboard
3. Click "Pending Properties" tab
4. View property details
5. Approve or Reject
6. Approved properties appear on browsing page

## Files Created/Modified

### New Files
- `database_migration_property_approval.sql` - Database migration
- `templates/upload-property.html` - Property upload page
- `PROPERTY_UPLOAD_README.md` - This documentation

### Modified Files
- `app.py` - Added property creation, room addition, and approval endpoints
- `templates/owner-dashboard.html` - Added upload button and status badges
- `templates/admin-dashboard.html` - Added pending properties tab
- Browse endpoint - Now filters by `status='approved'`

## Testing

### Test Property Upload
1. Login as owner
2. Navigate to `/upload-property`
3. Fill in property form
4. Add amenities
5. Add rooms
6. Submit
7. Check "Pending Properties" in sidebar
8. Login as admin
9. Go to Admin Dashboard → Pending Properties tab
10. Approve the property
11. Check browsing page - property should appear

## Notes

- Properties are created with `status='pending'` by default
- Rooms can be added immediately after property creation
- Only approved properties appear on the public browsing page
- Owners can see all their properties (pending/approved/rejected) in dashboard
- Admin can view property details before approving

