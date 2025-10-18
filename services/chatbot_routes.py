# FILE: services/chatbot_routes.py
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
import os
from datetime import datetime
from openai import OpenAI

chatbot_bp = Blueprint("chatbot", __name__, template_folder="../templates")

# OpenAI client з API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

# Assistants API v2 header (для всіх запитів)
V2_HEADERS = {"OpenAI-Beta": "assistants=v2"}

# Agent Builder workflow ID (або Assistant ID)
AGENT_WORKFLOW_ID = os.getenv("OPENAI_AGENT_WORKFLOW_ID", "asst_vi3FV2KYJYJXrvSJGEa4ThE2")


@chatbot_bp.route("/chat", methods=["GET"])
def chat_page():
    """Сторінка з чат-інтерфейсом"""
    return render_template("chatbot/chat.html", now=datetime.now())


@chatbot_bp.route("/api/chat/message", methods=["POST"])
@login_required
def send_message():
    """API endpoint для відправки повідомлень до AI асистента через Agents SDK"""
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip()
        
        if not user_message:
            return jsonify({"error": "Message is required"}), 400
        
        # Перевірка наявності API ключа
        if not client.api_key:
            return jsonify({
                "error": "API key not configured",
                "details": "OPENAI_API_KEY environment variable is not set"
            }), 500
        
        # Контекст користувача для персоналізації
        user_context = f"""
Benutzerkontext:
- E-Mail: {current_user.email}
- Name: {current_user.first_name} {current_user.last_name}
- Abonnement: {getattr(current_user.subscription, 'plan', 'free') if hasattr(current_user, 'subscription') else 'free'}
- Administrator: {'Ja' if current_user.is_admin else 'Nein'}
"""
        
        # Повне повідомлення з контекстом
        full_message = f"{user_context}\n\nBenutzeranfrage: {user_message}"
        
        print(f"[CHATBOT] Using Agents SDK with workflow: {AGENT_WORKFLOW_ID}")
        print(f"[CHATBOT] User message: {user_message}")
        
        # Створюємо thread для розмови (з v2 header)
        thread = client.beta.threads.create(extra_headers=V2_HEADERS)
        print(f"[CHATBOT] Created thread: {thread.id}")
        
        # Додаємо повідомлення користувача
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=full_message,
            extra_headers=V2_HEADERS
        )
        
        # Запускаємо агента з вашим workflow
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=AGENT_WORKFLOW_ID,
            extra_headers=V2_HEADERS
        )
        print(f"[CHATBOT] Started run: {run.id}")
        
        # Чекаємо завершення (polling)
        import time
        max_wait = 60  # seconds
        elapsed = 0
        while run.status in ['queued', 'in_progress', 'requires_action'] and elapsed < max_wait:
            time.sleep(2)
            elapsed += 2
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id,
                extra_headers=V2_HEADERS
            )
            print(f"[CHATBOT] Run status: {run.status} (elapsed: {elapsed}s)")
        
        if run.status != 'completed':
            error_details = getattr(run, 'last_error', None)
            print(f"[CHATBOT] Run failed with status: {run.status}, error: {error_details}")
            return jsonify({
                "error": f"Agent run failed with status: {run.status}",
                "details": str(error_details) if error_details else "Unknown error"
            }), 500
        
        # Отримуємо відповідь від агента
        messages = client.beta.threads.messages.list(
            thread_id=thread.id,
            extra_headers=V2_HEADERS
        )
        assistant_messages = [msg for msg in messages.data if msg.role == 'assistant']
        
        if not assistant_messages:
            print("[CHATBOT] No assistant messages found")
            return jsonify({"error": "No response from assistant"}), 500
        
        # Беремо останнє повідомлення асистента
        latest_message = assistant_messages[0]
        response_text = latest_message.content[0].text.value
        
        print(f"[CHATBOT] Success! Response length: {len(response_text)} chars")
        
        return jsonify({
            "response": response_text,
            "timestamp": datetime.utcnow().isoformat(),
            "thread_id": thread.id
        })
    
    except Exception as e:
        print(f"[CHATBOT] Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@chatbot_bp.route("/api/chat/history", methods=["GET"])
@login_required
def get_chat_history():
    """Отримати історію чату користувача (опціонально - зберігати в БД)"""
    # TODO: Implement chat history storage in database
    return jsonify({
        "messages": [],
        "note": "Chat history storage not yet implemented"
    })
