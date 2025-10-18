# FILE: services/chatbot_routes.py
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
import httpx
import os
import asyncio
from datetime import datetime

chatbot_bp = Blueprint("chatbot", __name__, template_folder="../templates")

# OpenAI Agent Builder API endpoint
AGENT_API_URL = os.getenv("OPENAI_AGENT_API_URL", "https://api.openai.com/v1/agents/run")
AGENT_API_KEY = os.getenv("OPENAI_AGENT_API_KEY", "")


@chatbot_bp.route("/chat", methods=["GET"])
def chat_page():
    """Сторінка з чат-інтерфейсом"""
    return render_template("chatbot/chat.html")


@chatbot_bp.route("/api/chat/message", methods=["POST"])
@login_required
async def send_message():
    """API endpoint для відправки повідомлень до AI асистента"""
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip()
        
        if not user_message:
            return jsonify({"error": "Message is required"}), 400
        
        # Контекст користувача для персоналізації
        user_context = {
            "user_email": current_user.email,
            "user_name": f"{current_user.first_name} {current_user.last_name}",
            "subscription_plan": getattr(current_user.subscription, 'plan', 'free') if hasattr(current_user, 'subscription') else 'free',
            "is_admin": current_user.is_admin
        }
        
        # Виклик Agent Builder workflow
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                AGENT_API_URL,
                json={
                    "input_as_text": user_message,
                    "context": user_context
                },
                headers={
                    "Authorization": f"Bearer {AGENT_API_KEY}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code != 200:
                return jsonify({
                    "error": "Agent API error",
                    "details": response.text
                }), 500
            
            agent_response = response.json()
            
            return jsonify({
                "response": agent_response.get("output_text", "Вибачте, не вдалося отримати відповідь."),
                "timestamp": datetime.utcnow().isoformat(),
                "user_context": user_context
            })
    
    except httpx.TimeoutException:
        return jsonify({"error": "Agent timeout. Please try again."}), 504
    except Exception as e:
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
