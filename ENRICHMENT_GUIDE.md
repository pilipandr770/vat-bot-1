# Enrichment Orchestrator - Автоматичне збагачення даних контрагентів

## Огляд
**EnrichmentOrchestrator** - це єдина точка входу для автоматичного заповнення даних контрагента, яка комбінує 3 безкоштовних джерела:

1. **VIES** (EU VAT Information Exchange System) - валідація VAT номерів
2. **Business Registries** - державні реєстри компаній (DE/CZ/PL)
3. **OSINT Scanner** - відкриті дані з інтернету (WHOIS, DNS, SSL, HTTP headers)

## Архітектура

### Основні компоненти

```
Frontend (static/js/app.js)
    ↓ VAT number input → blur event
    ↓ POST /api/vat-lookup
Backend (application.py)
    ↓ @app.route('/api/vat-lookup')
    ↓ EnrichmentOrchestrator.enrich()
Services:
    ├── VatLookupService → VIES API
    ├── BusinessRegistryManager → DE/CZ/PL registries
    └── OsintScanner → WHOIS/DNS/SSL/Headers
    ↓ Aggregate results
Frontend
    ↓ Auto-fill form fields with highlighted animation
```

### Файлова структура

```
services/
├── enrichment_flow.py        # EnrichmentOrchestrator (головний клас)
├── vat_lookup.py              # VIES integration
├── business_registry.py       # Business registries manager
└── osint/
    └── scanner.py             # OSINT aggregator

routes/
└── enrichment.py              # Dedicated enrichment API blueprint

application.py                 # Main app with /api/vat-lookup endpoint

static/js/
└── app.js                     # Frontend VAT input handler
```

## Використання

### Backend API

#### Endpoint: `/api/vat-lookup` (POST)
**Призначення:** Автозаповнення форми верифікації контрагента

**Request:**
```json
{
  "vat_number": "DE123456789",     // Optional
  "email": "info@company.de",      // Optional
  "domain": "company.de",          // Optional
  "company_name": "Company GmbH",  // Optional
  "country_code": "DE"             // Optional (hint)
}
```

**Response (Success):**
```json
{
  "success": true,
  "prefill": {
    "company_name": "Company GmbH",
    "company_address": "Hauptstr. 1, 10115 Berlin",
    "company_country": "DE",
    "counterparty_name": "Company GmbH",
    "counterparty_address": "Hauptstr. 1",
    "counterparty_city": "Berlin",
    "counterparty_postal_code": "10115",
    "counterparty_country": "DE",
    "counterparty_website": "https://company.de",
    "counterparty_email": "info@company.de",
    "counterparty_phone": "+49 30 12345678"
  },
  "services": {
    "vat_lookup": {
      "success": true,
      "data": {
        "valid": true,
        "name": "Company GmbH",
        "address": "Hauptstr. 1, 10115 Berlin"
      }
    },
    "osint": [
      {
        "service": "whois",
        "status": "success",
        "data": {
          "org": "Company GmbH",
          "country": "DE",
          "city": "Berlin"
        }
      },
      {
        "service": "dns",
        "status": "success",
        "data": {
          "A": ["1.2.3.4"],
          "MX": ["mail.company.de"]
        }
      }
    ],
    "registry_de": {
      "status": "success",
      "data": {
        "company_name": "Company GmbH",
        "address": "Hauptstr. 1, 10115 Berlin"
      }
    }
  },
  "messages": [
    "VIES validation successful",
    "OSINT-аналіз для company.de виконано (Whois/DNS/SSL/Headers)",
    "Знайдено запис у державному реєстрі (DE)"
  ]
}
```

### Frontend Integration

**1. VAT Input Handler (static/js/app.js)**

```javascript
async handleVatPrefill(event) {
    const vatRaw = event.target.value.trim().toUpperCase();
    if (!vatRaw || vatRaw.length < 4) return;

    const payload = { vat_number: vatRaw };
    const countrySelect = document.getElementById('counterparty_country');
    if (countrySelect?.value) {
        payload.country_code = countrySelect.value;
    }

    this.showVatPrefillMessages('search');

    try {
        const response = await fetch('/api/vat-lookup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok && data.success) {
            this.applyPrefill(data.prefill || {});
            this.showVatPrefillMessages(data);
        }
    } catch (error) {
        this.showVatPrefillMessages({
            messages: [{ 
                level: 'danger', 
                text: error.message || 'Unbekannter Fehler' 
            }]
        }, true);
    }
}
```

**2. Auto-fill with Highlight Animation**

```javascript
setFieldValue(field, value) {
    if (!field || value === undefined || value === null) return;
    if (field.dataset.userEdited === 'true' && field.value) return;
    
    field.value = value;
    field.dataset.autofilled = 'true';
    field.classList.add('autofill-highlight');
    setTimeout(() => field.classList.remove('autofill-highlight'), 3500);
}
```

**CSS для підсвічування:**
```css
.autofill-highlight {
    background-color: #fff3cd !important;
    transition: background-color 0.5s ease;
}
```

## Приклади використання

### Сценарій 1: Тільки VAT номер
**Input:** `DE123456789`

**Процес:**
1. Frontend відправляє `POST /api/vat-lookup` з `vat_number`
2. `EnrichmentOrchestrator`:
   - Викликає `VatLookupService.lookup()` → VIES API
   - Отримує назву компанії та адресу
   - Витягує домен з VIES адреси (якщо є)
   - Запускає OSINT по домену
3. Backend повертає `prefill` з 5-10 полями
4. Frontend підсвічує автозаповнені поля жовтим на 3.5 секунди

### Сценарій 2: Email або домен
**Input:** `info@company.de` або `company.de`

**Процес:**
1. `EnrichmentOrchestrator`:
   - Витягує домен з email (`company.de`)
   - Запускає `OsintScanner.run_all()`:
     - WHOIS → організація, країна, місто
     - DNS → A/MX записи
     - SSL → сертифікат (організація, валідність)
     - HTTP Headers → технології, CSP
2. Витягує підказки з OSINT:
   - `whois.org` → `counterparty_name`
   - `whois.country` → `counterparty_country`
   - `ssl.organization` → підтвердження назви
3. Повертає частково заповнені поля

### Сценарій 3: Комбінація VAT + Email + Назва компанії
**Input:**
```json
{
  "vat_number": "DE123456789",
  "email": "info@company.de",
  "company_name": "Company GmbH",
  "country_code": "DE"
}
```

**Процес:**
1. VIES lookup → основні дані компанії
2. OSINT по домену → додаткові поля (телефон, соцмережі)
3. Business Registry DE → перевірка реєстрації
4. Агрегація всіх джерел → максимальна кількість заповнених полів

## Додаткові можливості

### Enrichment Blueprint (`routes/enrichment.py`)

**Endpoint:** `/api/enrichment/enrich` (POST)

Альтернативний endpoint з тією ж логікою, але відокремлений від legacy `/api/vat-lookup`.

**Використання:**
```javascript
const response = await fetch('/api/enrichment/enrich', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        vat_number: 'DE123456789',
        domain: 'company.de'
    })
});
```

### Логування та моніторинг

```python
# application.py
app.logger.info(f"User {current_user.id} enrichment: VAT={vat_number}, "
                f"sources={enrichment_result.get('services', {}).keys()}")
```

**Лог-події:**
- Кількість використаних джерел (`vies`, `osint`, `registry_de`)
- Кількість заповнених полів
- Час виконання запиту

## Тестування

### 1. Через UI
1. Відкрийте `http://127.0.0.1:5000`
2. Увійдіть як `admin@example.com` / `admin123`
3. Перейдіть до форми верифікації
4. Введіть VAT номер: `DE123456789`
5. Клацніть поза полем (blur event)
6. Перевірте автозаповнення полів із підсвіткою

### 2. Через Postman/cURL
```bash
# 1. Login and get session cookie
curl -X POST http://127.0.0.1:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123"}' \
  -c cookies.txt

# 2. Test enrichment
curl -X POST http://127.0.0.1:5000/api/vat-lookup \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"vat_number": "DE123456789", "country_code": "DE"}'
```

### 3. Unit тести
```python
# tests/test_enrichment.py
def test_enrichment_vat_only():
    orchestrator = EnrichmentOrchestrator()
    result = orchestrator.enrich(vat_number='DE123456789')
    
    assert result['success'] is True
    assert 'prefill' in result
    assert 'services' in result
    assert 'vat_lookup' in result['services']

def test_enrichment_domain_only():
    orchestrator = EnrichmentOrchestrator()
    result = orchestrator.enrich(domain='example.com')
    
    assert result['success'] is True
    assert 'osint' in result['services']
```

## Обмеження та відомі проблеми

### 1. Затримка OSINT сканування
**Проблема:** WHOIS/DNS запити займають 2-5 секунд  
**Рішення:** Додано індикатор завантаження у frontend (`this.showVatPrefillMessages('search')`)

### 2. Недоступність державних реєстрів
**Проблема:** Деякі реєстри можуть бути недоступні або повільні  
**Рішення:** `try/except` блоки в `BusinessRegistryManager`, повертаємо часткові дані

### 3. Формат адреси з VIES
**Проблема:** VIES повертає адресу одним рядком ("Hauptstr. 1, 10115 Berlin")  
**Рішення:** Парсинг адреси в `VatLookupService._parse_address()` (якщо реалізовано)

### 4. OSINT може бути порожнім
**Проблема:** Новий домен без WHOIS/SSL даних  
**Рішення:** `_extract_from_osint()` обережно перевіряє наявність даних

## Майбутні покращення

### Фаза 1: Кешування (найближчим часом)
```python
# services/enrichment_flow.py
from flask_caching import Cache

cache = Cache(config={'CACHE_TYPE': 'redis', 'CACHE_DEFAULT_TIMEOUT': 3600})

@cache.memoize(timeout=3600)
def enrich(self, vat_number=None, domain=None, ...):
    # Enrichment logic
```

### Фаза 2: Paid APIs інтеграція (Q1 2026)
- **Clearbit API** ($99-999/mo) - розширені дані компанії
- **Hunter.io** ($49-399/mo) - перевірка email deliverability
- **Creditsafe** (€0.50-2.00/report) - кредитні звіти

### Фаза 3: ML покращення (Q2 2026)
- Передбачення відсутніх полів на основі історичних даних
- Оцінка достовірності (confidence score)
- Автоматична категоризація галузі

## Конфігурація

### Environment Variables
```bash
# .env
# No additional keys needed - uses free APIs

# Optional: Enable debug logging
ENRICHMENT_DEBUG=true

# Optional: Timeout for OSINT requests (default: 10s)
OSINT_TIMEOUT=15
```

## Troubleshooting

### Проблема: "Interner Fehler bei der Datensuche"
**Рішення:**
1. Перевірте логи Flask: `tail -f logs/app.log`
2. Перевірте доступність VIES API: `curl https://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl`
3. Перезапустіть сервіс: `flask run --debug`

### Проблема: Поля не автозаповнюються
**Рішення:**
1. Відкрийте DevTools → Network → перевірте відповідь `/api/vat-lookup`
2. Переконайтеся, що `prefill` об'єкт не пустий
3. Перевірте JavaScript консоль на помилки

### Проблема: OSINT не повертає дані
**Рішення:**
1. Перевірте, чи домен існує: `nslookup company.de`
2. Перевірте WHOIS доступність: `whois company.de`
3. Збільште timeout у `.env`: `OSINT_TIMEOUT=20`

---

**Дата оновлення:** 11 листопада 2025  
**Версія:** 1.0.0  
**Автор:** AI Assistant  
**Статус:** ✅ Активна функція в production
