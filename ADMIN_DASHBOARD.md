# Admin Dashboard Documentation

## Overview
Comprehensive administrative interface for managing users, monitoring subscriptions, tracking revenue, and viewing system-wide verification activity.

---

## Features Implemented

### 1. Admin Dashboard (`/admin/dashboard`)
**File:** `admin/routes.py::dashboard()`, `templates/admin/dashboard.html`

**Key Metrics Displayed:**
- **User Statistics:**
  - Total users count
  - Active users
  - New users today
  - New users this month
  
- **Revenue Metrics:**
  - MRR (Monthly Recurring Revenue) = (Pro users × €49) + (Enterprise users × €149)
  - Total revenue (all-time)
  - Revenue this month
  
- **Subscription Distribution:**
  - Free plan users count
  - Pro plan users count
  - Enterprise plan users count
  - Visual percentage breakdown with progress bars
  
- **API Usage:**
  - Total verifications (all-time)
  - Verifications today
  - Verifications this month

**Recent Activity Sections:**
- Last 10 user registrations (with plan badges)
- Last 10 verification checks (across all users)
- Monthly growth data (last 6 months)

### 2. User Management (`/admin/users`)
**File:** `admin/routes.py::users()`, `templates/admin/users.html`

**Features:**
- **Search and Filters:**
  - Full-text search: email, first name, last name, company name
  - Plan filter: All / Free / Pro / Enterprise
  - Status filter: All / Active / Inactive
  
- **User Table Columns:**
  - User ID
  - Name, email, admin badge, email confirmation status
  - Company name
  - Current plan (badge)
  - API usage (X / Y)
  - Registration date
  - Active/Inactive status badge
  
- **Actions Per User:**
  - 👁️ View Details - Opens user detail page
  - ⚡ Toggle Status - Activate/Deactivate account
  - 🔒 Toggle Admin - Grant/Revoke admin privileges
  
- **Pagination:**
  - 20 users per page
  - Next/Previous buttons
  - Page numbers with ellipsis

**AJAX Endpoints:**
- `POST /admin/users/<id>/toggle-status` - Toggle user active status
- `POST /admin/users/<id>/toggle-admin` - Toggle admin privileges

### 3. User Detail View (`/admin/users/<id>`)
**File:** `admin/routes.py::user_detail()`, `templates/admin/user_detail.html`

**Profile Section:**
- Avatar with initials
- Full name and email
- Admin/Active/Email confirmed badges
- Company info, phone, country
- Registration date
- Last login timestamp

**Statistics Cards:**
- Current subscription plan badge
- Total amount spent (sum of successful payments)

**API Usage Section:**
- Monthly usage: X / Y (or Unbegrenzt)
- Progress bar with color coding:
  - Green: < 80% usage
  - Yellow: 80-99% usage
  - Red: At/over limit
- Total verifications count

**Payment History Table:**
- Date and time
- Amount (€)
- Status badge (Erfolgreich/Fehlgeschlagen)
- Stripe payment intent ID

**Recent Verifications Table:**
- Date and time
- Counterparty company name
- VAT number
- Status badge (Gültig/Warnung/Fehler)

### 4. All Verifications View (`/admin/verifications`)
**File:** `admin/routes.py::verifications()`, `templates/admin/verifications.html`

**Features:**
- View all verification checks across all users
- 50 verifications per page with pagination
- Sortable columns:
  - Verification ID
  - Date and time
  - User email (clickable link to user detail)
  - Counterparty company name
  - VAT number
  - Country
  - Status badge

### 5. System Logs View (`/admin/logs`)
**File:** `admin/routes.py::logs()`, `templates/admin/logs.html`

**Status:** Placeholder implementation
- "Coming Soon" message
- Preview of future features:
  - Error logs (application errors, stack traces)
  - API logs (call history, response times)
  - Security logs (login attempts, suspicious activity)

### 6. Admin Access Control
**Decorator:** `@admin_required` in `admin/routes.py`

**Security Checks:**
1. User must be authenticated (`@login_required`)
2. User must have `is_admin=True` flag
3. If not authenticated → Redirect to login
4. If not admin → Flash error message + redirect to dashboard

**Prevents:**
- Admins from deactivating their own account
- Admins from removing their own admin privileges

---

## User Interface Design

### Dashboard Cards
- 4 metric cards with color coding:
  - Primary (blue): Total Users
  - Success (green): MRR
  - Info (cyan): Total Revenue
  - Warning (yellow): API Verifications
  
- Each card shows:
  - Icon (large, right-aligned)
  - Main metric (h2)
  - Supporting metric (small, muted)

### Subscription Distribution Chart
- 3-column layout
- Each column shows:
  - Plan name
  - User count (h2)
  - Progress bar
  - Percentage

### Recent Activity Tables
- Compact, hover-highlighted rows
- Clickable links to user details
- Color-coded status badges
- Responsive design with table-responsive wrapper

### User Management
- Filter form with Bootstrap styling
- Action buttons in btn-group
- AJAX toggle without page reload
- Confirmation dialogs before destructive actions

---

## Database Queries & Performance

### Optimized Queries:
```python
# Dashboard - Single queries with aggregations
total_users = User.query.count()
pro_users = Subscription.query.filter_by(plan='pro', status='active').count()
total_revenue = db.session.query(func.sum(Payment.amount)).filter(...).scalar()

# User Management - Paginated with joins
query = User.query.join(Subscription).filter(...).paginate(page, per_page)

# User Detail - Efficient relationship loading
user = User.query.get_or_404(user_id)
payments = Payment.query.filter_by(user_id=user_id).limit(20).all()
```

### Performance Considerations:
- Pagination to limit result sets
- Joins instead of N+1 queries
- `.count()` instead of `len(.all())`
- Index on foreign keys (user_id, subscription_id)

---

## Navigation Integration

### Base Template Update (`templates/base.html`):
```html
{% if current_user.is_admin %}
<li class="nav-item">
    <a class="nav-link text-warning" href="{{ url_for('admin.dashboard') }}">
        <i class="bi bi-shield-lock"></i> Admin
    </a>
</li>
{% endif %}
```

- Admin link only visible to users with `is_admin=True`
- Yellow text to differentiate from regular navigation
- Shield icon indicates privileged access

---

## JavaScript Functionality

### User Management AJAX:
```javascript
function toggleUserStatus(userId) {
    fetch(`/admin/users/${userId}/toggle-status`, {method: 'POST'})
    .then(response => response.json())
    .then(data => {
        // Update badge without page reload
        updateBadge(userId, data.is_active);
    });
}
```

**Benefits:**
- No page refresh needed
- Instant feedback to admin
- Preserves scroll position and filters

---

## Security Features

### Access Control:
- `@admin_required` decorator on all admin routes
- Checks authentication + admin flag
- Logs unauthorized access attempts

### Self-Protection:
- Admins cannot deactivate own account
- Admins cannot remove own admin status
- Prevents accidental lockout

### CSRF Protection:
- All POST requests require CSRF token (Flask-WTF)
- AJAX requests inherit token from forms

---

## Admin Workflow Examples

### Scenario 1: Investigate High API Usage
1. Go to Admin Dashboard
2. See "Verifications Today" metric is high
3. Click "Alle Prüfungen" button
4. Review recent verifications
5. Click user email to see their detail page
6. Check API usage progress bar
7. Review verification history

### Scenario 2: Promote User to Admin
1. Navigate to User Management
2. Search for user by email
3. Click shield button to grant admin
4. Confirm dialog
5. User row updates with "ADMIN" badge

### Scenario 3: Monthly Revenue Audit
1. Check Admin Dashboard
2. View MRR breakdown (Pro vs Enterprise)
3. Compare to "Revenue This Month"
4. Check subscription distribution percentages
5. Review growth data chart

### Scenario 4: Support Request Investigation
1. Search user by email in User Management
2. Click "View Details"
3. Check email confirmation status
4. Review payment history for billing issues
5. Check recent verifications for errors
6. Toggle account status if needed

---

## Statistics Calculations

### MRR (Monthly Recurring Revenue):
```python
pro_mrr = pro_users * 49  # €49/month per Pro user
enterprise_mrr = enterprise_users * 149  # €149/month per Enterprise user
total_mrr = pro_mrr + enterprise_mrr
```

### Revenue This Month:
```python
revenue_this_month = db.session.query(func.sum(Payment.amount)).filter(
    Payment.status == 'succeeded',
    extract('month', Payment.created_at) == current_month,
    extract('year', Payment.created_at) == current_year
).scalar()
```

### Growth Data (Last 6 Months):
```python
for i in range(5, -1, -1):
    target_date = datetime.utcnow() - timedelta(days=i*30)
    users_count = User.query.filter(
        extract('month', User.created_at) == target_date.month,
        extract('year', User.created_at) == target_date.year
    ).count()
```

---

## Future Enhancements

### TODO:
1. **Advanced Filtering:**
   - Date range picker for verifications
   - Revenue date range filter
   - Export to CSV/Excel
   
2. **Real-Time Updates:**
   - WebSocket for live dashboard updates
   - Real-time notification bell for new registrations
   
3. **Analytics:**
   - Conversion funnel (Free → Pro → Enterprise)
   - Churn rate calculation
   - Revenue forecasting
   
4. **User Actions:**
   - Send email directly from user detail page
   - Refund payment button
   - Reset user password as admin
   
5. **System Logs:**
   - Implement log file reader
   - Filter by log level (ERROR, WARNING, INFO)
   - Search logs by keyword
   - Download log files
   
6. **Audit Trail:**
   - Track all admin actions
   - "Modified by" field on user changes
   - Restore deleted users
   
7. **Notifications:**
   - Daily/weekly email digest for admins
   - Alert when user reaches API limit
   - Payment failure notifications

---

## Testing Admin Dashboard

### Manual Testing Checklist:

**Dashboard:**
- [ ] All metrics display correctly
- [ ] Recent users table shows correct data
- [ ] Recent verifications table shows correct data
- [ ] Quick access buttons navigate properly

**User Management:**
- [ ] Search finds users by email/name/company
- [ ] Plan filter works (Free/Pro/Enterprise)
- [ ] Status filter works (Active/Inactive)
- [ ] Pagination shows correct pages
- [ ] Toggle status updates badge without reload
- [ ] Toggle admin shows confirmation and updates

**User Detail:**
- [ ] Profile displays all user information
- [ ] API usage bar shows correct percentage
- [ ] Payment history displays all payments
- [ ] Verification history displays all checks
- [ ] Breadcrumb navigation works

**Verifications:**
- [ ] Displays all verifications across users
- [ ] User email links to user detail
- [ ] Pagination works correctly
- [ ] Status badges show correct colors

**Security:**
- [ ] Non-admin users cannot access /admin/*
- [ ] Admin cannot deactivate own account
- [ ] Admin cannot remove own admin status

---

## Deployment Considerations

### Database Indexes:
```sql
CREATE INDEX idx_user_created_at ON users(created_at);
CREATE INDEX idx_payment_created_at ON payments(created_at);
CREATE INDEX idx_verification_check_date ON verification_checks(check_date);
CREATE INDEX idx_subscription_plan_status ON subscriptions(plan, status);
```

### Caching Strategy:
- Cache dashboard metrics for 5 minutes
- Use Redis to avoid repeated DB queries
- Invalidate cache on user/payment updates

### Monitoring:
- Track admin action frequency
- Alert if admin deletes many users
- Log all admin privilege changes

---

## Status: ✅ COMPLETE

**Implemented:**
- Admin dashboard with key metrics
- User management with search/filter
- User detail view with full history
- All verifications view
- AJAX user status toggling
- Admin access control
- Navigation integration
- Pagination
- Security safeguards

**Next Steps:**
- Task #8: Documentation (README, deployment guide)
- Implement system logs viewer
- Add advanced analytics
