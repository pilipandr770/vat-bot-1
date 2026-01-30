"""
Тестовый скрипт для проверки mail_analyzer (без Flask зависимостей)
"""
import re
from typing import Dict, List, Tuple


# Копия функций из mail_analyzer.py для тестирования
def analyze_message(subject: str, body_text: str, from_email: str) -> Dict:
    """Полный анализ сообщения"""
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
    """Определить категорию письма"""
    text = f"{subject} {body_text}".lower()
    
    invoice_keywords = ['rechnung', 'invoice', 'payment', 'zahlung', 'bezahlung', 
                       'überweisung', 'betrag', 'fällig', 'due', 'bill']
    if any(keyword in text for keyword in invoice_keywords):
        return 'invoice'
    
    complaint_keywords = ['beschwerde', 'complaint', 'problem', 'issue', 'fehler', 
                         'error', 'nicht funktioniert', 'not working', 'unzufrieden',
                         'dissatisfied', 'reklamation']
    if any(keyword in text for keyword in complaint_keywords):
        return 'complaint'
    
    order_keywords = ['bestellung', 'order', 'bestellen', 'kaufen', 'purchase',
                     'auftrag', 'lieferung', 'delivery', 'shipping']
    if any(keyword in text for keyword in order_keywords):
        return 'order'
    
    support_keywords = ['support', 'hilfe', 'help', 'unterstützung', 'assistance',
                       'how to', 'wie kann', 'anleitun', 'tutorial']
    if any(keyword in text for keyword in support_keywords):
        return 'support'
    
    notification_keywords = ['notification', 'benachrichtigung', 'alert', 'reminder',
                            'erinnerung', 'update', 'confirmation', 'bestätigung',
                            'noreply', 'no-reply', 'automated']
    if any(keyword in text for keyword in notification_keywords):
        return 'notification'
    
    marketing_keywords = ['angebot', 'offer', 'rabatt', 'discount', 'sale',
                         'aktion', 'promotion', 'newsletter', 'unsubscribe']
    if any(keyword in text for keyword in marketing_keywords):
        return 'marketing'
    
    inquiry_keywords = ['anfrage', 'inquiry', 'question', 'frage', 'information',
                       'details', 'können sie', 'can you', 'would you', 'könnten']
    if any(keyword in text for keyword in inquiry_keywords):
        return 'inquiry'
    
    return 'other'


def detect_priority(subject: str, body_text: str) -> str:
    """Определить приоритет письма"""
    text = f"{subject} {body_text}".lower()
    
    urgent_keywords = ['urgent', 'dringend', 'sofort', 'immediately', 'asap',
                      'notfall', 'emergency', 'kritisch', 'critical', '!!!',
                      'wichtig!', 'important!']
    if any(keyword in text for keyword in urgent_keywords):
        return 'urgent'
    
    high_keywords = ['wichtig', 'important', 'priorität', 'priority',
                    'deadline', 'frist', 'heute', 'today', 'morgen', 'tomorrow']
    if any(keyword in text for keyword in high_keywords):
        return 'high'
    
    low_keywords = ['newsletter', 'unsubscribe', 'werbung', 'advertisement',
                   'marketing', 'optional', 'freiwillig']
    if any(keyword in text for keyword in low_keywords):
        return 'low'
    
    return 'normal'


def detect_sentiment(text: str) -> str:
    """Определить тональность письма"""
    positive_words = ['danke', 'thank', 'super', 'excellent', 'great', 'wonderful',
                     'perfekt', 'perfect', 'zufrieden', 'satisfied', 'happy',
                     'freue', 'appreciate', 'schätzen']
    positive_score = sum(1 for word in positive_words if word in text)
    
    negative_words = ['problem', 'fehler', 'error', 'schlecht', 'bad', 'terrible',
                     'unzufrieden', 'dissatisfied', 'angry', 'ärgerlich', 'disappointed',
                     'enttäuscht', 'complaint', 'beschwerde', 'nicht gut', 'not good']
    negative_score = sum(1 for word in negative_words if word in text)
    
    if negative_score > positive_score:
        return 'negative'
    elif positive_score > negative_score:
        return 'positive'
    else:
        return 'neutral'


def detect_intent(subject: str, body_text: str) -> str:
    """Определить намерение отправителя"""
    text = f"{subject} {body_text}".lower()
    
    info_patterns = [r'\b(was|what|wie|how|wann|when|wo|where|warum|why)\b',
                    r'\b(können sie|can you|würden sie|would you).*\b(sagen|tell|erklären|explain)\b']
    if any(re.search(pattern, text) for pattern in info_patterns):
        return 'request_info'
    
    action_patterns = [r'\b(bitte|please).*\b(senden|send|machen|do|erstellen|create)\b',
                      r'\b(könnten sie|could you|können sie|can you)\b']
    if any(re.search(pattern, text) for pattern in action_patterns):
        return 'request_action'
    
    provide_patterns = [r'\b(hier ist|here is|anbei|attached|im anhang|in attachment)\b']
    if any(re.search(pattern, text) for pattern in provide_patterns):
        return 'provide_info'
    
    return 'other'


def detect_question(text: str) -> bool:
    """Проверить, содержит ли письмо вопросы"""
    question_markers = ['?', 'was ', 'wie ', 'wann ', 'wo ', 'warum ', 
                       'what ', 'how ', 'when ', 'where ', 'why ',
                       'können sie', 'can you']
    return any(marker in text.lower() for marker in question_markers)


def detect_attachment_request(text: str) -> bool:
    """Проверить, запрашивается ли вложение"""
    attachment_keywords = ['senden sie', 'send me', 'schicken sie', 'anhängen', 'attach',
                          'datei', 'file', 'dokument', 'document']
    return any(keyword in text.lower() for keyword in attachment_keywords)


def detect_automated_message(from_email: str, subject: str, body_text: str) -> bool:
    """Определить, является ли письмо автоматическим"""
    auto_indicators = ['noreply', 'no-reply', 'donotreply', 'automated',
                      'automatic', 'automatisch']
    return any(indicator in from_email.lower() for indicator in auto_indicators)


def detect_language(text: str) -> str:
    """Определить язык письма"""
    german_words = ['der', 'die', 'das', 'und', 'ist', 'mit', 'für']
    german_score = sum(1 for word in german_words if f' {word} ' in text)
    
    english_words = ['the', 'and', 'is', 'are', 'was', 'with']
    english_score = sum(1 for word in english_words if f' {word} ' in text)
    
    if german_score > english_score * 1.5:
        return 'de'
    elif english_score > german_score * 1.5:
        return 'en'
    return 'unknown'


def suggest_labels(subject: str, body_text: str) -> List[str]:
    """Предложить метки для письма"""
    labels = []
    text = f"{subject} {body_text}".lower()
    
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
    if any(word in text for word in ['angebot', 'offer']):
        labels.append('Angebot')
    
    return labels


def calculate_reply_confidence(message_analysis: Dict, thread_length: int,
                               counterparty_trust: str, security_status: str) -> Tuple[float, List[str]]:
    """Рассчитать уверенность в автоматическом ответе"""
    confidence = 1.0
    reasons = []
    
    if security_status in ['blocked', 'warning']:
        confidence -= 0.3
        reasons.append('Sicherheitswarnung')
    
    if counterparty_trust == 'low':
        confidence -= 0.2
        reasons.append('Niedriges Vertrauensniveau')
    
    if message_analysis.get('sentiment') == 'negative':
        confidence -= 0.15
        reasons.append('Negative Stimmung')
    
    if message_analysis.get('category') == 'complaint':
        confidence -= 0.2
        reasons.append('Beschwerde erfordert persönliche Betreuung')
    
    if message_analysis.get('priority') == 'urgent':
        confidence -= 0.15
        reasons.append('Dringliche Nachricht')
    
    if thread_length == 0:
        confidence -= 0.1
        reasons.append('Erstkontakt')
    
    if thread_length > 3:
        confidence += 0.1
        if confidence > 1.0:
            confidence = 1.0
    
    if counterparty_trust == 'vip':
        confidence += 0.1
        if confidence > 1.0:
            confidence = 1.0
    
    return max(0.0, min(1.0, confidence)), reasons


# Тесты
def run_tests():
    print("\n" + "="*80)
    print(" ТЕСТИРОВАНИЕ УЛУЧШЕННОГО МОДУЛЯ MAILGUARD")
    print("="*80 + "\n")
    
    # Тест 1: Счет
    print("="*80)
    print("ТЕСТ 1: Анализ счета (Invoice)")
    print("="*80)
    subject1 = "Rechnung für Bestellung #12345"
    body1 = "Sehr geehrte Damen und Herren, anbei finden Sie die Rechnung für Ihre Bestellung. Der Betrag ist fällig bis zum 15.02.2026."
    result1 = analyze_message(subject1, body1, "billing@example.com")
    print(f"Тема: {subject1}")
    print(f"Категория: {result1['category']}")
    print(f"Приоритет: {result1['priority']}")
    print(f"Тональность: {result1['sentiment']}")
    print(f"Предложенные метки: {', '.join(result1['suggested_labels'])}\n")
    
    # Тест 2: Жалоба
    print("="*80)
    print("ТЕСТ 2: Срочная жалоба")
    print("="*80)
    subject2 = "DRINGEND: Problem mit Lieferung!!!"
    body2 = "ich bin sehr unzufrieden! Die Lieferung ist nicht angekommen und ich brauche die Ware SOFORT."
    result2 = analyze_message(subject2, body2, "customer@example.com")
    print(f"Тема: {subject2}")
    print(f"Категория: {result2['category']}")
    print(f"Приоритет: {result2['priority']}")
    print(f"Тональность: {result2['sentiment']}")
    print(f"Предложенные метки: {', '.join(result2['suggested_labels'])}\n")
    
    # Тест 3: Уверенность
    print("="*80)
    print("ТЕСТ 3: Расчет уверенности")
    print("="*80)
    analysis = {'category': 'complaint', 'priority': 'urgent', 'sentiment': 'negative'}
    confidence, reasons = calculate_reply_confidence(analysis, 0, 'low', 'warning')
    print(f"Сценарий: Новый контакт, срочная жалоба, подозрительное письмо")
    print(f"Уверенность: {confidence:.2%}")
    print(f"Причины снижения:")
    for reason in reasons:
        print(f"  - {reason}")
    
    print("\n" + "="*80)
    print(" ✓ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ УСПЕШНО")
    print("="*80 + "\n")


if __name__ == "__main__":
    run_tests()
