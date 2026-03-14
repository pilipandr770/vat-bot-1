# MailGuard Email Security Architecture

## 🏗️ Архитектура системы безопасности

```
┌─────────────────────────────────────────────────────────────────┐
│                      MailGuard Email System                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               IMAP Connector (connectors/imap.py)               │
│  Fetches emails from: Gmail, Outlook, Yahoo, Mail.ru, Yandex   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Email Processor (mailguard/tasks.py)               │
│  - Parses email (text, HTML, attachments, links)               │
│  - Extracts thread context (in_reply_to, references)           │
│  - Calls scanner_client.scan_message()                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│         Scanner Client (mailguard/scanner_client.py)            │
│  Primary: External API → /file-scanner/api/email-scan          │
│  Fallback: Local heuristic scan (keywords + links)             │
└─────────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┴─────────────┐
                ▼                           ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│   External Scanner API    │   │   Local Fallback Scan     │
│ /file-scanner/api/email-  │   │  (scanner_client.py)      │
│        scan endpoint      │   │                           │
│  (file_scanner/routes.py) │   │  - Keyword detection      │
│                           │   │  - Link analysis          │
│  1. Text Analysis         │   │  - Extension check        │
│  2. Link Analysis         │   │  - Risk scoring           │
│  3. Attachment Scan       │   │                           │
│  4. VirusTotal API        │   │  Returns: verdict + score │
└───────────────────────────┘   └───────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────┐
│              VirusTotal API v3                                │
│  - Hash lookup (fast, no upload)                             │
│  - File upload (if hash not found)                           │
│  - 70+ antivirus engines                                     │
│  - Returns: malicious_count / total_engines                  │
└───────────────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────┐
│              Scan Result Processing                           │
│  - verdict: safe / suspicious / malicious                    │
│  - score: 0-100 (risk level)                                 │
│  - Store in ScanReport model (optional)                      │
│  - Generate AI reply with security context                   │
└───────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow Example

### Scenario: User receives email with PDF attachment

```
1. IMAP Fetch
   📧 Email arrives → IMAP connector fetches
   
2. Email Parsing
   ┌─ Subject: "Invoice for October 2025"
   ├─ Body: "Please find attached invoice..."
   ├─ Attachments: [invoice.pdf (150 KB)]
   └─ Links: ["https://example.com/payment"]

3. Security Scan Request
   POST /file-scanner/api/email-scan
   {
     "content": {
       "subject": "Invoice for October 2025",
       "text": "Please find attached...",
       "links": ["https://example.com/payment"]
     },
     "attachments": [{
       "filename": "invoice.pdf",
       "temp_path": "/tmp/tmpXYZ123",
       "size": 153600
     }]
   }

4. Scanner Processing
   ├─ Text Analysis:
   │  └─ Keywords: ✅ No suspicious keywords
   │
   ├─ Link Analysis:
   │  └─ HTTPS link: ✅ Safe
   │
   └─ Attachment Analysis:
      ├─ Extension: .pdf ✅ Safe
      ├─ SHA256 Hash: abc123...def456
      └─ VirusTotal Lookup:
         GET /api/v3/files/abc123...def456
         Response: 0 malicious / 71 total ✅

5. Scan Result
   {
     "verdict": "safe",
     "score": 5,
     "details": {
       "attachment_analysis": [{
         "filename": "invoice.pdf",
         "risk": "safe",
         "virustotal": {
           "malicious": 0,
           "total": 71
         }
       }]
     }
   }

6. AI Reply Generation
   ✅ Email marked as safe
   → Generate contextual AI reply
   → Store draft in MailDraft table
```

---

## 📊 Risk Scoring Matrix

| Component           | Detection                         | Score Impact | Verdict Upgrade    |
|---------------------|-----------------------------------|--------------|-------------------|
| **Text Analysis**   | Suspicious keyword                | +10 per kw   | 3+ → suspicious   |
| **Link Analysis**   | HTTP (not HTTPS)                  | +15 per link | 3+ → suspicious   |
|                     | Shortened URL                     | +10 per link | -                 |
| **Attachment**      | Dangerous extension (exe, dll)    | +50          | → malicious       |
|                     | Archive file (zip, rar)           | +20          | → suspicious      |
|                     | VirusTotal malware detected       | +5 per engine| → malicious       |

**Final Verdict Logic:**
- Score 0-39: ✅ **safe**
- Score 40-69: ⚠️ **suspicious**
- Score 70-100: 🚨 **malicious**

---

## 🔑 Configuration on Render

### Required Environment Variables

```bash
# File Scanner Endpoint (production URL)
FILE_SCANNER_URL=https://vat-bot-1.onrender.com/file-scanner/api/email-scan

# Enable scanner
FILE_SCANNER_ENABLED=true

# Authentication token (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
FILE_SCANNER_TOKEN=<your-secure-token>

# VirusTotal API Key (free tier: 500 requests/day)
VIRUSTOTAL_API_KEY=7977663b17d01aade4620f45d557de21525b7a67e91e21986ac2fb5f85574e66

# OpenAI for AI replies
OPENAI_API_KEY=<your-openai-key>

# Email encryption key (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
MAILGUARD_ENCRYPTION_KEY=<your-fernet-key>
```

---

## 🛡️ Security Features

### 1. **No File Execution**
- All scanning is **read-only**
- Files analyzed in temporary directory
- Automatic cleanup after scan

### 2. **Privacy-First VirusTotal**
- **Hash lookup first** (no file upload if already known)
- Only uploads new/unknown files
- Files <32MB supported

### 3. **Token Authentication**
- Bearer token required for API access
- Prevents unauthorized scanning
- Separate from user authentication

### 4. **Fallback Protection**
- If external API fails → local heuristic scan
- Always returns verdict (never fails silently)
- Logs warnings for debugging

### 5. **Thread Context**
- Uses email threading (in_reply_to, references)
- Loads conversation history for AI context
- Links to CRM counterparty data

---

## 🧪 Testing Checklist

### Local Testing
- [ ] Start Flask dev server: `flask run --debug`
- [ ] Test endpoint: `http://localhost:5000/file-scanner/api/email-scan`
- [ ] Verify VirusTotal API key works
- [ ] Check fallback when API disabled

### Render Testing (After Deployment)
- [ ] Verify environment variables set
- [ ] Test production endpoint: `https://vat-bot-1.onrender.com/file-scanner/api/email-scan`
- [ ] Send test email with attachment
- [ ] Check logs for VirusTotal API calls
- [ ] Verify ScanReport stored in database

### Integration Testing
- [ ] MailGuard fetches email via IMAP
- [ ] Email automatically scanned
- [ ] AI reply includes security context
- [ ] Thread history loaded correctly

---

## 📚 API Documentation

See [`EMAIL_SCAN_API.md`](./EMAIL_SCAN_API.md) for:
- Complete API reference
- Request/response formats
- Python code examples
- Deployment guide

---

**Last Updated:** November 11, 2025  
**Status:** ✅ Production-ready on Render  
**Next Steps:** Test with real email data, implement APScheduler auto-sync
