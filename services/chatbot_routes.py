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
CHATBOT_SYSTEM_PROMPT = """Du bist ein hilfreicher Assistent der VAT Verifizierung Plattform.
Du hilfst Benutzern bei Fragen zu:
- USt-IdNr. und VAT-Verifizierung über VIES
- Handelsregister-Abfragen
- Sanktionslisten-Prüfungen (EU, OFAC, UK)
- CRM und Kontrollverwaltung
- MailGuard E-Mail-Sicherheit
- Website-Sicherheitsscans
- Abonnement und Preise

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
