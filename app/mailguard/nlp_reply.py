"""
Email reply generation using Claude (Anthropic).
"""
import anthropic
from flask import current_app
from datetime import datetime

CLAUDE_MODEL = "claude-sonnet-4-6"


def build_reply(counterparty_profile, thread_history, inbound_message, assistant_profile=None):
    """
    Generate a reply to an incoming email.

    Returns:
        dict: {'text', 'html', 'confidence', 'analysis', 'reasons'}
    """
    try:
        api_key = current_app.config.get('ANTHROPIC_API_KEY')
        if not api_key:
            return _error_reply('Anthropic API key not configured')

        from .mail_analyzer import analyze_message, calculate_reply_confidence

        subject = inbound_message.get('subject', '')
        text = inbound_message.get('text', '')
        from_email = inbound_message.get('from_email', '')

        message_analysis = analyze_message(subject, text, from_email)

        thread_length = len(thread_history)
        counterparty_trust = counterparty_profile.get('trust_level', 'medium')
        security_status = (inbound_message.get('security') or {}).get('status', 'review')

        confidence, reasons = calculate_reply_confidence(
            message_analysis, thread_length, counterparty_trust, security_status
        )

        client = anthropic.Anthropic(api_key=api_key)

        system_prompt = build_system_prompt(counterparty_profile, assistant_profile, message_analysis)
        user_prompt = build_user_prompt(thread_history, inbound_message, message_analysis)

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        reply_text = response.content[0].text.strip()

        return {
            'text': reply_text,
            'html': text_to_html(reply_text),
            'confidence': confidence,
            'analysis': message_analysis,
            'reasons': reasons
        }

    except Exception as e:
        current_app.logger.error(f"Claude reply generation error: {e}")
        return _error_reply(str(e))


def _error_reply(msg: str) -> dict:
    return {
        'text': f'Fehler bei der Antwortgenerierung: {msg}',
        'html': f'<p>Fehler: {msg}</p>',
        'confidence': 0.0,
        'analysis': {},
        'reasons': [msg]
    }


def build_system_prompt(counterparty_profile, assistant_profile=None, message_analysis=None):
    """Build system prompt for Claude."""
    tone = counterparty_profile.get('tone', 'professionell')
    language = detect_language(counterparty_profile)

    sections = [
        "Du bist der offizielle E-Mail-Assistent der MailGuard-Plattform und betreust die Geschäftskorrespondenz.",
        "Deine Aufgabe: einen Antwort-Entwurf erstellen, der alle Richtlinien beachtet.",
        "Der Entwurf wird nicht automatisch versendet — er bleibt ein Vorschlag.",
        f"- Sprache: {language}",
        f"- Ton: {tone} (sachlich, freundlich, präzise)",
        "- Struktur: kurze Einleitung → konkrete Antworten → nächste Schritte → abschließender Gruß",
        "- Erfinde keine Fakten und nenne nur Inhalte aus dem E-Mail-Text oder den Richtlinien",
        "- Beginne mit Sicherheitsstatus (z.B. 'Sicherheitsprüfung: ✅ ...') basierend auf Prüfungsdaten",
    ]

    if message_analysis:
        category_names = {
            'invoice': 'Rechnung/Zahlung', 'complaint': 'Beschwerde',
            'order': 'Bestellung', 'support': 'Support-Anfrage',
            'inquiry': 'Informationsanfrage', 'other': 'Allgemein'
        }
        sections.append(f"\nNachrichtenanalyse:")
        sections.append(f"- Kategorie: {category_names.get(message_analysis.get('category', 'other'), 'Allgemein')}")
        if message_analysis.get('priority') in ('urgent', 'high'):
            sections.append(f"- Priorität: {message_analysis['priority'].upper()} — bitte zeitnah reagieren")
        if message_analysis.get('has_question'):
            sections.append("- Enthält Fragen — stelle sicher, dass alle beantwortet werden")

    if assistant_profile and assistant_profile.get('instructions'):
        sections.append("Zusätzliche Richtlinie:\n" + assistant_profile['instructions'])
    if assistant_profile and assistant_profile.get('faq'):
        sections.append("FAQ-Auszüge:\n" + assistant_profile['faq'])

    return "\n\n".join(sections)


def build_user_prompt(thread_history, inbound_message, message_analysis=None):
    prompt = (
        f"Eingangsnachricht:\n"
        f"Betreff: {inbound_message.get('subject', 'Ohne Betreff')}\n"
        f"Text: {inbound_message.get('text', '')}\n\n"
    )

    security = inbound_message.get('security') or {}
    if security:
        prompt += (
            f"Sicherheitsbewertung:\n"
            f"- Status: {security.get('status_label', security.get('status', 'Unbekannt'))}\n"
        )
        if security.get('score') is not None:
            prompt += f"- Score: {security['score']}/100\n"
        if security.get('summary'):
            prompt += f"- Zusammenfassung: {security['summary']}\n"
        prompt += "\n"

    if message_analysis:
        prompt += (
            f"Automatische Analyse:\n"
            f"- Kategorie: {message_analysis.get('category', 'other')}\n"
            f"- Priorität: {message_analysis.get('priority', 'normal')}\n"
            f"- Stimmung: {message_analysis.get('sentiment', 'neutral')}\n\n"
        )

    if thread_history:
        prompt += "Vorherige Nachrichten:\n"
        for msg in thread_history[-3:]:
            prompt += f"- {msg.get('direction', 'eingehend')}: {msg.get('subject', '')[:50]}\n"
        prompt += "\n"

    prompt += (
        "Erstelle einen höflichen, sachlichen Geschäftsbrief-Entwurf mit konkreten nächsten Schritten. "
        "Beginne mit einem kurzen 'Kurzüberblick' (2-3 Sätze), dann Sicherheitsstatus und Empfehlungen."
    )
    return prompt


def detect_language(counterparty_profile):
    domain = counterparty_profile.get('domain', '').lower()
    german_domains = ['.de', '.at', '.ch', 'germany', 'deutsch']
    if any(g in domain for g in german_domains):
        return 'Deutsch'
    return 'Englisch'


def text_to_html(text):
    html = text.replace('\n', '<br>')
    if not html.startswith('<p>'):
        html = f'<p>{html}</p>'
    return html


def get_counterparty_profile(counterparty):
    return {
        'display_name': counterparty.display_name,
        'email': counterparty.email,
        'domain': counterparty.domain,
        'tone': 'professionell',
        'language': detect_language({'domain': counterparty.domain}),
        'assistant_profile_id': counterparty.assistant_profile_id
    }


def get_thread_history(message):
    return []
