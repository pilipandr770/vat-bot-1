"""
Alternative chatbot implementation — Claude (Anthropic).
"""
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
import os
from datetime import datetime
import anthropic

chatbot_sdk_bp = Blueprint("chatbot_sdk", __name__, template_folder="../templates")

CLAUDE_MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """Du bist ein hilfreicher Assistent der VAT Verifizierung Plattform.
Beantworte Fragen zu USt-IdNr-Prüfungen, Handelsregister, Sanktionslisten, MailGuard und Sicherheitsscans.
Antworte kurz, präzise und auf Deutsch."""


@chatbot_sdk_bp.route("/chat", methods=["GET"])
def chat_page():
    return render_template("chatbot/chat.html", now=datetime.now())


@chatbot_sdk_bp.route("/api/chat/message", methods=["POST"])
@login_required
def send_message():
    try:
        data = request.get_json()
        user_message = (data.get("message") or "").strip()

        if not user_message:
            return jsonify({"error": "Message is required"}), 400

        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return jsonify({"error": "ANTHROPIC_API_KEY not configured", "details": "Set ANTHROPIC_API_KEY in .env"}), 500

        client = anthropic.Anthropic(api_key=api_key)

        subscription = getattr(current_user, 'subscription', None)
        plan = getattr(subscription, 'plan', 'free') if subscription else 'free'
        context = (
            f"[Benutzer: {current_user.email}, "
            f"{current_user.first_name} {current_user.last_name}, "
            f"Plan: {plan}]"
        )

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=800,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"{context}\n\n{user_message}"}]
        )

        return jsonify({
            "response": response.content[0].text,
            "timestamp": datetime.utcnow().isoformat(),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
