"""
Chatbot routes — powered by Claude (Anthropic).
"""
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
import os
from datetime import datetime
import anthropic

chatbot_bp = Blueprint("chatbot", __name__, template_folder="../templates")

CLAUDE_MODEL = "claude-sonnet-4-6"

# Module-level client — initialized lazily on first request to avoid import-time failures
_client: anthropic.Anthropic | None = None

def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client

# System prompt — адаптирован под VAT Verifizierung платформу
CHATBOT_SYSTEM_PROMPT = """Du bist ein hilfreicher KI-Assistent der VAT Verifizierung Plattform (vat-verifizierung.de).

Die Plattform bietet folgende Module:

1. VIES USt-IdNr. Prüfung — Echtzeit-Validierung von EU-Umsatzsteuer-IDs über die offizielle VIES-Datenbank.
2. Handelsregister — Firmendaten aus deutschem, tschechischem, polnischem und ukrainischem Register.
3. Sanktionslisten — Automatischer Abgleich mit EU, OFAC und UK Sanktionslisten.
4. OSINT Scanner — Domain-Analyse, DNS, SSL, WHOIS, Security Headers, Social Media.
5. Phone Intelligence — Telefonnummern-Analyse mit Spam-Erkennung für USA und Europa.
6. Link Scanner — URLs auf Phishing und Malware prüfen (VirusTotal + Google Safe Browsing).
7. MailGuard AI — KI-gestützte E-Mail-Verwaltung mit Gmail/Outlook-OAuth, automatischen Antworten.
8. Website Security Scanner — 7 Schwachstellen-Checks, SSL/TLS-Analyse, KI-Empfehlungen.
9. Smart CRM — Geprüfte Kontrahenten verwalten, Notizen, Tags, Prüfungshistorie.
10. KI-Assistent — Dieser Chatbot, beantwortet Fragen 24/7.
11. EU Compliance Checker (NEU, kostenlos, ohne Registrierung) — Prüft Websites auf Impressum (§5 TMG), Datenschutzerklärung (DSGVO Art.13/14), AGB (BGB§305), Widerrufsbelehrung (§355 BGB) und Cookie-Banner. Ergebnis: Score 0-100, Detailanalyse pro Seite, KI-Zusammenfassung. URL: /compliance-check/
12. KI B2B Marktforschung (NEU, kostenlos, ohne Registrierung) — 15 synthetische deutsche B2B-Entscheider (Geschäftsführer, CFO, IT-Leiterin, Steuerberaterin, Startup-Gründer u.a.) bewerten ein Produkt oder Tool. Ergebnisse: Ø Relevanz (1-10), Zahlungsbereitschaft (EUR/Monat mit Perzentilen), Kaufbereitschaft (%), Hauptbedenken, Hauptvorteile, Executive Summary. Läuft ca. 60 Sekunden. URL: /consumer-panel/

Abo-Pläne: Free (0€, 1 Prüfung/Monat), Basic (9,99€/Monat, 100 Prüfungen), Professional (49,90€/Monat, 500 Prüfungen).

Die beiden neuen Tools (EU Compliance Checker und KI B2B Marktforschung) sind komplett kostenlos und ohne Registrierung nutzbar.

Antworte auf Deutsch, präzise und freundlich. Wenn du dir bei etwas unsicher bist, sage es ehrlich.
"""


@chatbot_bp.route("/chat", methods=["GET"])
def chat_page():
    return render_template("chatbot/chat.html", now=datetime.now())


@chatbot_bp.route("/api/chat/message", methods=["POST"])
@login_required
def send_message():
    """Chat endpoint using Claude Messages API."""
    try:
        data = request.get_json()
        user_message = (data.get("message") or "").strip()
        history = data.get("history") or []   # [{role, content}, ...]

        if not user_message:
            return jsonify({"error": "Message is required"}), 400

        client = _get_client()

        # Контекст пользователя
        subscription = getattr(current_user, 'subscription', None)
        plan = getattr(subscription, 'plan', 'free') if subscription else 'free'
        user_context = (
            f"[Benutzerkontext: E-Mail={current_user.email}, "
            f"Name={current_user.first_name} {current_user.last_name}, "
            f"Plan={plan}, Admin={'Ja' if current_user.is_admin else 'Nein'}]"
        )

        # Строим историю (последние 20 сообщений)
        messages = []
        for msg in history[-20:]:
            role = msg.get("role")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        # Добавляем контекст к первому или текущему сообщению
        messages.append({"role": "user", "content": f"{user_context}\n\n{user_message}"})

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=800,
            system=CHATBOT_SYSTEM_PROMPT,
            messages=messages
        )

        reply = response.content[0].text

        return jsonify({
            "response": reply,
            "timestamp": datetime.utcnow().isoformat(),
        })

    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except anthropic.AuthenticationError:
        return jsonify({"error": "Ungültiger Anthropic API-Schlüssel"}), 500
    except anthropic.RateLimitError:
        return jsonify({"error": "Zu viele Anfragen. Bitte kurz warten und erneut versuchen."}), 429
    except anthropic.APIConnectionError:
        return jsonify({"error": "Verbindung zu Claude nicht möglich. Bitte erneut versuchen."}), 503
    except anthropic.APIStatusError as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Claude API Fehler: {e.status_code}"}), 502
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@chatbot_bp.route("/api/chat/history", methods=["GET"])
@login_required
def get_chat_history():
    return jsonify({
        "messages": [],
        "note": "Chat history storage not yet implemented"
    })
