"""
Chatbot routes — powered by Claude (Anthropic).
"""
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
import os
from datetime import datetime
import anthropic
from services.security_helpers import require_same_origin

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
CHATBOT_SYSTEM_PROMPT = """Du bist ein hilfreicher KI-Assistent der VAT Verifizierung Plattform (vat-verifizierung.de).

Die Plattform bietet folgende Module:

1. VIES USt-IdNr. Prüfung — Echtzeit-Validierung von EU-Umsatzsteuer-IDs über die offizielle VIES-Datenbank.
2. Handelsregister — Firmendaten aus deutschem, tschechischem, polnischem und ukrainischem Register (ЄДР).
3. Sanktionslisten — Automatischer Abgleich mit EU, OFAC und UK Sanktionslisten.
4. OSINT Scanner — Domain-Analyse, DNS, SSL, WHOIS, Security Headers, Social Media.
5. Phone Intelligence — Telefonnummern-Analyse mit Spam-Score (0-100), 950+ bekannte Spam-Nummern (USA + Europa), wöchentliche Updates.
6. Link Scanner — URLs auf Phishing und Malware prüfen (VirusTotal + Google Safe Browsing).
7. MailGuard AI — KI-gestützte E-Mail-Verwaltung mit Gmail/Outlook/IMAP-Integration, automatischen Claude-Antworten, VirusTotal-Anhang-Scan.
8. Website Security Scanner — 7 Schwachstellen-Checks (OWASP Top 10), SSL/TLS-Analyse, Security Headers, KI-Empfehlungen.
9. Smart CRM — Geprüfte Kontrahenten verwalten, Notizen, Tags, Prüfungshistorie, Monitoring & Alerts.
10. KI-Assistent — Dieser Chatbot, beantwortet Fragen 24/7.
11. EU Compliance Checker (kostenlos, ohne Registrierung) — Prüft Websites auf Impressum (§5 TMG), Datenschutzerklärung (DSGVO Art.13/14), AGB, Widerrufsbelehrung und Cookie-Banner. Score 0-100 + KI-Zusammenfassung. URL: /compliance-check/
12. KI B2B Marktforschung (kostenlos, ohne Registrierung) — 15 synthetische deutsche B2B-Entscheider (Geschäftsführer, CFO, IT-Leiterin usw.) bewerten ein Produkt: Kaufbereitschaft, Zahlungsbereitschaft, Hauptbedenken, Executive Summary (~60 Sek.). URL: /consumer-panel/
13. TeamGuard — Interne Team-Sicherheit für KMU: Mitarbeiter mit Zugriffslevels verwalten (Owner/Admin/Manager/Mitarbeiter/Gast), sichere Passwörter automatisch generieren und per E-Mail verteilen, Passwort-Rotationsintervall konfigurieren (empfohlen: 90 Tage), Phishing-Simulation für das eigene Team durchführen (klickende Mitarbeiter werden zur Security-Awareness-Seite geleitet), vollständiger Audit-Log aller Sicherheitsereignisse. Keine IT-Abteilung nötig. URL: /teamguard/
14. Enrichment Orchestrator — Automatisches Form-Auto-Fill durch Kombination aus VIES + OSINT + Handelsregistern. API: /api/enrichment/enrich
15. NIS2 Compliance Plattform (Professional Plan) — Vollständige Umsetzung aller 10 Pflichtmaßnahmen nach §30 BSIG (NIS2UmsuCG, seit 6. Dez. 2025 in Deutschland):
    • BSI-Registrierungs-Assistent (§33 BSIG) — Branchencheck, Betroffenheitsprüfung, Registrierungsformular
    • KI-ISMS-Dokumentengenerator — 7 BSI-konforme Dokumente in 10 Minuten (Informationssicherheitsrichtlinie, Risikoanalyse, IRP, BCP, Kryptokonzept, Lieferantenrichtlinie, Zugriffskontrolle)
    • Incident Response & BSI-Meldungen — 24h/72h Fristen-Timer, Meldevorlagen nach §32 BSIG
    • Lieferkettensicherheit (§30 Nr. 4) — Automatischer OSINT-Scan aller Lieferanten, Risikoklassifizierung
    • Kontinuierliches Monitoring (§30 Nr. 5/6) — Wöchentliche Schwachstellenscans von Domains und Infrastruktur
    • Awareness-Schulungen (§30 Nr. 7) — Schulungen erstellen, per E-Mail versenden, digitale Bestätigungen sammeln, Audit-Berichte
    • NIS2 Compliance Dashboard — Ampelstatus für alle 10 Maßnahmen, Lückenanalyse, BSI-Auditbericht
    URL: /nis2/ (nur Professional Plan)

NIS2-Betroffenheit: ~30.000 deutsche Unternehmen in 18 Sektoren mit 50+ Mitarbeitern oder >10 Mio. € Umsatz.
Bußgeld bei Verstoß: bis €10 Mio. oder 2 % des globalen Jahresumsatzes (§60 BSIG).

Abo-Pläne:
- Free: 0€, 1 Prüfung/Monat
- Basic: €9,99/Monat, 100 Prüfungen, OSINT, Link Scanner, CRM
- Professional: €49,90/Monat, 500 Prüfungen, alle Basic-Features + Handelsregister, MailGuard AI (3 Konten), TeamGuard (bis 20 Mitarbeiter), Phishing-Simulation, API-Zugang, NIS2 Compliance Plattform (§30 BSIG)

Alle bezahlten Pläne: 3 Tage kostenlos testen, keine Kreditkarte nötig.
EU Compliance Checker und KI B2B Marktforschung: komplett kostenlos, ohne Registrierung.
NIS2 Compliance Plattform: nur im Professional-Plan, URL: /nis2/

Antworte auf Deutsch, präzise und freundlich. Wenn du dir bei etwas unsicher bist, sage es ehrlich.
"""


@chatbot_bp.route("/chat", methods=["GET"])
def chat_page():
    return render_template("chatbot/chat.html", now=datetime.now())


@chatbot_bp.route("/api/chat/message", methods=["POST"])
@login_required
@require_same_origin
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
