# Email Scan API Documentation

## Endpoint: `/file-scanner/api/email-scan`

**Method:** `POST`

**Content-Type:** `application/json`

**Authentication:** Bearer token via `Authorization` header or `X-Scanner-Token` header

---

## Request Format

```json
{
  "source": "mailguard",
  "content": {
    "text": "Email body plain text",
    "html": "<html>Email HTML content</html>",
    "subject": "Email subject line",
    "links": [
      "https://example.com",
      "http://suspicious-link.com"
    ]
  },
  "attachments": [
    {
      "filename": "document.pdf",
      "content_type": "application/pdf",
      "temp_path": "/tmp/tmpfile123",
      "size": 102400
    }
  ]
}
```

## Response Format

### Success Response

```json
{
  "success": true,
  "verdict": "safe",  // "safe" | "suspicious" | "malicious"
  "score": 25,        // 0-100 (0=safe, 100=dangerous)
  "details": {
    "text_analysis": {
      "suspicious_keywords": ["bitcoin", "überweisen"]
    },
    "link_analysis": {
      "http_links": ["http://example.com"],
      "shortened_links": ["https://bit.ly/abc123"]
    },
    "attachment_analysis": [
      {
        "filename": "document.pdf",
        "size": 102400,
        "extension": "pdf",
        "risk": "safe",
        "virustotal": {
          "malicious": 0,
          "total": 71,
          "hash": "abc123...",
          "link": "https://www.virustotal.com/gui/file/abc123"
        }
      }
    ]
  },
  "source": "file_scanner_email_api"
}
```

### Error Response

```json
{
  "success": false,
  "error": "Error message",
  "verdict": "unknown",
  "score": 0
}
```

---

## Verdict Logic

| Score Range | Verdict      | Description                          |
|-------------|--------------|--------------------------------------|
| 0-39        | `safe`       | No significant threats detected      |
| 40-69       | `suspicious` | Some warning signs found             |
| 70-100      | `malicious`  | High risk - dangerous content found  |

---

## Score Calculation

### Text Analysis
- **Suspicious keyword detected:** +10 points per keyword
- **3+ keywords:** Auto-upgrade to `suspicious`

**Keywords:**
- überweisen, zahlung dringend, bitcoin, passwort zurücksetzen
- invoice attached, payment required, account suspended
- verify your account, click here immediately, urgent action required
- cryptocurrency, wallet address

### Link Analysis
- **HTTP link (not HTTPS):** +15 points per link
- **3+ HTTP links:** Auto-upgrade to `suspicious`
- **Shortened URL (bit.ly, tinyurl.com, goo.gl):** +10 points per link

### Attachment Analysis
- **Dangerous extension (exe, dll, bat, cmd, vbs, js, jar, scr, pif, com):**
  - +50 points
  - Auto-upgrade to `malicious`
  
- **Archive file (zip, rar, 7z, gz, tar, iso):**
  - +20 points
  - Auto-upgrade to `suspicious` if verdict was `safe`

- **VirusTotal detection:**
  - +5 points per engine detecting malware
  - Any malware detected → Auto-upgrade to `malicious`

---

## Configuration (Environment Variables)

```bash
# File Scanner URL (Render deployment)
FILE_SCANNER_URL=https://vat-bot-1.onrender.com/file-scanner/api/email-scan

# Enable/disable external scanner
FILE_SCANNER_ENABLED=true

# Request timeout (seconds)
FILE_SCANNER_TIMEOUT=30

# Bearer token for authentication
FILE_SCANNER_TOKEN=your-secure-token-here

# VirusTotal API key for attachment scanning
VIRUSTOTAL_API_KEY=your-virustotal-api-key
```

---

## Usage Example (Python)

```python
import requests

url = "https://vat-bot-1.onrender.com/file-scanner/api/email-scan"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer your-token-here"
}

payload = {
    "source": "mailguard",
    "content": {
        "text": "Please transfer money urgently to bitcoin wallet",
        "subject": "URGENT: Payment Required",
        "links": ["http://suspicious-site.com"]
    },
    "attachments": []
}

response = requests.post(url, json=payload, headers=headers, timeout=30)
result = response.json()

print(f"Verdict: {result['verdict']}")
print(f"Score: {result['score']}/100")
```

---

## Integration with MailGuard

The `scanner_client.py` module automatically calls this endpoint when:
1. New email arrives (in `tasks.py` → `create_draft_reply()`)
2. `FILE_SCANNER_URL` is configured
3. `FILE_SCANNER_ENABLED=true`

**Fallback:** If external scanner fails, uses local heuristic scanning (`local_message_scan()`).

---

## Security Notes

- **No file execution:** All analysis is read-only
- **Temporary files:** Attachments stored in system temp directory, deleted after scan
- **VirusTotal privacy:** File hashes checked first (no upload if already known)
- **Token authentication:** Required for production to prevent abuse
- **Rate limiting:** Configured in `file_scanner/routes.py` (MAX_CONCURRENT_SCANS)

---

## Deployment on Render

**Environment Variables to Set:**
```
FILE_SCANNER_URL=https://vat-bot-1.onrender.com/file-scanner/api/email-scan
FILE_SCANNER_ENABLED=true
FILE_SCANNER_TOKEN=<generate-secure-random-token>
VIRUSTOTAL_API_KEY=7977663b17d01aade4620f45d557de21525b7a67e91e21986ac2fb5f85574e66
```

**Generate secure token:**
```python
import secrets
print(secrets.token_urlsafe(32))
```

---

Last Updated: November 11, 2025
