"""
Alternative chatbot implementation using OpenAI SDK directly
This can be used if Agent Builder API has different endpoint structure
"""
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
import os
from datetime import datetime
from openai import OpenAI

chatbot_sdk_bp = Blueprint("chatbot_sdk", __name__, template_folder="../templates")

# OpenAI client with API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

# Agent/Assistant ID from Agent Builder
ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID", "")
# Or use your workflow ID: wf_68f3ed065d5881909c95b20ad801090b07e400bf50570e4d


@chatbot_sdk_bp.route("/chat", methods=["GET"])
def chat_page():
    """Сторінка з чат-інтерфейсом"""
    return render_template("chatbot/chat.html", now=datetime.now())


@chatbot_sdk_bp.route("/api/chat/message", methods=["POST"])
@login_required
def send_message():
    """API endpoint використовуючи OpenAI SDK"""
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip()
        
        if not user_message:
            return jsonify({"error": "Message is required"}), 400
        
        if not ASSISTANT_ID:
            return jsonify({
                "error": "Assistant not configured",
                "details": "OPENAI_ASSISTANT_ID environment variable is not set"
            }), 500
        
        # Контекст користувача
        user_context = {
            "user_email": current_user.email,
            "user_name": f"{current_user.first_name} {current_user.last_name}",
            "subscription_plan": getattr(current_user.subscription, 'plan', 'free') if hasattr(current_user, 'subscription') else 'free',
            "is_admin": current_user.is_admin
        }
        
        print(f"[CHATBOT_SDK] Using Assistant ID: {ASSISTANT_ID}")
        print(f"[CHATBOT_SDK] User message: {user_message}")
        
        # Створюємо thread для розмови
        thread = client.beta.threads.create()
        
        # Додаємо повідомлення користувача
        context_message = f"User context: {user_context}\n\nUser question: {user_message}"
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=context_message
        )
        
        # Запускаємо асистента
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )
        
        # Чекаємо завершення (з таймаутом)
        import time
        max_wait = 60  # seconds
        elapsed = 0
        while run.status in ['queued', 'in_progress'] and elapsed < max_wait:
            time.sleep(1)
            elapsed += 1
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
        
        if run.status != 'completed':
            return jsonify({
                "error": f"Assistant run failed with status: {run.status}",
                "details": getattr(run, 'last_error', None)
            }), 500
        
        # Отримуємо відповідь
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        assistant_message = next(
            (msg for msg in messages.data if msg.role == 'assistant'),
            None
        )
        
        if not assistant_message:
            return jsonify({"error": "No response from assistant"}), 500
        
        response_text = assistant_message.content[0].text.value
        
        return jsonify({
            "response": response_text,
            "timestamp": datetime.utcnow().isoformat(),
            "user_context": user_context
        })
    
    except Exception as e:
        print(f"[CHATBOT_SDK] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@chatbot_sdk_bp.route("/api/chat/history", methods=["GET"])
@login_required
def get_chat_history():
    """Отримати історію чату"""
    return jsonify({
        "messages": [],
        "note": "Chat history storage not yet implemented"
    })
