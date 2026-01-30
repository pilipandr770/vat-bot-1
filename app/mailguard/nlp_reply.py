import openai
from flask import current_app
import json
from datetime import datetime

def build_reply(counterparty_profile, thread_history, inbound_message, assistant_profile=None):
    """
    Сгенерировать ответ на входящее сообщение с расширенным анализом

    Args:
        counterparty_profile: профиль контрагента (dict)
        thread_history: история переписки (list of dicts)
        inbound_message: входящее сообщение (dict)
        assistant_profile: профиль ассистента (optional dict)

    Returns:
        dict: {'text': str, 'html': str, 'confidence': float, 'analysis': dict, 'reasons': list}
    """
    try:
        # Получаем API ключ
        api_key = current_app.config.get('OPENAI_API_KEY')
        if not api_key:
            return {
                'text': 'Ошибка: OpenAI API ключ не настроен',
                'html': '<p>Ошибка: OpenAI API ключ не настроен</p>',
                'confidence': 0.0,
                'analysis': {},
                'reasons': ['API key not configured']
            }

        # Анализируем сообщение
        from .mail_analyzer import analyze_message, calculate_reply_confidence
        
        subject = inbound_message.get('subject', '')
        text = inbound_message.get('text', '')
        from_email = inbound_message.get('from_email', '')
        
        message_analysis = analyze_message(subject, text, from_email)
        
        # Рассчитываем уверенность
        thread_length = len(thread_history)
        counterparty_trust = counterparty_profile.get('trust_level', 'medium')
        security = inbound_message.get('security') or {}
        security_status = security.get('status', 'review')
        
        confidence, reasons = calculate_reply_confidence(
            message_analysis,
            thread_length,
            counterparty_trust,
            security_status
        )

        # Настраиваем OpenAI
        client = openai.OpenAI(api_key=api_key)

        # Формируем системный промпт с учетом анализа
        system_prompt = build_system_prompt(counterparty_profile, assistant_profile, message_analysis)

        # Формируем пользовательский промпт
        user_prompt = build_user_prompt(thread_history, inbound_message, message_analysis)

        # Вызываем OpenAI
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Или gpt-3.5-turbo для экономии
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )

        # Получаем ответ
        reply_text = response.choices[0].message.content.strip()

        # Конвертируем в HTML (простая версия)
        reply_html = text_to_html(reply_text)

        return {
            'text': reply_text,
            'html': reply_html,
            'confidence': confidence,
            'analysis': message_analysis,
            'reasons': reasons
        }

    except Exception as e:
        current_app.logger.error(f"Error generating reply: {e}")
        return {
            'text': f'Ошибка генерации ответа: {str(e)}',
            'html': f'<p>Ошибка генерации ответа: {str(e)}</p>',
            'confidence': 0.0,
            'analysis': {},
            'reasons': [str(e)]
        }

def build_system_prompt(counterparty_profile, assistant_profile=None, message_analysis=None):
    """Создать системный промпт для OpenAI с учетом анализа сообщения"""
    tone = counterparty_profile.get('tone', 'professionell')
    language = detect_language(counterparty_profile)

    prompt_sections = [
        "Du bist der offizielle E-Mail-Assistent der MailGuard-Plattform unseres Unternehmens und betreust die offizielle Geschäftskorrespondenz.",
        "Deine Aufgabe ist es, für eingehende Geschäftsmails einen Entwurf zu erstellen, der die Inhalte des erhaltenen Schreibens aufgreift und alle bereitgestellten Richtlinien beachtet.",
        "Der Entwurf bleibt ein Vorschlag und wird nicht automatisch versendet.",
        "Arbeite stets auf Grundlage der folgenden Leitplanken:",
        f"- Sprache: {language}",
        f"- Ton: {tone} (sachlich, freundlich, präzise)",
        "- Struktur: kurze Einleitung, klare Antworten auf die Anliegen, konkrete nächste Schritte, abschließender Gruß",
        "- Falls Informationen fehlen, frage höflich nach den notwendigen Details",
        "- Nutze Aufzählungen oder nummerierte Listen, wenn sie die Lesbarkeit verbessern",
        "- Erfinde keine Fakten und nenne nur Inhalte, die aus dem E-Mail-Text oder den Richtlinien hervorgehen",
        "- Beginne mit einem klaren Sicherheitsstatus (z.B. 'Sicherheitsprüfung: ✅ ...') basierend auf den gelieferten Prüfungsdaten und weise auf Warnungen hin",
        "- Fasse danach das eingegangene Schreiben in maximal drei Sätzen zusammen, bevor du konkrete Antworten formulierst",
        "- Kennzeichne deutlich, falls eine manuelle Sicherheitsprüfung oder Zurückhaltung geboten ist"
    ]
    
    # Добавляем контекст анализа сообщения
    if message_analysis:
        analysis_context = [
            "\nKontext der Nachrichtenanalyse:"
        ]
        
        category = message_analysis.get('category', 'other')
        category_names = {
            'invoice': 'Rechnung/Zahlung',
            'complaint': 'Beschwerde',
            'order': 'Bestellung',
            'support': 'Support-Anfrage',
            'inquiry': 'Informationsanfrage',
            'notification': 'Benachrichtigung',
            'marketing': 'Marketing',
            'other': 'Allgemein'
        }
        analysis_context.append(f"- Kategorie: {category_names.get(category, category)}")
        
        priority = message_analysis.get('priority', 'normal')
        if priority in ['urgent', 'high']:
            analysis_context.append(f"- Priorität: {priority.upper()} - Bitte zeitnah reagieren")
        
        sentiment = message_analysis.get('sentiment', 'neutral')
        sentiment_names = {'positive': 'positiv', 'negative': 'negativ', 'neutral': 'neutral'}
        analysis_context.append(f"- Stimmung: {sentiment_names.get(sentiment, sentiment)}")
        
        if message_analysis.get('has_question'):
            analysis_context.append("- Enthält Fragen - stelle sicher, dass alle beantwortet werden")
        
        if message_analysis.get('has_attachment_request'):
            analysis_context.append("- Anforderung von Dateien/Dokumenten")
        
        intent = message_analysis.get('intent', 'other')
        if intent == 'request_action':
            analysis_context.append("- Absender erwartet eine Aktion/Handlung")
        elif intent == 'request_info':
            analysis_context.append("- Absender benötigt Informationen")
        
        prompt_sections.extend(analysis_context)

    if assistant_profile and assistant_profile.get('instructions'):
        prompt_sections.append(
            "Zusätzliche benutzerdefinierte Richtlinie:\n" + assistant_profile['instructions']
        )

    if assistant_profile and assistant_profile.get('faq'):
        prompt_sections.append(
            "Relevante FAQ-Auszüge:\n" + assistant_profile['faq']
        )

    return "\n\n".join(prompt_sections)

def build_user_prompt(thread_history, inbound_message, message_analysis=None):
    """Создать пользовательский промпт с анализом"""
    prompt = f"""Входящее письмо:
Тема: {inbound_message.get('subject', 'Без темы')}
Текст: {inbound_message.get('text', '')}

"""

    security = inbound_message.get('security') or {}
    if security:
        status_label = security.get('status_label') or security.get('status') or 'Unbekannt'
        score = security.get('score')
        source = security.get('source') or 'unbekannt'
        summary = security.get('summary')
        prompt += "Sicherheitsbewertung:\n"
        prompt += f"- Status: {status_label} ({security.get('status')})\n"
        if score is not None:
            prompt += f"- Score: {score}/100\n"
        prompt += f"- Quelle: {source}\n"
        if summary:
            prompt += f"- Zusammenfassung: {summary}\n"
        if security.get('dangerous_attachments'):
            prompt += f"- Blockierte Anhänge: {', '.join(security['dangerous_attachments'])}\n"
        if security.get('warning_attachments'):
            prompt += f"- Warnungen bei Anhängen: {', '.join(security['warning_attachments'])}\n"
        if security.get('fallback_used'):
            prompt += "- Hinweis: Ergebnis basiert auf heuristischer Ersatzanalyse.\n"
        prompt += "\n"

    if inbound_message.get('attachments'):
        attachment_lines = []
        for attachment in inbound_message['attachments']:
            name = attachment.get('filename', 'Datei')
            risk = attachment.get('risk_level', 'unbekannt')
            attachment_lines.append(f"{name} (Risiko: {risk})")
        prompt += "Anhänge:\n" + "\n".join(f"- {line}" for line in attachment_lines) + "\n\n"
    
    # Добавляем результаты анализа
    if message_analysis:
        prompt += "Automatische Analyse:\n"
        prompt += f"- Kategorie: {message_analysis.get('category', 'other')}\n"
        prompt += f"- Priorität: {message_analysis.get('priority', 'normal')}\n"
        prompt += f"- Stimmung: {message_analysis.get('sentiment', 'neutral')}\n"
        prompt += f"- Absicht: {message_analysis.get('intent', 'other')}\n"
        
        if message_analysis.get('suggested_labels'):
            prompt += f"- Vorgeschlagene Labels: {', '.join(message_analysis['suggested_labels'])}\n"
        
        prompt += "\n"

    if thread_history:
        prompt += "История переписки:\n"
        for msg in thread_history[-3:]:  # Последние 3 сообщения
            prompt += f"- {msg.get('direction', 'входящее')}: {msg.get('subject', '')[:50]}...\n"
        prompt += "\n"

    prompt += """Сформируй вежливый деловой ответ с конкретными шагами.
Начни с краткого Abschnitt "Kurzüberblick" (2-3 предложения), затем перечисли Sicherheitsstatus und Empfehlungen.
Добавь bullets, если уместно. Будь краток, но информативен."""

    return prompt

def detect_language(counterparty_profile):
    """Определить язык для ответа"""
    # Простая логика определения языка
    domain = counterparty_profile.get('domain', '').lower()

    german_domains = ['.de', '.at', '.ch', 'germany', 'deutsch']
    if any(german in domain for german in german_domains):
        return 'немецкий'

    # По умолчанию английский, но можно расширить
    return 'английский'

def text_to_html(text):
    """Простое конвертирование текста в HTML"""
    # Заменяем переносы строк на <br>
    html = text.replace('\n', '<br>')

    # Оборачиваем в параграфы
    if not html.startswith('<p>'):
        html = f'<p>{html}</p>'

    return html

def get_counterparty_profile(counterparty):
    """Получить профиль контрагента из БД"""
    # counterparty - объект KnownCounterparty
    return {
        'display_name': counterparty.display_name,
        'email': counterparty.email,
        'domain': counterparty.domain,
        'tone': 'профессиональный',  # Можно расширить
        'language': detect_language({'domain': counterparty.domain}),
        'assistant_profile_id': counterparty.assistant_profile_id
    }

def get_thread_history(message):
    """Получить историю переписки по thread_id"""
    # TODO: Реализовать получение истории из БД
    return []