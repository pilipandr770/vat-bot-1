from datetime import datetime
import pytz
from .models import MailRule
import json

def apply_rules(message, rules=None):
    """
    Применить правила к сообщению
    Возвращает: (action, requires_human, matched_rule)
    """
    if rules is None:
        rules = MailRule.query.filter_by(is_enabled=True).order_by(MailRule.priority.desc()).all()

    for rule in rules:
        if rule.matches(message):
            # Проверяем рабочие часы, если они заданы
            workhours = rule.get_workhours()
            if workhours and not is_within_workhours(workhours):
                continue  # Правило не применяется вне рабочих часов

            return rule.action, rule.requires_human, rule

    # Правило по умолчанию
    return 'draft', True, None

def is_within_workhours(workhours):
    """Проверить, находится ли текущее время в рабочих часах"""
    if not workhours:
        return True

    try:
        tz_name = workhours.get('tz', 'UTC')
        tz = pytz.timezone(tz_name)
        now = datetime.now(tz)

        start_time = workhours.get('start', '00:00')
        end_time = workhours.get('end', '23:59')
        weekdays = workhours.get('weekdays', list(range(7)))  # 0=понедельник, 6=воскресенье

        # Проверяем день недели
        current_weekday = now.weekday()  # 0=понедельник, 6=воскресенье
        if current_weekday not in weekdays:
            return False

        # Проверяем время
        current_time = now.time()
        start = datetime.strptime(start_time, '%H:%M').time()
        end = datetime.strptime(end_time, '%H:%M').time()

        return start <= current_time <= end

    except Exception as e:
        # В случае ошибки считаем, что в рабочих часах
        print(f"Error checking workhours: {e}")
        return True

def get_default_rules():
    """Получить список стандартных правил"""
    return [
        {
            'name': 'VIP автоответ',
            'is_enabled': True,
            'match_domain': '*',
            'action': 'auto_reply',
            'requires_human': False,
            'workhours_json': json.dumps({
                'tz': 'Europe/Berlin',
                'start': '09:00',
                'end': '18:00',
                'weekdays': [0, 1, 2, 3, 4]  # Пн-Пт
            }),
            'priority': 100
        },
        {
            'name': 'Новые домены → проверка',
            'is_enabled': True,
            'match_domain': '*',
            'action': 'draft',
            'requires_human': True,
            'priority': 50
        },
        {
            'name': 'Вложения .zip/.exe → карантин',
            'is_enabled': True,
            'match_subject_regex': '.*',
            'action': 'quarantine',
            'requires_human': True,
            'priority': 75
        }
    ]

def create_default_rules():
    """Создать стандартные правила в БД"""
    from .models import db

    existing_rules = MailRule.query.count()
    if existing_rules > 0:
        return  # Правила уже созданы

    for rule_data in get_default_rules():
        rule = MailRule(**rule_data)
        db.session.add(rule)

    db.session.commit()