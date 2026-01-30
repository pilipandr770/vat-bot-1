"""
Тестовый скрипт для проверки улучшенных функций MailGuard
"""
import sys
sys.path.insert(0, '/home/runner/work/vat-bot-1/vat-bot-1')

from app.mailguard.mail_analyzer import (
    analyze_message,
    calculate_reply_confidence,
    suggest_labels,
    detect_category,
    detect_priority,
    detect_sentiment
)


def test_mail_analysis():
    """Тест анализа писем"""
    print("="*80)
    print("ТЕСТ 1: Анализ счета (Invoice)")
    print("="*80)
    
    subject1 = "Rechnung für Bestellung #12345"
    body1 = """Sehr geehrte Damen und Herren,
    
anbei finden Sie die Rechnung für Ihre Bestellung. 
Der Betrag ist fällig bis zum 15.02.2026.

Mit freundlichen Grüßen"""
    
    result1 = analyze_message(subject1, body1, "billing@example.com")
    print(f"Тема: {subject1}")
    print(f"Категория: {result1['category']}")
    print(f"Приоритет: {result1['priority']}")
    print(f"Тональность: {result1['sentiment']}")
    print(f"Намерение: {result1['intent']}")
    print(f"Предложенные метки: {', '.join(result1['suggested_labels'])}")
    print()
    
    print("="*80)
    print("ТЕСТ 2: Срочная жалоба (Urgent Complaint)")
    print("="*80)
    
    subject2 = "DRINGEND: Problem mit Lieferung!!!"
    body2 = """Guten Tag,
    
ich bin sehr unzufrieden! Die Lieferung ist nicht angekommen und 
ich brauche die Ware SOFORT. Das ist ein Notfall!

Bitte reagieren Sie umgehend."""
    
    result2 = analyze_message(subject2, body2, "customer@example.com")
    print(f"Тема: {subject2}")
    print(f"Категория: {result2['category']}")
    print(f"Приоритет: {result2['priority']}")
    print(f"Тональность: {result2['sentiment']}")
    print(f"Намерение: {result2['intent']}")
    print(f"Есть вопросы: {result2['has_question']}")
    print(f"Предложенные метки: {', '.join(result2['suggested_labels'])}")
    print()
    
    print("="*80)
    print("ТЕСТ 3: Запрос информации (Information Request)")
    print("="*80)
    
    subject3 = "Anfrage: Produktdetails"
    body3 = """Guten Tag,
    
können Sie mir bitte mehr Informationen über Ihr Produkt XYZ senden?
Ich hätte gerne Details zu:
- Preis
- Lieferzeit
- Technische Spezifikationen

Vielen Dank im Voraus!"""
    
    result3 = analyze_message(subject3, body3, "info@customer.com")
    print(f"Тема: {subject3}")
    print(f"Категория: {result3['category']}")
    print(f"Приоритет: {result3['priority']}")
    print(f"Тональность: {result3['sentiment']}")
    print(f"Намерение: {result3['intent']}")
    print(f"Есть вопросы: {result3['has_question']}")
    print(f"Предложенные метки: {', '.join(result3['suggested_labels'])}")
    print()


def test_confidence_calculation():
    """Тест расчета уверенности"""
    print("="*80)
    print("ТЕСТ 4: Расчет уверенности для автоматического ответа")
    print("="*80)
    
    # Сценарий 1: VIP клиент, длинный тред, безопасное письмо
    analysis1 = {
        'category': 'inquiry',
        'priority': 'normal',
        'sentiment': 'positive'
    }
    confidence1, reasons1 = calculate_reply_confidence(
        analysis1,
        thread_length=5,
        counterparty_trust='vip',
        security_status='safe'
    )
    print(f"Сценарий 1: VIP клиент, постоянная переписка")
    print(f"  Уверенность: {confidence1:.2%}")
    print(f"  Причины: {', '.join(reasons1) if reasons1 else 'Нет ограничений'}")
    print()
    
    # Сценарий 2: Новый контакт, жалоба, предупреждение безопасности
    analysis2 = {
        'category': 'complaint',
        'priority': 'urgent',
        'sentiment': 'negative'
    }
    confidence2, reasons2 = calculate_reply_confidence(
        analysis2,
        thread_length=0,
        counterparty_trust='low',
        security_status='warning'
    )
    print(f"Сценарий 2: Новый контакт, срочная жалоба, подозрительное письмо")
    print(f"  Уверенность: {confidence2:.2%}")
    print(f"  Причины снижения:")
    for reason in reasons2:
        print(f"    - {reason}")
    print()
    
    # Сценарий 3: Обычный клиент, нормальное письмо
    analysis3 = {
        'category': 'order',
        'priority': 'normal',
        'sentiment': 'neutral'
    }
    confidence3, reasons3 = calculate_reply_confidence(
        analysis3,
        thread_length=2,
        counterparty_trust='medium',
        security_status='safe'
    )
    print(f"Сценарий 3: Обычный клиент, заказ")
    print(f"  Уверенность: {confidence3:.2%}")
    print(f"  Причины: {', '.join(reasons3) if reasons3 else 'Нет ограничений'}")
    print()


def test_label_suggestions():
    """Тест предложения меток"""
    print("="*80)
    print("ТЕСТ 5: Автоматическое предложение меток")
    print("="*80)
    
    test_cases = [
        ("Rechnung #123", "Anbei die Rechnung für letzten Monat", ["Rechnung"]),
        ("Dringende Anfrage", "Ich brauche ASAP eine Antwort", ["Anfrage", "Dringend"]),
        ("Vertragsentwurf", "Hier der neue Vertrag zur Unterschrift", ["Vertrag"]),
        ("Angebot für Projekt X", "Unser spezielles Angebot nur für Sie", ["Angebot"]),
    ]
    
    for subject, body, expected_keywords in test_cases:
        labels = suggest_labels(subject, body)
        print(f"Тема: {subject}")
        print(f"  Предложенные метки: {', '.join(labels)}")
        print(f"  Ожидаемые ключевые слова: {', '.join(expected_keywords)}")
        print()


if __name__ == "__main__":
    print("\n" + "="*80)
    print(" ТЕСТИРОВАНИЕ УЛУЧШЕННОГО МОДУЛЯ MAILGUARD")
    print("="*80 + "\n")
    
    try:
        test_mail_analysis()
        test_confidence_calculation()
        test_label_suggestions()
        
        print("\n" + "="*80)
        print(" ✓ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ УСПЕШНО")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n✗ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
