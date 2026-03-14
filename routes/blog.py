"""
Blog Routes — /blog/
"""
from flask import Blueprint, render_template, abort, request
from crm.models import BlogPost

blog_bp = Blueprint('blog', __name__, url_prefix='/blog')

POSTS_PER_PAGE = 9


@blog_bp.route('/')
def index():
    """Blog listing page with pagination."""
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', None)

    query = BlogPost.query.filter_by(is_published=True)
    if category:
        query = query.filter_by(category=category)
    query = query.order_by(BlogPost.published_at.desc())

    pagination = query.paginate(page=page, per_page=POSTS_PER_PAGE, error_out=False)
    posts = pagination.items

    # Category counts for sidebar
    from sqlalchemy import func
    from crm.models import db
    category_counts = dict(
        db.session.query(BlogPost.category, func.count(BlogPost.id))
        .filter_by(is_published=True)
        .group_by(BlogPost.category)
        .all()
    )

    from services.blog_generator import CATEGORY_LABELS
    return render_template(
        'blog/list.html',
        posts=posts,
        pagination=pagination,
        current_category=category,
        category_counts=category_counts,
        category_labels=CATEGORY_LABELS,
    )


@blog_bp.route('/<slug>')
def article(slug):
    """Single article view."""
    post = BlogPost.query.filter_by(slug=slug, is_published=True).first_or_404()

    # Increment view count
    from crm.models import db
    post.view_count = (post.view_count or 0) + 1
    db.session.commit()

    # Related posts (same category, excluding current)
    related = (
        BlogPost.query
        .filter(BlogPost.category == post.category,
                BlogPost.id != post.id,
                BlogPost.is_published == True)
        .order_by(BlogPost.published_at.desc())
        .limit(3)
        .all()
    )

    from services.blog_generator import CATEGORY_LABELS
    return render_template(
        'blog/article.html',
        post=post,
        related=related,
        category_labels=CATEGORY_LABELS,
    )
