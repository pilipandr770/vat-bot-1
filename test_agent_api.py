"""
Test script for Claude (Anthropic) API connectivity.
Usage: python test_agent_api.py
"""
import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

CLAUDE_MODEL = "claude-sonnet-4-6"


def test_claude_api():
    """Test direct connection to Anthropic Claude API."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")

    if not api_key:
        print("❌ ERROR: ANTHROPIC_API_KEY not set in .env file")
        return

    print(f"🔑 API Key: {api_key[:15]}...")
    print(f"🤖 Model: {CLAUDE_MODEL}")
    print()

    test_message = "Wie starte ich eine Prüfung? (VAT Verifizierung Plattform)"

    try:
        print(f"📤 Sending message: {test_message}")
        client = anthropic.Anthropic(api_key=api_key)

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=256,
            system="Du bist ein hilfreicher Assistent der VAT Verifizierung Plattform. Antworte kurz auf Deutsch.",
            messages=[{"role": "user", "content": test_message}]
        )

        reply = response.content[0].text
        print()
        print("📥 Claude Response:")
        print(reply)
        print()
        print(f"📊 Usage: input_tokens={response.usage.input_tokens}, output_tokens={response.usage.output_tokens}")
        print("✅ SUCCESS! Claude API is working correctly.")

    except anthropic.AuthenticationError:
        print("❌ ERROR: Invalid ANTHROPIC_API_KEY — check your key at https://console.anthropic.com/")
    except anthropic.RateLimitError:
        print("❌ ERROR: Rate limit exceeded — wait a moment and retry.")
    except anthropic.APIConnectionError as e:
        print(f"❌ ERROR: Connection failed: {e}")
    except Exception as e:
        import traceback
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()


def test_chatbot_endpoint(base_url: str = "http://localhost:5000"):
    """Test the /chatbot/api/chat/message endpoint (requires running Flask app + login cookie)."""
    import httpx

    print()
    print("🌐 Testing local chatbot endpoint...")
    print(f"   URL: {base_url}/chatbot/api/chat/message")
    print("   Note: Requires authenticated session (login first).")

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{base_url}/chatbot/api/chat/message",
                json={"message": "Hallo, was kann ich hier tun?"},
                headers={"Content-Type": "application/json"},
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   Response: {response.json().get('response', '')[:120]}...")
                print("   ✅ Endpoint reachable.")
            elif response.status_code == 401:
                print("   ⚠️  401 Unauthorized — expected without a session cookie.")
            else:
                print(f"   ❌ Unexpected status: {response.text[:200]}")
    except Exception as e:
        print(f"   ⚠️  Could not reach local server: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("Claude (Anthropic) API Test — VAT Verifizierung")
    print("=" * 60)
    print()
    test_claude_api()
    test_chatbot_endpoint()
