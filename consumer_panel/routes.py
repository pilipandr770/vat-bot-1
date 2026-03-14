"""
AI B2B Consumer Panel — synthetic market research with 15 diverse business personas.
Accessible without registration. Uses Claude AI to simulate B2B buyer feedback.
"""
from __future__ import annotations
import json, re, statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Blueprint, render_template, request, jsonify, current_app
import anthropic

consumer_panel_bp = Blueprint('consumer_panel', __name__, url_prefix='/consumer-panel')

CLAUDE_MODEL = "claude-sonnet-4-6"

B2B_PERSONAS = [
    {"name": "Klaus M.", "role": "Geschäftsführer KMU", "company_size": "10–50 MA", "age": 52, "region": "Bayern",
     "traits": "preisbewusst, konservativ, sucht Verlässlichkeit und einfache Bedienung"},
    {"name": "Sarah K.", "role": "IT-Leiterin", "company_size": "100–500 MA", "age": 38, "region": "NRW",
     "traits": "tech-affin, prozessorientiert, schätzt Automatisierung und API-Integration"},
    {"name": "Mohamed A.", "role": "CFO", "company_size": "50–100 MA", "age": 45, "region": "Hessen",
     "traits": "zahlengetrieben, sehr risikobewusst, compliance-fokussiert, ROI-orientiert"},
    {"name": "Petra W.", "role": "Buchhalterin", "company_size": "5–10 MA", "age": 48, "region": "Sachsen",
     "traits": "praktisch, zeiteffizient, skeptisch bei neuen Tools, wenig tech-affin"},
    {"name": "Jan B.", "role": "Startup-Gründer", "company_size": "1–5 MA", "age": 31, "region": "Berlin",
     "traits": "innovationsfreudig, sehr budgetbewusst, data-driven, agil"},
    {"name": "Anna S.", "role": "Compliance-Officer", "company_size": "500+ MA", "age": 41, "region": "Hamburg",
     "traits": "rechtlich sehr genau, dokumentationsorientiert, stark risikoavers"},
    {"name": "Mehmet Y.", "role": "Einkaufsleiter", "company_size": "100–200 MA", "age": 44, "region": "BW",
     "traits": "verhandlungsstark, lieferkettenfokussiert, international aufgestellt"},
    {"name": "Lisa H.", "role": "Steuerberaterin", "company_size": "Kanzlei 15 MA", "age": 37, "region": "München",
     "traits": "hochpräzise, mandantenorientiert, DSGVO-bewusst, zeitkritisch"},
    {"name": "Thomas R.", "role": "Vertriebsleiter", "company_size": "200–500 MA", "age": 49, "region": "NRW",
     "traits": "ergebnisorientiert, trifft schnelle Entscheidungen, kundenorientiert"},
    {"name": "Elena Z.", "role": "Operations Manager", "company_size": "50–100 MA", "age": 33, "region": "Berlin",
     "traits": "prozessoptimierend, international, SaaS-erfahren, effizienzfokussiert"},
    {"name": "Rainer S.", "role": "Unternehmensberater", "company_size": "Selbständig", "age": 55, "region": "Frankfurt",
     "traits": "strategisch, sehr erfahren, verschiedene Branchen, hohe Ansprüche"},
    {"name": "Yuna P.", "role": "HR-Direktorin", "company_size": "300+ MA", "age": 39, "region": "Hamburg",
     "traits": "mitarbeiterorientiert, datenschutzbewusst, ESG-fokussiert"},
    {"name": "Bernd T.", "role": "Handwerksmeister", "company_size": "5–10 MA", "age": 57, "region": "Bayern",
     "traits": "sehr pragmatisch, zeitsparend, wenig tech-affin, kostenbewusst"},
    {"name": "Chiara M.", "role": "E-Commerce Managerin", "company_size": "20–50 MA", "age": 29, "region": "Berlin",
     "traits": "digital-nativ, conversion-fokussiert, DSGVO-erfahren, wachstumsorientiert"},
    {"name": "Frank G.", "role": "Produktionsleiter", "company_size": "50–100 MA", "age": 46, "region": "Sachsen",
     "traits": "kosteneffizienz, Zuverlässigkeit, pragmatisch, wenig Zeit für Tests"},
]

QUESTIONS = [
    {
        "id": "interest",
        "text": "Wie relevant ist dieses Produkt/Tool für dein Unternehmen? (1=kaum relevant, 10=sehr relevant)",
        "type": "scale",
    },
    {
        "id": "price_willingness",
        "text": "Was wärst du bereit, pro Monat für dieses Tool zu zahlen? (Betrag in EUR, z.B. 29.99)",
        "type": "price",
    },
    {
        "id": "would_buy",
        "text": "Würdest du dieses Tool kaufen oder testen?",
        "type": "choice",
        "options": ["Ja, sofort kaufen", "Ja, nach kostenlosem Test", "Vielleicht, muss überzeugen", "Nein"],
    },
    {
        "id": "main_concern",
        "text": "Was ist dein größtes Bedenken oder Hindernis bei der Einführung dieses Tools?",
        "type": "open",
    },
    {
        "id": "key_benefit",
        "text": "Welchen konkreten Nutzen oder Vorteil siehst du für dein Unternehmen?",
        "type": "open",
    },
]


def _ask_persona(persona: dict, product_description: str, api_key: str) -> dict:
    q_lines = []
    for q in QUESTIONS:
        if q["type"] == "choice":
            opts = " / ".join(q["options"])
            q_lines.append(f'  "{q["id"]}": {q["text"]} Optionen: {opts}')
        elif q["type"] == "scale":
            q_lines.append(f'  "{q["id"]}": {q["text"]} (Nur eine Zahl von 1-10)')
        elif q["type"] == "price":
            q_lines.append(f'  "{q["id"]}": {q["text"]} (Nur eine Dezimalzahl in EUR)')
        else:
            q_lines.append(f'  "{q["id"]}": {q["text"]} (1-2 Sätze)')

    json_keys = "\n".join(f'  "{q["id"]}": <wert>' for q in QUESTIONS)

    prompt = (
        f"Du bist: {persona['name']}\n"
        f"Position: {persona['role']}\n"
        f"Unternehmensgröße: {persona['company_size']}\n"
        f"Region: {persona['region']}\n"
        f"Persönlichkeit: {persona['traits']}\n\n"
        f"Produkt/Tool das bewertet werden soll:\n{product_description[:1200]}\n\n"
        f"Beantworte diesen Fragebogen authentisch aus deiner Perspektive:\n"
        + "\n".join(q_lines)
        + f"\n\nAntworte AUSSCHLIESSLICH mit diesem JSON:\n{{\n{json_keys}\n}}"
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=450,
            system=(
                "Du bist eine reale Geschäftsperson. Antworte authentisch, manchmal kritisch und "
                "realistisch aus deiner konkreten beruflichen Perspektive. Sei nicht übermäßig positiv. "
                "Antworte AUSSCHLIESSLICH mit einem validen JSON-Objekt."
            ),
            messages=[{"role": "user", "content": prompt}],
        )
        m = re.search(r"\{.*\}", resp.content[0].text, re.DOTALL)
        if m:
            raw = json.loads(m.group())
            result: dict = {}
            for q in QUESTIONS:
                val = raw.get(q["id"])
                if val is None:
                    continue
                if q["type"] in ("scale", "price"):
                    try:
                        result[q["id"]] = float(str(val).replace(",", ".").replace("€", "").strip())
                    except (ValueError, AttributeError):
                        pass
                else:
                    result[q["id"]] = str(val)
            return {"persona": persona, "answers": result}
    except Exception as e:
        pass
    return {"persona": persona, "answers": {}}


def _executive_summary(product_desc: str, insights: dict, n: int, api_key: str) -> str:
    parts = [f"Panel: {n} B2B-Entscheider aus verschiedenen Branchen und Unternehmensgrößen."]
    if "interest" in insights:
        parts.append(f"Ø Relevanz: {insights['interest']['avg']:.1f}/10.")
    if "price_willingness" in insights and insights["price_willingness"].get("avg"):
        parts.append(f"Ø Zahlungsbereitschaft: {insights['price_willingness']['avg']:.2f} EUR/Monat.")
    if "would_buy" in insights:
        counts = insights["would_buy"]["counts"]
        yes = counts.get("Ja, sofort kaufen", 0) + counts.get("Ja, nach kostenlosem Test", 0)
        parts.append(f"Kaufbereitschaft: {yes}/{n} ({100 * yes // n if n else 0}%).")

    concerns = insights.get("main_concern", {}).get("quotes", [])[:5]
    benefits = insights.get("key_benefit", {}).get("quotes", [])[:5]

    prompt = (
        f"Produkt: {product_desc[:400]}\n\nPanel-Ergebnisse: {' '.join(parts)}\n\n"
        f"Hauptbedenken der Entscheider: {' | '.join(concerns)}\n\n"
        f"Genannte Hauptvorteile: {' | '.join(benefits)}\n\n"
        "Schreibe einen Executive Summary (5–7 Sätze) auf Deutsch für das Management. "
        "Fokus: Kaufbereitschaft, wichtigste Bedenken, Zahlungsbereitschaft nach Unternehmensgrößen, "
        "konkrete Handlungsempfehlung für Produktstrategie oder Pricing."
    )
    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()
    except Exception:
        return " ".join(parts)


@consumer_panel_bp.route('/', methods=['GET'])
def index():
    return render_template('consumer_panel/index.html')


@consumer_panel_bp.route('/run', methods=['POST'])
def run_panel():
    """Run AI consumer panel. Returns JSON. No login required."""
    data = request.get_json() or {}
    product_name = data.get('product_name', '').strip()
    product_desc = data.get('product_description', '').strip()

    if not product_name or not product_desc:
        return jsonify({'error': 'Produktname und Beschreibung sind erforderlich'}), 400

    api_key = current_app.config.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return jsonify({'error': 'KI-Analyse nicht verfügbar (API-Key fehlt)'}), 500

    full_desc = f"Produktname: {product_name}\n\nBeschreibung: {product_desc}"

    # Run all personas in parallel (max 5 threads to respect rate limits)
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_ask_persona, p, full_desc, api_key): p for p in B2B_PERSONAS}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception:
                pass

    # Aggregate results
    insights: dict = {}

    interest_vals = [r["answers"]["interest"] for r in results
                     if isinstance(r["answers"].get("interest"), (int, float))]
    if interest_vals:
        insights["interest"] = {
            "avg": round(statistics.mean(interest_vals), 2),
            "distribution": {str(k): sum(1 for v in interest_vals if int(round(v)) == k)
                             for k in range(1, 11) if any(int(round(v)) == k for v in interest_vals)},
        }

    price_vals = [r["answers"]["price_willingness"] for r in results
                  if isinstance(r["answers"].get("price_willingness"), (int, float))
                  and 0 < r["answers"]["price_willingness"] < 100_000]
    if price_vals:
        sv = sorted(price_vals)
        n = len(sv)
        insights["price_willingness"] = {
            "avg": round(statistics.mean(price_vals), 2),
            "p25": round(sv[n // 4], 2),
            "p50": round(sv[n // 2], 2),
            "p75": round(sv[3 * n // 4], 2),
            "values": price_vals,
        }

    buy_vals = [r["answers"]["would_buy"] for r in results if r["answers"].get("would_buy")]
    if buy_vals:
        counts: dict[str, int] = {}
        for v in buy_vals:
            counts[str(v)] = counts.get(str(v), 0) + 1
        insights["would_buy"] = {"counts": counts}

    concerns = [r["answers"]["main_concern"] for r in results if r["answers"].get("main_concern")]
    insights["main_concern"] = {"quotes": concerns}

    benefits = [r["answers"]["key_benefit"] for r in results if r["answers"].get("key_benefit")]
    insights["key_benefit"] = {"quotes": benefits}

    # Executive summary
    summary = _executive_summary(full_desc, insights, len(results), api_key)

    # Table rows
    persona_rows = [{
        "name": r["persona"]["name"],
        "role": r["persona"]["role"],
        "company_size": r["persona"]["company_size"],
        "interest": r["answers"].get("interest"),
        "price": r["answers"].get("price_willingness"),
        "would_buy": r["answers"].get("would_buy"),
    } for r in results]

    return jsonify({
        "personas_count": len(results),
        "insights": insights,
        "executive_summary": summary,
        "persona_rows": persona_rows,
    })
