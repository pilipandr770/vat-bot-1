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
import stripe

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
    basic_users = Subscription.query.filter_by(plan='basic', status='active').count()
    pro_users = Subscription.query.filter_by(plan='professional', status='active').count()
    enterprise_users = Subscription.query.filter_by(plan='enterprise', status='active').count()

    # Revenue Statistics (Monthly Recurring Revenue)
    basic_mrr = basic_users * 9.99
    pro_mrr = pro_users * 49.90
    enterprise_mrr = enterprise_users * 149
    total_mrr = basic_mrr + pro_mrr + enterprise_mrr
    
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
                         basic_users=basic_users,
                         pro_users=pro_users,
                         enterprise_users=enterprise_users,
                         total_mrr=total_mrr,
                         basic_mrr=basic_mrr,
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
    from auth.models import User as AuthUser

    tab = request.args.get('tab', 'api')
    page = request.args.get('page', 1, type=int)
    per_page = 50

    # Base query: CheckResult + VerificationCheck + User
    base_q = (
        db.session.query(CheckResult, VerificationCheck, AuthUser)
        .join(VerificationCheck, CheckResult.check_id == VerificationCheck.id)
        .join(AuthUser, VerificationCheck.user_id == AuthUser.id)
        .order_by(CheckResult.created_at.desc())
    )

    if tab == 'errors':
        pagination = base_q.filter(CheckResult.status == 'error').paginate(
            page=page, per_page=per_page, error_out=False
        )
    else:
        pagination = base_q.paginate(page=page, per_page=per_page, error_out=False)

    # Security logs: recent logins
    security_logs = (
        AuthUser.query.filter(AuthUser.last_login.isnot(None))
        .order_by(AuthUser.last_login.desc())
        .limit(100)
        .all()
    )

    # Quick counters
    total_errors = CheckResult.query.filter_by(status='error').count()
    total_api_calls = CheckResult.query.count()

    return render_template(
        'admin/logs.html',
        tab=tab,
        pagination=pagination,
        security_logs=security_logs,
        total_errors=total_errors,
        total_api_calls=total_api_calls,
    )


@admin_bp.route('/api/stats')
@login_required
@admin_required
def api_stats():
    """
    JSON endpoint for dashboard statistics (for AJAX updates)
    """
    total_users = User.query.count()
    basic_users = Subscription.query.filter_by(plan='basic', status='active').count()
    pro_users = Subscription.query.filter_by(plan='professional', status='active').count()
    enterprise_users = Subscription.query.filter_by(plan='enterprise', status='active').count()
    total_mrr = (basic_users * 9.99) + (pro_users * 49.90) + (enterprise_users * 149)

    verifications_today = VerificationCheck.query.filter(
        func.date(VerificationCheck.check_date) == datetime.utcnow().date()
    ).count()

    return jsonify({
        'total_users': total_users,
        'basic_users': basic_users,
        'pro_users': pro_users,
        'enterprise_users': enterprise_users,
        'total_mrr': round(total_mrr, 2),
        'verifications_today': verifications_today
    })


# ─── Promo Code Management ────────────────────────────────────────────────────

@admin_bp.route('/promo-codes')
@login_required
@admin_required
def promo_codes():
    """List all Stripe coupons and promotion codes."""
    from flask import current_app
    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']

    coupons = []
    error = None
    try:
        result = stripe.Coupon.list(limit=50)
        for coupon in result.auto_paging_iter():
            # Fetch promotion codes for this coupon
            promo_codes_for_coupon = stripe.PromotionCode.list(coupon=coupon.id, limit=10)
            codes = [p.code for p in promo_codes_for_coupon.auto_paging_iter()]
            coupons.append({
                'id': coupon.id,
                'name': coupon.name or coupon.id,
                'discount': f"{coupon.percent_off}%" if coupon.percent_off else f"€{coupon.amount_off / 100:.2f}",
                'duration': coupon.duration,
                'duration_months': coupon.duration_in_months,
                'redemptions': coupon.times_redeemed,
                'max_redemptions': coupon.max_redemptions,
                'valid': coupon.valid,
                'codes': codes,
            })
    except stripe.error.StripeError as e:
        error = str(e)

    return render_template('admin/promo_codes.html', coupons=coupons, error=error)


@admin_bp.route('/promo-codes/create', methods=['POST'])
@login_required
@admin_required
def create_promo_code():
    """Create a new Stripe coupon + promotion code."""
    from flask import current_app
    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']

    name = request.form.get('name', '').strip()
    code = request.form.get('code', '').strip().upper()
    discount_type = request.form.get('discount_type')  # 'percent' or 'amount'
    percent_off = request.form.get('percent_off', type=float)
    amount_off = request.form.get('amount_off', type=float)
    duration = request.form.get('duration', 'once')  # once / repeating / forever
    duration_months = request.form.get('duration_months', type=int)
    max_redemptions = request.form.get('max_redemptions', type=int)
    expires_at = request.form.get('expires_at')  # YYYY-MM-DD

    if not name or not code:
        flash('Name und Promocode-Code sind Pflichtfelder.', 'danger')
        return redirect(url_for('admin.promo_codes'))

    try:
        coupon_params = {
            'name': name,
            'duration': duration,
            'currency': 'eur',
        }
        if discount_type == 'percent' and percent_off:
            coupon_params['percent_off'] = percent_off
        elif discount_type == 'amount' and amount_off:
            coupon_params['amount_off'] = int(amount_off * 100)  # cents

        if duration == 'repeating' and duration_months:
            coupon_params['duration_in_months'] = duration_months

        if max_redemptions:
            coupon_params['max_redemptions'] = max_redemptions

        coupon = stripe.Coupon.create(**coupon_params)

        promo_params = {
            'coupon': coupon.id,
            'code': code,
        }
        if max_redemptions:
            promo_params['max_redemptions'] = max_redemptions
        if expires_at:
            import time
            from datetime import date
            exp = datetime.strptime(expires_at, '%Y-%m-%d')
            promo_params['expires_at'] = int(exp.timestamp())

        stripe.PromotionCode.create(**promo_params)

        discount_str = f"{coupon_params['percent_off']}%" if discount_type == 'percent' else f"{amount_off}€"
        flash(f'Promocode "{code}" erfolgreich erstellt ({discount_str} Rabatt).', 'success')
    except stripe.error.StripeError as e:
        flash(f'Stripe-Fehler: {e.user_message or str(e)}', 'danger')

    return redirect(url_for('admin.promo_codes'))


@admin_bp.route('/promo-codes/<coupon_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_promo_code(coupon_id):
    """Deactivate (delete) a Stripe coupon."""
    from flask import current_app
    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
    try:
        stripe.Coupon.delete(coupon_id)
        flash('Coupon wurde deaktiviert.', 'success')
    except stripe.error.StripeError as e:
        flash(f'Fehler: {e.user_message or str(e)}', 'danger')
    return redirect(url_for('admin.promo_codes'))


@admin_bp.route('/blog')
@login_required
@admin_required
def blog_management():
    """Blog management page — list posts, scheduler status, manual trigger."""
    from crm.models import BlogPost
    from services.blog_generator import SEO_TOPICS
    from sqlalchemy import func

    page  = request.args.get('page', 1, type=int)
    posts = BlogPost.query.order_by(BlogPost.generated_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    total_posts     = BlogPost.query.count()
    published_posts = BlogPost.query.filter_by(is_published=True).count()
    total_topics    = len(SEO_TOPICS)

    # Slugs already used
    used_slugs = {
        r[0] for r in BlogPost.query.with_entities(BlogPost.slug).all()
    }
    from services.blog_generator import _slugify
    topics_remaining = sum(
        1 for t in SEO_TOPICS if _slugify(t[0]) not in used_slugs
    )

    # Today's post
    from datetime import datetime
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_post  = BlogPost.query.filter(BlogPost.generated_at >= today_start).first()

    # Anthropic key configured?
    import os
    anthropic_ok = bool(os.environ.get('ANTHROPIC_API_KEY'))

    # LinkedIn status
    from services.linkedin_publisher import is_configured as li_configured, is_authorized as li_authorized
    linkedin_configured = li_configured()
    linkedin_authorized = li_authorized()

    return render_template(
        'admin/blog.html',
        posts=posts,
        total_posts=total_posts,
        published_posts=published_posts,
        total_topics=total_topics,
        topics_remaining=topics_remaining,
        today_post=today_post,
        anthropic_ok=anthropic_ok,
        linkedin_configured=linkedin_configured,
        linkedin_authorized=linkedin_authorized,
    )


@admin_bp.route('/blog/<int:post_id>/toggle', methods=['POST'])
@login_required
@admin_required
def blog_toggle_publish(post_id):
    """Toggle is_published for a blog post."""
    from crm.models import BlogPost
    post = BlogPost.query.get_or_404(post_id)
    post.is_published = not post.is_published
    db.session.commit()
    return jsonify({'success': True, 'is_published': post.is_published})


@admin_bp.route('/blog/<int:post_id>/delete', methods=['POST'])
@login_required
@admin_required
def blog_delete(post_id):
    """Delete a blog post."""
    from crm.models import BlogPost
    post = BlogPost.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash(f'Artikel "{post.title[:60]}" gelöscht.', 'success')
    return redirect(url_for('admin.blog_management'))


@admin_bp.route('/blog/generate', methods=['POST'])
@login_required
@admin_required
def generate_blog():
    """Manually trigger daily blog post generation."""
    from services.blog_generator import generate_daily_blog_post
    from flask import current_app
    force = request.args.get('force', 'false').lower() == 'true'
    try:
        result = generate_daily_blog_post(current_app._get_current_object(), force=force)
        if result:
            return jsonify({'success': True, 'message': 'Blog post generated successfully'})
        return jsonify({'success': False, 'message': 'Skipped: post exists today or AI unavailable'})
    except Exception as exc:
        current_app.logger.error('Admin blog generation failed: %s', exc, exc_info=True)
        return jsonify({'error': str(exc)}), 500


# ─── LinkedIn OAuth & Publishing ─────────────────────────────────────────────

@admin_bp.route('/linkedin/auth')
@login_required
@admin_required
def linkedin_auth():
    """Redirect admin to LinkedIn OAuth2 authorization page."""
    from services.linkedin_publisher import get_auth_url, is_configured
    from flask import current_app, request as req

    if not is_configured():
        flash('LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET not set.', 'danger')
        return redirect(url_for('admin.blog_management'))

    redirect_uri = req.host_url.rstrip('/') + url_for('admin.linkedin_callback')
    auth_url = get_auth_url(redirect_uri, state='vatbot-admin')
    return redirect(auth_url)


@admin_bp.route('/linkedin/callback')
@login_required
@admin_required
def linkedin_callback():
    """LinkedIn OAuth2 callback — exchange code for token and save it."""
    from services.linkedin_publisher import exchange_code, get_member_id
    from crm.models import LinkedInToken
    from flask import request as req
    import os
    from datetime import datetime, timedelta

    code  = req.args.get('code')
    error = req.args.get('error')

    if error or not code:
        flash(f'LinkedIn Auth fehlgeschlagen: {error or "Kein Code"}', 'danger')
        return redirect(url_for('admin.blog_management'))

    redirect_uri = req.host_url.rstrip('/') + url_for('admin.linkedin_callback')

    try:
        token_data = exchange_code(code, redirect_uri)
    except Exception as exc:
        flash(f'Token-Austausch fehlgeschlagen: {exc}', 'danger')
        return redirect(url_for('admin.blog_management'))

    access_token = token_data.get('access_token', '')
    expires_in   = token_data.get('expires_in', 5183944)  # 60 days default
    expires_at   = datetime.utcnow() + timedelta(seconds=expires_in)

    # Get member sub (who authorized)
    try:
        member_id = get_member_id(access_token)
    except Exception:
        member_id = ''

    # Org ID from env (already known)
    org_id = os.environ.get('LINKEDIN_ORGANIZATION_ID', '')

    # Save to DB (replace old rows)
    LinkedInToken.query.delete()
    token_row = LinkedInToken(
        access_token=access_token,
        expires_at=expires_at,
        organization_id=org_id,
        member_id=member_id,
    )
    db.session.add(token_row)
    db.session.commit()

    flash(
        f'✅ LinkedIn verbunden! Token gültig bis {expires_at.strftime("%d.%m.%Y %H:%M")} UTC. '
        f'Vergiss nicht, LINKEDIN_ORGANIZATION_ID in Render zu setzen.',
        'success'
    )
    return redirect(url_for('admin.blog_management'))


@admin_bp.route('/blog/<int:post_id>/linkedin', methods=['POST'])
@login_required
@admin_required
def blog_post_to_linkedin(post_id):
    """Manually post an existing blog article to LinkedIn."""
    from crm.models import BlogPost
    from services.linkedin_publisher import publish_post, is_authorized
    from flask import request as req, current_app

    post = BlogPost.query.get_or_404(post_id)

    if not is_authorized():
        return jsonify({'error': 'LinkedIn not authorized. Visit /admin/linkedin/auth first.'}), 400

    base_url = req.host_url.rstrip('/')
    article_url = f"{base_url}/blog/{post.slug}"

    try:
        result = publish_post(
            title=post.title,
            url=article_url,
            summary=post.meta_description or post.title,
        )
        li_id = result.get('id', '')
        post.linkedin_post_id = li_id
        post.linkedin_posted_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True, 'linkedin_id': li_id})
    except Exception as exc:
        current_app.logger.error('LinkedIn publish failed: %s', exc, exc_info=True)
        return jsonify({'error': str(exc)}), 500


@admin_bp.route('/linkedin/status')
@login_required
@admin_required
def linkedin_status():
    """Return LinkedIn configuration / token status as JSON."""
    from services.linkedin_publisher import is_configured, is_authorized
    from crm.models import LinkedInToken
    import os

    token_row = LinkedInToken.query.order_by(LinkedInToken.id.desc()).first()
    return jsonify({
        'configured': is_configured(),
        'authorized': is_authorized(),
        'org_id': os.environ.get('LINKEDIN_ORGANIZATION_ID', ''),
        'expires_at': token_row.expires_at.isoformat() if token_row and token_row.expires_at else None,
        'expired': token_row.is_expired() if token_row else None,
        'member_id': token_row.member_id if token_row else None,
    })


@admin_bp.route('/scheduler/status')
@login_required
@admin_required
def scheduler_status():
    """View scheduled jobs status for all three schedulers."""
    from flask import current_app
    from services.scheduler import get_scheduler

    def _jobs(sched):
        """Works with both MonitoringScheduler wrapper and bare APScheduler."""
        if not sched:
            return None
        try:
            # MonitoringScheduler wraps APScheduler in self.scheduler
            inner = getattr(sched, 'scheduler', sched)
            return [
                {
                    'id': j.id,
                    'name': j.name,
                    'next_run': str(j.next_run_time) if j.next_run_time else 'paused',
                }
                for j in inner.get_jobs()
            ]
        except Exception as exc:
            return {'error': str(exc)}

    main_sched = get_scheduler()
    mailguard_sched = getattr(current_app, 'mailguard_scheduler', None)
    crm_sched = getattr(current_app, 'crm_monitoring_scheduler', None)

    # Expose last-error hint stored on the app object (set during create_app)
    sched_error = getattr(current_app, '_scheduler_init_error', None)

    return jsonify({
        'monitoring': {
            'status': 'running' if main_sched else 'not_initialized',
            'jobs': _jobs(main_sched),
            'error': str(sched_error) if sched_error and not main_sched else None,
        },
        'mailguard': {
            'status': 'running' if mailguard_sched else 'not_initialized',
            'jobs': _jobs(mailguard_sched),
        },
        'crm_monitoring': {
            'status': 'running' if crm_sched else 'not_initialized',
            'jobs': _jobs(crm_sched),
        },
    })

