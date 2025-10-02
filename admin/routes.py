"""
Admin Dashboard Routes
Provides administrative interface for user management, statistics, and monitoring
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from auth.models import db, User, Subscription, Payment
from crm.models import Company, Counterparty, VerificationCheck, CheckResult
from sqlalchemy import func, extract
from datetime import datetime, timedelta
import calendar

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    """
    Decorator to ensure user is an admin
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Bitte melden Sie sich an.', 'warning')
            return redirect(url_for('auth.login'))
        
        if not current_user.is_admin:
            flash('Sie haben keine Berechtigung für diese Seite.', 'danger')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """
    Admin dashboard with key metrics and statistics
    """
    # User Statistics
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    new_users_today = User.query.filter(
        func.date(User.created_at) == datetime.utcnow().date()
    ).count()
    new_users_this_month = User.query.filter(
        extract('month', User.created_at) == datetime.utcnow().month,
        extract('year', User.created_at) == datetime.utcnow().year
    ).count()
    
    # Subscription Statistics
    free_users = Subscription.query.filter_by(plan='free').count()
    pro_users = Subscription.query.filter_by(plan='pro', status='active').count()
    enterprise_users = Subscription.query.filter_by(plan='enterprise', status='active').count()
    
    # Revenue Statistics (Monthly Recurring Revenue)
    pro_mrr = pro_users * 49
    enterprise_mrr = enterprise_users * 149
    total_mrr = pro_mrr + enterprise_mrr
    
    # Calculate total revenue (all-time)
    total_revenue = db.session.query(
        func.sum(Payment.amount)
    ).filter(
        Payment.status == 'succeeded'
    ).scalar() or 0.0
    
    # Revenue this month
    revenue_this_month = db.session.query(
        func.sum(Payment.amount)
    ).filter(
        Payment.status == 'succeeded',
        extract('month', Payment.created_at) == datetime.utcnow().month,
        extract('year', Payment.created_at) == datetime.utcnow().year
    ).scalar() or 0.0
    
    # API Usage Statistics
    total_verifications = VerificationCheck.query.count()
    verifications_today = VerificationCheck.query.filter(
        func.date(VerificationCheck.check_date) == datetime.utcnow().date()
    ).count()
    verifications_this_month = VerificationCheck.query.filter(
        extract('month', VerificationCheck.check_date) == datetime.utcnow().month,
        extract('year', VerificationCheck.check_date) == datetime.utcnow().year
    ).count()
    
    # Recent Activity - Last 10 registrations
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    
    # Recent Verifications
    recent_verifications = VerificationCheck.query.join(User).order_by(
        VerificationCheck.check_date.desc()
    ).limit(10).all()
    
    # Monthly Growth Data (last 6 months)
    growth_data = []
    for i in range(5, -1, -1):
        target_date = datetime.utcnow() - timedelta(days=i*30)
        month_name = calendar.month_name[target_date.month][:3]
        
        users_count = User.query.filter(
            extract('month', User.created_at) == target_date.month,
            extract('year', User.created_at) == target_date.year
        ).count()
        
        revenue = db.session.query(
            func.sum(Payment.amount)
        ).filter(
            Payment.status == 'succeeded',
            extract('month', Payment.created_at) == target_date.month,
            extract('year', Payment.created_at) == target_date.year
        ).scalar() or 0.0
        
        growth_data.append({
            'month': month_name,
            'users': users_count,
            'revenue': revenue
        })
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         active_users=active_users,
                         new_users_today=new_users_today,
                         new_users_this_month=new_users_this_month,
                         free_users=free_users,
                         pro_users=pro_users,
                         enterprise_users=enterprise_users,
                         total_mrr=total_mrr,
                         pro_mrr=pro_mrr,
                         enterprise_mrr=enterprise_mrr,
                         total_revenue=total_revenue,
                         revenue_this_month=revenue_this_month,
                         total_verifications=total_verifications,
                         verifications_today=verifications_today,
                         verifications_this_month=verifications_this_month,
                         recent_users=recent_users,
                         recent_verifications=recent_verifications,
                         growth_data=growth_data)


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """
    User management page with search and filter
    """
    # Get query parameters
    search_query = request.args.get('search', '')
    plan_filter = request.args.get('plan', 'all')
    status_filter = request.args.get('status', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Base query
    query = User.query.join(Subscription)
    
    # Apply search filter
    if search_query:
        query = query.filter(
            (User.email.ilike(f'%{search_query}%')) |
            (User.first_name.ilike(f'%{search_query}%')) |
            (User.last_name.ilike(f'%{search_query}%')) |
            (User.company_name.ilike(f'%{search_query}%'))
        )
    
    # Apply plan filter
    if plan_filter != 'all':
        query = query.filter(Subscription.plan == plan_filter)
    
    # Apply status filter
    if status_filter == 'active':
        query = query.filter(User.is_active == True)
    elif status_filter == 'inactive':
        query = query.filter(User.is_active == False)
    
    # Order by most recent
    query = query.order_by(User.created_at.desc())
    
    # Paginate results
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    users_list = pagination.items
    
    return render_template('admin/users.html',
                         users=users_list,
                         pagination=pagination,
                         search_query=search_query,
                         plan_filter=plan_filter,
                         status_filter=status_filter)


@admin_bp.route('/users/<int:user_id>')
@login_required
@admin_required
def user_detail(user_id):
    """
    Detailed view of a specific user
    """
    user = User.query.get_or_404(user_id)
    
    # Get user's subscription
    subscription = user.active_subscription
    
    # Get user's payments
    payments = Payment.query.filter_by(user_id=user_id).order_by(
        Payment.created_at.desc()
    ).limit(20).all()
    
    # Get user's verifications
    verifications = VerificationCheck.query.filter_by(user_id=user_id).order_by(
        VerificationCheck.check_date.desc()
    ).limit(20).all()
    
    # Calculate statistics
    total_spent = db.session.query(
        func.sum(Payment.amount)
    ).filter(
        Payment.user_id == user_id,
        Payment.status == 'succeeded'
    ).scalar() or 0.0
    
    total_verifications = VerificationCheck.query.filter_by(user_id=user_id).count()
    
    return render_template('admin/user_detail.html',
                         user=user,
                         subscription=subscription,
                         payments=payments,
                         verifications=verifications,
                         total_spent=total_spent,
                         total_verifications=total_verifications)


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    """
    Activate or deactivate a user account
    """
    user = User.query.get_or_404(user_id)
    
    # Prevent deactivating own account
    if user.id == current_user.id:
        return jsonify({'error': 'Sie können Ihr eigenes Konto nicht deaktivieren.'}), 400
    
    # Toggle status
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'aktiviert' if user.is_active else 'deaktiviert'
    return jsonify({
        'success': True,
        'message': f'Benutzer {user.email} wurde {status}.',
        'is_active': user.is_active
    })


@admin_bp.route('/users/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin_status(user_id):
    """
    Grant or revoke admin privileges
    """
    user = User.query.get_or_404(user_id)
    
    # Prevent removing own admin status
    if user.id == current_user.id:
        return jsonify({'error': 'Sie können Ihre eigenen Admin-Rechte nicht entfernen.'}), 400
    
    # Toggle admin status
    user.is_admin = not user.is_admin
    db.session.commit()
    
    status = 'erteilt' if user.is_admin else 'entzogen'
    return jsonify({
        'success': True,
        'message': f'Admin-Rechte für {user.email} wurden {status}.',
        'is_admin': user.is_admin
    })


@admin_bp.route('/verifications')
@login_required
@admin_required
def verifications():
    """
    View all verification checks across all users
    """
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # Get all verifications with user info
    pagination = VerificationCheck.query.join(User).order_by(
        VerificationCheck.check_date.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    verifications_list = pagination.items
    
    return render_template('admin/verifications.html',
                         verifications=verifications_list,
                         pagination=pagination)


@admin_bp.route('/logs')
@login_required
@admin_required
def logs():
    """
    View system logs and errors
    """
    # TODO: Implement log viewer
    # This would read from application logs file
    # For now, placeholder
    return render_template('admin/logs.html')


@admin_bp.route('/api/stats')
@login_required
@admin_required
def api_stats():
    """
    JSON endpoint for dashboard statistics (for AJAX updates)
    """
    total_users = User.query.count()
    pro_users = Subscription.query.filter_by(plan='pro', status='active').count()
    enterprise_users = Subscription.query.filter_by(plan='enterprise', status='active').count()
    total_mrr = (pro_users * 49) + (enterprise_users * 149)
    
    verifications_today = VerificationCheck.query.filter(
        func.date(VerificationCheck.check_date) == datetime.utcnow().date()
    ).count()
    
    return jsonify({
        'total_users': total_users,
        'pro_users': pro_users,
        'enterprise_users': enterprise_users,
        'total_mrr': total_mrr,
        'verifications_today': verifications_today
    })
