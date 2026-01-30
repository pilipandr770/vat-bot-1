"""
Модуль для анализа и классификации писем
Определяет категории, приоритет, sentiment и другие метрики
"""
import re
from typing import Dict, List, Tuple


def analyze_message(subject: str, body_text: str, from_email: str) -> Dict:
    """
    Полный анализ сообщения
    
    Args:
        subject: тема письма
        body_text: текст письма
        from_email: адрес отправителя
    
    Returns:
        dict с результатами анализа
    """
    text = f"{subject} {body_text}".lower()
    
    return {
        'category': detect_category(subject, body_text),
        'priority': detect_priority(subject, body_text),
        'sentiment': detect_sentiment(text),
        'intent': detect_intent(subject, body_text),
        'has_question': detect_question(text),
        'has_attachment_request': detect_attachment_request(text),
        'is_automated': detect_automated_message(from_email, subject, body_text),
        'language': detect_language(text),
        'suggested_labels': suggest_labels(subject, body_text)
    }


def detect_category(subject: str, body_text: str) -> str:
    """
    Определить категорию письма
    
    Возможные категории:
    - invoice: счета и платежи
    - inquiry: запросы информации
    - complaint: жалобы и проблемы
    - order: заказы
    - support: техподдержка
    - notification: уведомления
    - marketing: маркетинг
    - other: остальное
    """
    text = f"{subject} {body_text}".lower()
    
    # Счета и платежи
    invoice_keywords = [
        'rechnung', 'invoice', 'payment', 'zahlung', 'bezahlung', 
        'überweisung', 'betrag', 'fällig', 'due', 'bill'
    ]
    if any(keyword in text for keyword in invoice_keywords):
        return 'invoice'
    
    # Жалобы и проблемы
    complaint_keywords = [
        'beschwerde', 'complaint', 'problem', 'issue', 'fehler', 
        'error', 'nicht funktioniert', 'not working', 'unzufrieden',
        'dissatisfied', 'reklamation'
    ]
    if any(keyword in text for keyword in complaint_keywords):
        return 'complaint'
    
    # Заказы
    order_keywords = [
        'bestellung', 'order', 'bestellen', 'kaufen', 'purchase',
        'auftrag', 'lieferung', 'delivery', 'shipping'
    ]
    if any(keyword in text for keyword in order_keywords):
        return 'order'
    
    # Техподдержка
    support_keywords = [
        'support', 'hilfe', 'help', 'unterstützung', 'assistance',
        'how to', 'wie kann', 'anleitun', 'tutorial'
    ]
    if any(keyword in text for keyword in support_keywords):
        return 'support'
    
    # Уведомления (автоматические)
    notification_keywords = [
        'notification', 'benachrichtigung', 'alert', 'reminder',
        'erinnerung', 'update', 'confirmation', 'bestätigung',
        'noreply', 'no-reply', 'automated'
    ]
    if any(keyword in text for keyword in notification_keywords):
        return 'notification'
    
    # Маркетинг
    marketing_keywords = [
        'angebot', 'offer', 'rabatt', 'discount', 'sale',
        'aktion', 'promotion', 'newsletter', 'unsubscribe'
    ]
    if any(keyword in text for keyword in marketing_keywords):
        return 'marketing'
    
    # Запросы информации
    inquiry_keywords = [
        'anfrage', 'inquiry', 'question', 'frage', 'information',
        'details', 'können sie', 'can you', 'would you', 'könnten'
    ]
    if any(keyword in text for keyword in inquiry_keywords):
        return 'inquiry'
    
    return 'other'


def detect_priority(subject: str, body_text: str) -> str:
    """
    Определить приоритет письма
    
    Returns:
        'urgent', 'high', 'normal', 'low'
    """
    text = f"{subject} {body_text}".lower()
    
    # Срочные маркеры
    urgent_keywords = [
        'urgent', 'dringend', 'sofort', 'immediately', 'asap',
        'notfall', 'emergency', 'kritisch', 'critical', '!!!',
        'wichtig!', 'important!'
    ]
    if any(keyword in text for keyword in urgent_keywords):
        return 'urgent'
    
    # Высокий приоритет
    high_keywords = [
        'wichtig', 'important', 'priorität', 'priority',
        'deadline', 'frist', 'heute', 'today', 'morgen', 'tomorrow'
    ]
    if any(keyword in text for keyword in high_keywords):
        return 'high'
    
    # Низкий приоритет
    low_keywords = [
        'newsletter', 'unsubscribe', 'werbung', 'advertisement',
        'marketing', 'optional', 'freiwillig'
    ]
    if any(keyword in text for keyword in low_keywords):
        return 'low'
    
    return 'normal'


def detect_sentiment(text: str) -> str:
    """
    Определить тональность письма
    
    Returns:
        'positive', 'neutral', 'negative'
    """
    # Позитивные слова
    positive_words = [
        'danke', 'thank', 'super', 'excellent', 'great', 'wonderful',
        'perfekt', 'perfect', 'zufrieden', 'satisfied', 'happy',
        'freue', 'appreciate', 'schätzen'
    ]
    positive_score = sum(1 for word in positive_words if word in text)
    
    # Негативные слова
    negative_words = [
        'problem', 'fehler', 'error', 'schlecht', 'bad', 'terrible',
        'unzufrieden', 'dissatisfied', 'angry', 'ärgerlich', 'disappointed',
        'enttäuscht', 'complaint', 'beschwerde', 'nicht gut', 'not good'
    ]
    negative_score = sum(1 for word in negative_words if word in text)
    
    if negative_score > positive_score:
        return 'negative'
    elif positive_score > negative_score:
        return 'positive'
    else:
        return 'neutral'


def detect_intent(subject: str, body_text: str) -> str:
    """
    Определить намерение отправителя
    
    Returns:
        'request_info', 'request_action', 'provide_info', 'feedback', 'other'
    """
    text = f"{subject} {body_text}".lower()
    
    # Запрос информации
    info_patterns = [
        r'\b(was|what|wie|how|wann|when|wo|where|warum|why)\b',
        r'\b(können sie|can you|würden sie|would you).*\b(sagen|tell|erklären|explain)\b',
        r'\b(ich hätte gerne|i would like).*\b(information|details|auskunft)\b'
    ]
    if any(re.search(pattern, text) for pattern in info_patterns):
        return 'request_info'
    
    # Запрос действия
    action_patterns = [
        r'\b(bitte|please).*\b(senden|send|machen|do|erstellen|create)\b',
        r'\b(könnten sie|could you|können sie|can you)\b',
        r'\b(ich brauche|i need|ich benötige|i require)\b'
    ]
    if any(re.search(pattern, text) for pattern in action_patterns):
        return 'request_action'
    
    # Предоставление информации
    provide_patterns = [
        r'\b(hier ist|here is|anbei|attached|im anhang|in attachment)\b',
        r'\b(ich sende|i send|i am sending|ich schicke)\b',
        r'\b(finden sie|you will find|sie erhalten|you receive)\b'
    ]
    if any(re.search(pattern, text) for pattern in provide_patterns):
        return 'provide_info'
    
    # Отзыв/feedback
    feedback_patterns = [
        r'\b(feedback|rückmeldung|bewertung|review|meinung|opinion)\b',
        r'\b(ich finde|i think|meiner meinung|in my opinion)\b'
    ]
    if any(re.search(pattern, text) for pattern in feedback_patterns):
        return 'feedback'
    
    return 'other'


def detect_question(text: str) -> bool:
    """Проверить, содержит ли письмо вопросы"""
    question_markers = ['?', 'was ', 'wie ', 'wann ', 'wo ', 'warum ', 
                       'what ', 'how ', 'when ', 'where ', 'why ',
                       'können sie', 'can you', 'würden sie', 'would you']
    return any(marker in text.lower() for marker in question_markers)


def detect_attachment_request(text: str) -> bool:
    """Проверить, запрашивается ли вложение"""
    attachment_keywords = [
        'senden sie', 'send me', 'schicken sie', 'anhängen', 'attach',
        'datei', 'file', 'dokument', 'document', 'bericht', 'report'
    ]
    return any(keyword in text.lower() for keyword in attachment_keywords)


def detect_automated_message(from_email: str, subject: str, body_text: str) -> bool:
    """Определить, является ли письмо автоматическим"""
    auto_indicators = [
        'noreply', 'no-reply', 'donotreply', 'automated',
        'automatic', 'automatisch', 'system@', 'robot@'
    ]
    
    email_lower = from_email.lower()
    text_lower = f"{subject} {body_text}".lower()
    
    return (any(indicator in email_lower for indicator in auto_indicators) or
            'do not reply' in text_lower or
            'nicht antworten' in text_lower)


def detect_language(text: str) -> str:
    """
    Определить язык письма (базовая эвристика)
    
    Returns:
        'de', 'en', 'unknown'
    """
    # Характерные немецкие слова
    german_words = ['der', 'die', 'das', 'und', 'ist', 'mit', 'für', 
                   'von', 'auf', 'eine', 'einen', 'ich', 'sie']
    german_score = sum(1 for word in german_words if f' {word} ' in text)
    
    # Характерные английские слова
    english_words = ['the', 'and', 'is', 'are', 'was', 'were', 'with',
                    'for', 'from', 'that', 'this', 'have', 'has']
    english_score = sum(1 for word in english_words if f' {word} ' in text)
    
    if german_score > english_score * 1.5:
        return 'de'
    elif english_score > german_score * 1.5:
        return 'en'
    else:
        return 'unknown'


def suggest_labels(subject: str, body_text: str) -> List[str]:
    """
    Предложить метки для письма на основе содержимого
    
    Returns:
        список рекомендуемых меток
    """
    labels = []
    text = f"{subject} {body_text}".lower()
    
    # Метки по категориям
    if any(word in text for word in ['rechnung', 'invoice', 'payment']):
        labels.append('Rechnung')
    
    if any(word in text for word in ['bestellung', 'order']):
        labels.append('Bestellung')
    
    if any(word in text for word in ['problem', 'fehler', 'beschwerde']):
        labels.append('Problem')
    
    if any(word in text for word in ['anfrage', 'question', 'frage']):
        labels.append('Anfrage')
    
    if any(word in text for word in ['dringend', 'urgent', 'asap']):
        labels.append('Dringend')
    
    if any(word in text for word in ['vertrag', 'contract']):
        labels.append('Vertrag')
    
    if any(word in text for word in ['angebot', 'offer', 'quote']):
        labels.append('Angebot')
    
    return labels


def calculate_reply_confidence(
    message_analysis: Dict,
    thread_length: int,
    counterparty_trust: str,
    security_status: str
) -> Tuple[float, List[str]]:
    """
    Рассчитать уверенность в автоматическом ответе
    
    Args:
        message_analysis: результат analyze_message
        thread_length: количество сообщений в треде
        counterparty_trust: уровень доверия к контрагенту
        security_status: статус безопасности
    
    Returns:
        (confidence_score, reasons) - оценка 0-1 и причины снижения
    """
    confidence = 1.0
    reasons = []
    
    # Снижаем уверенность при проблемах безопасности
    if security_status in ['blocked', 'warning']:
        confidence -= 0.3
        reasons.append('Sicherheitswarnung')
    
    # Снижаем при низком доверии к отправителю
    if counterparty_trust == 'low':
        confidence -= 0.2
        reasons.append('Niedriges Vertrauensniveau')
    
    # Снижаем при негативной тональности
    if message_analysis.get('sentiment') == 'negative':
        confidence -= 0.15
        reasons.append('Negative Stimmung')
    
    # Снижаем при жалобах
    if message_analysis.get('category') == 'complaint':
        confidence -= 0.2
        reasons.append('Beschwerde erfordert persönliche Betreuung')
    
    # Снижаем при высоком приоритете
    if message_analysis.get('priority') == 'urgent':
        confidence -= 0.15
        reasons.append('Dringliche Nachricht')
    
    # Снижаем при первом контакте
    if thread_length == 0:
        confidence -= 0.1
        reasons.append('Erstkontakt')
    
    # Повышаем при длинном треде (постоянная переписка)
    if thread_length > 3:
        confidence += 0.1
        if confidence > 1.0:
            confidence = 1.0
    
    # Повышаем при высоком доверии
    if counterparty_trust == 'vip':
        confidence += 0.1
        if confidence > 1.0:
            confidence = 1.0
    
    return max(0.0, min(1.0, confidence)), reasons
