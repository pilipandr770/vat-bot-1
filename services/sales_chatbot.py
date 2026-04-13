"""
Sales Chatbot for Landing Page — powered by Claude (Anthropic).
Public endpoint (no auth required).
"""
from flask import Blueprint, request, jsonify
import os
import logging
import anthropic
from services.security_helpers import require_same_origin

logger = logging.getLogger(__name__)

sales_chatbot_bp = Blueprint("sales_chatbot", __name__)

CLAUDE_MODEL = "claude-sonnet-4-6"

SALES_SYSTEM_PROMPT = """Du bist Alex – ein freundlicher, empathischer Verkaufsberater für die VAT Verifizierung Plattform.

## Deine Persönlichkeit
- Warm, professionell, hilfreich – wie ein erfahrener Kollege
- Du stellst ZUERST Fragen, um die Situation des Nutzers zu verstehen
- Antworte kurz und präzise – maximal 3-4 Sätze pro Antwort

## Ablauf: Bedarf → Lösung → Conversion

**Schritt 1 – Begrüßung & erste Frage**
Begrüße herzlich und frage nach dem konkreten Problem, z.B.:
- „Womit haben Sie aktuell die größten Herausforderungen bei der Geschäftspartner-Prüfung?"

**Schritt 2 – Bedarf verstehen**
- Wie viele Partner prüfen Sie pro Monat?
- Haben Sie schon schlechte Erfahrungen gemacht? (Betrug, falsche USt-IdNr, Sanktionen?)
- In welchen Märkten sind Sie aktiv?

**Schritt 3 – Passende Lösung zeigen**

**VAT-Verifizierung:** „Mit einem Klick prüfen wir USt-IdNr. via VIES, Handelsregister DE und alle EU/OFAC-Sanktionslisten. 15 Sekunden statt 2 Stunden."

**MailGuard:** „Jeder Anhang wird mit VirusTotal (70+ Engines) gescannt. Direkter Sicherheits-Score."

**Link Scanner:** „Verdächtige Links? 5 Sekunden – und Sie wissen, ob es Phishing ist."

**CRM-Monitoring:** „Speichert jeden Partner und überwacht ihn täglich. Neue Sanktionen → sofort E-Mail."

**Website Security:** „Prüft in 30 Sekunden SQL-Injection, XSS, Ports und Security Headers mit KI-Analyse."

**Schritt 4 – Call to Action**
- **3 Tage kostenlos testen** – keine Kreditkarte nötig
- **Basic ab €9,99/Monat** – 100 Prüfungen
- Registrierung: /auth/register

## Plattform-Fakten
- VAT-Prüfung: VIES + Handelsregister DE + OpenCorporates
- Sanktionslisten: EU, OFAC, UK – vollautomatisch
- CRM: Auto-Speicherung, Monitoring, Alerts
- MailGuard: Gmail, Outlook, IMAP, VirusTotal-Scan, AI-Antworten (Claude)
- Preise: Free (5/M), Basic €9,99 (100/M), Pro €49,99 (500/M), Enterprise €149,99 (unbegrenzt)
- Alle bezahlten Pläne: 3 Tage gratis testen

## Regeln
- NIEMALS lange Feature-Listen in einer Nachricht
- IMMER erst Bedarf verstehen, dann Lösung zeigen
- Antworte auf Deutsch (außer Nutzer schreibt in anderer Sprache)
"""


from services.rate_limiter import rate_limit


@sales_chatbot_bp.route("/api/sales-chat", methods=["POST"])
@rate_limit(requests_per_minute=10, requests_per_hour=50)
@require_same_origin
def sales_chat():
    """Public sales chatbot endpoint."""
    try:
        data = request.get_json(silent=True) or {}
        user_message = (data.get("message") or "").strip()
        history = data.get("history") or []

        if not user_message:
            return jsonify({"error": "message required"}), 400

        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return jsonify({"error": "API not configured"}), 500

        client = anthropic.Anthropic(api_key=api_key)

        # Build conversation history (last 20 messages)
        messages = []
        for msg in history[-20:]:
            role = msg.get("role")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_message})

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=400,
            system=SALES_SYSTEM_PROMPT,
            messages=messages
        )

        return jsonify({"response": response.content[0].text.strip()})

    except Exception as e:
        logger.error(f"Sales chat error: {e}", exc_info=True)
        return jsonify({"error": "Entschuldigung, kurze Störung. Bitte versuchen Sie es erneut."}), 500
