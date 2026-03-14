#!/usr/bin/env python3
"""
Standalone script for daily blog post generation.
Called by Render Cron Job every day at 07:00 UTC.

Usage:
    python scripts/generate_blog.py
"""
import sys
import os
import logging

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    stream=sys.stdout,
)
logger = logging.getLogger('generate_blog')


def main():
    logger.info("=== Daily Blog Generator - Starting ===")
    try:
        from application import create_app
        app = create_app()
    except Exception as e:
        logger.error(f"Failed to create Flask app: {e}", exc_info=True)
        sys.exit(1)

    try:
        from services.blog_generator import generate_daily_blog_post
        result = generate_daily_blog_post(app)
        if result:
            logger.info("=== Blog post generated successfully ===")
            sys.exit(0)
        else:
            logger.info("=== Blog post skipped (already exists today or no content) ===")
            sys.exit(0)
    except Exception as e:
        logger.error(f"Blog generation failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
