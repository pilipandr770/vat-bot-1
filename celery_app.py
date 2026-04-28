"""
Celery application factory.

Usage:
    celery -A celery_app.celery worker --loglevel=info
    celery -A celery_app.celery beat   --loglevel=info

The CELERY_WORKER=true env var tells create_app() to skip APScheduler
and MailGuard in-process schedulers (they duplicate Celery Beat).
"""
import os
os.environ.setdefault('CELERY_WORKER', 'true')

from celery import Celery
from application import create_app

flask_app = create_app(os.environ.get('FLASK_ENV', 'development'))


def make_celery(app) -> Celery:
    celery = Celery(app.import_name)
    celery.conf.update(
        broker_url=app.config['CELERY_BROKER_URL'],
        result_backend=app.config['CELERY_RESULT_BACKEND'],
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],
        timezone='Europe/Berlin',
        task_track_started=True,
        worker_prefetch_multiplier=1,
    )

    class ContextTask(celery.Task):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


celery = make_celery(flask_app)

# Auto-discover tasks from registered packages
celery.autodiscover_tasks(['app.pentesting', 'app.mailguard'])
