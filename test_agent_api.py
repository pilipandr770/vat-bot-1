"""
Test script for OpenAI Agent Builder API
Usage: python test_agent_api.py
"""
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

AGENT_API_URL = os.getenv("OPENAI_AGENT_API_URL", "https://api.openai.com/v1/agents/run")
AGENT_API_KEY = os.getenv("OPENAI_AGENT_API_KEY", "")

def test_agent_api():
    """Test connection to Agent Builder"""
    
    if not AGENT_API_KEY:
        print("❌ ERROR: OPENAI_AGENT_API_KEY not set in .env file")
        return
    
    print(f"🔗 Testing Agent API: {AGENT_API_URL}")
    print(f"🔑 API Key: {AGENT_API_KEY[:20]}...")
    print()
    
    test_message = "Wie starte ich eine Prüfung?"
    
    try:
        print(f"📤 Sending message: {test_message}")
        
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                AGENT_API_URL,
                json={
                    "input_as_text": test_message,
                    "context": {
                        "user_email": "test@example.com",
                        "user_name": "Test User",
                        "subscription_plan": "free",
                        "is_admin": False
                    }
                },
                headers={
                    "Authorization": f"Bearer {AGENT_API_KEY}",
                    "Content-Type": "application/json"
                }
            )
            
            print(f"📥 Response Status: {response.status_code}")
            print(f"📥 Response Headers: {dict(response.headers)}")
            print()
            print(f"📄 Response Body:")
            print(response.text)
            print()
            
            if response.status_code == 200:
                print("✅ SUCCESS! Agent API is working")
                try:
                    data = response.json()
                    print(f"📝 Agent Response: {data}")
                except Exception as e:
                    print(f"⚠️ Warning: Could not parse JSON: {e}")
            else:
                print(f"❌ ERROR: Got status code {response.status_code}")
                
    except httpx.TimeoutException:
        print("❌ ERROR: Request timeout (60s)")
    except httpx.ConnectError as e:
        print(f"❌ ERROR: Connection failed: {e}")
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 60)
    print("OpenAI Agent Builder API Test")
    print("=" * 60)
    print()
    test_agent_api()
