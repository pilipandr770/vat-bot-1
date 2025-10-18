# 🤖 AI Chatbot Deployment Guide

## ✅ What's Deployed
Your OpenAI Agent Builder chatbot is now integrated into the platform with:
- **Backend**: Async API endpoint at `/chatbot/api/chat/message`
- **Frontend**: Modern card-based chat UI at `/chatbot/chat`
- **Navigation**: "AI Assistent" link in navbar (robot icon)
- **User Context**: Automatically injects user email, name, subscription, admin status
- **Error Handling**: 60s timeout, network error recovery, proper JSON validation

## 🔧 Render Dashboard Configuration

### Required Environment Variables
Log into Render Dashboard → Your Service → Environment → Add:

```
OPENAI_AGENT_API_KEY=sk-proj-YOUR_API_KEY_HERE
OPENAI_AGENT_API_URL=https://api.openai.com/v1/agents/run
```

**Important Notes:**
- Get your API key from: https://platform.openai.com/api-keys
- If using Agent Builder workflows, the URL might be different (check OpenAI docs)
- For your workflow ID `wf_68f3ed065d5881909c95b20ad801090b07e400bf50570e4d`, verify the correct endpoint format

### Steps to Configure on Render

1. **Open Render Dashboard**:
   - Go to https://dashboard.render.com
   - Select your `vat-bot-1` service

2. **Add Environment Variables**:
   - Click "Environment" tab
   - Click "Add Environment Variable"
   - Add `OPENAI_AGENT_API_KEY`: Your OpenAI API key
   - Add `OPENAI_AGENT_API_URL`: Agent Builder endpoint
   - Click "Save Changes"

3. **Deploy**:
   - Render will automatically redeploy after saving env vars
   - Monitor logs: "Logs" tab → Check for errors
   - Wait for "Build successful" and "Service is live"

4. **Test the Chatbot**:
   - Navigate to: `https://vat-bot-1.onrender.com/chatbot/chat`
   - Try sending: "Wie starte ich eine Prüfung?"
   - Should get German response from your agent

## 🧪 Testing Checklist

### Local Testing (Optional)
Before deploying, test locally:

1. **Create `.env` file** in project root:
```
OPENAI_AGENT_API_KEY=sk-proj-YOUR_KEY
OPENAI_AGENT_API_URL=https://api.openai.com/v1/agents/run
```

2. **Run Flask**:
```powershell
python app.py
```

3. **Open browser**:
```
http://localhost:5000/chatbot/chat
```

4. **Send test messages**:
- "Wie starte ich eine Prüfung?"
- "Was macht der OSINT-Scanner?"
- "Wie ändere ich mein Abo?"

### Production Testing
Once deployed on Render:

1. **Access chatbot**: https://vat-bot-1.onrender.com/chatbot/chat
2. **Test German questions**:
   - ✅ VAT verification process
   - ✅ OSINT scanner features
   - ✅ Subscription management
   - ✅ Status meanings
3. **Verify user context**: Agent should know your email/name if logged in
4. **Check error handling**: Try with invalid input, check graceful errors

## 💰 Cost Monitoring

Your chatbot uses OpenAI API with estimated costs:
- **Per message**: ~$0.01 - $0.03
- **100 messages/day**: ~$1 - $3/day
- **Monthly estimate**: ~$30 - $90

**Monitor usage**:
- OpenAI Dashboard: https://platform.openai.com/usage
- Set up billing alerts in OpenAI settings
- Review costs weekly during initial rollout

## 🔒 Security Best Practices

✅ **Already Implemented**:
- API keys stored in environment variables (not in code)
- 60-second timeout prevents long-running requests
- Error messages don't expose sensitive data
- AJAX requests use Content-Type validation

🔄 **Additional Recommendations**:
- **Rate Limiting**: Add rate limits per user (e.g., 10 messages/minute)
- **Logging**: Monitor API calls and errors in Render logs
- **API Key Rotation**: Rotate keys quarterly
- **User Authentication**: Ensure only logged-in users access chatbot

## 🐛 Troubleshooting

### Common Issues

**1. "Failed to send message" error**
- Check Render logs: `Logs` tab
- Verify `OPENAI_AGENT_API_KEY` is set correctly
- Test API key in OpenAI Playground

**2. Timeout errors**
- Agent responses taking > 60s
- Optimize agent instructions in OpenAI Agent Builder
- Consider increasing timeout in `chatbot_routes.py` (line 31)

**3. Agent gives wrong information**
- Update system instructions in OpenAI Agent Builder
- Your current instructions cover: Dashboard, OSINT, verification, pricing, legal pages
- Add more context to agent prompts if needed

**4. User context not working**
- Check if user is logged in (`current_user` Flask-Login)
- Verify session data in browser dev tools
- Review `chatbot_routes.py` line 38-42 (context injection)

### Debug Steps

1. **Check Render Logs**:
```
Render Dashboard → Logs → Filter by "chatbot"
```

2. **Test API Key Separately**:
```python
import httpx
import asyncio

async def test_api():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/agents/run",
            headers={"Authorization": "Bearer YOUR_KEY"},
            json={"message": "Test"}
        )
        print(response.status_code, response.text)

asyncio.run(test_api())
```

3. **Browser DevTools**:
- Open chatbot page
- F12 → Network tab
- Send message
- Check `/api/chat/message` request/response

## 📊 Monitoring Dashboard

Create a simple monitoring setup:

1. **OpenAI Dashboard**: Track API usage and costs
2. **Render Logs**: Monitor errors and performance
3. **User Feedback**: Add feedback buttons in chat UI (future enhancement)

## 🚀 Next Steps

### Immediate (Required)
- [ ] Add environment variables on Render
- [ ] Test chatbot on production
- [ ] Monitor costs for first week

### Future Enhancements
- [ ] Add rate limiting per user
- [ ] Implement chat history persistence
- [ ] Add feedback buttons (thumbs up/down)
- [ ] Analytics dashboard for chatbot usage
- [ ] Multi-language support (English, Ukrainian)
- [ ] Voice input/output integration

## 📞 Support

If you encounter issues:
1. Check Render logs first
2. Verify OpenAI API key is active
3. Test locally with `.env` file
4. Review error messages in browser console

---

**Your chatbot is ready to deploy! 🎉**

Just add the API keys on Render and start chatting in German about VAT verification!
