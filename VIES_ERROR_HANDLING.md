# VIES Error Handling Documentation

## Обзор

VAT Bot использует VIES (VAT Information Exchange System) Европейской Комиссии для проверки EU VAT номеров. Система VIES может возвращать различные ошибки, которые требуют специальной обработки.

## Типы VIES Ошибок

### 1. MS_UNAVAILABLE
**Причина:** Сервис проверки конкретной страны-члена ЕС временно недоступен.

**Обработка:**
- ✅ Автоматический retry с экспоненциальной задержкой (2s → 4s → 8s)
- ✅ 3 попытки по умолчанию
- ✅ Не кэшируется (чтобы не сохранять временную ошибку)
- ✅ Пользовательское сообщение на немецком: "Der Validierungsservice für dieses Land ist vorübergehend nicht verfügbar"

**Пример:**
```xml
<soap:Fault>
  <faultstring>MS_UNAVAILABLE</faultstring>
</soap:Fault>
```

### 2. MS_MAX_CONCURRENT_REQ
**Причина:** Превышен лимит одновременных запросов к сервису конкретной страны.

**Обработка:**
- ✅ Автоматический retry с экспоненциальной задержкой
- ✅ 3 попытки
- ✅ Не кэшируется
- ✅ Сообщение: "Zu viele gleichzeitige Anfragen. Bitte warten Sie einen Moment."

### 3. GLOBAL_MAX_CONCURRENT_REQ / SERVICE_UNAVAILABLE
**Причина:** VIES перегружен общими запросами от всех пользователей.

**Обработка:**
- ✅ Автоматический retry
- ✅ Не кэшируется
- ✅ Сообщение: "Der VIES-Service ist überlastet. Bitte versuchen Sie es in wenigen Minuten erneut."

### 4. TIMEOUT
**Причина:** Время ожидания ответа от сервиса истекло.

**Обработка:**
- ✅ Автоматический retry
- ✅ Не кэшируется
- ✅ Сообщение: "Service-Zeitüberschreitung. Bitte versuchen Sie es erneut."

### 5. INVALID_INPUT
**Причина:** Неправильный формат VAT номера.

**Обработка:**
- ❌ НЕ retry (постоянная ошибка)
- ✅ Кэшируется (1 час)
- ✅ Сообщение: "Ungültiges VAT-Nummernformat."

## Стратегия Retry

### Экспоненциальная задержка
```python
retry_delay = base_delay * (2 ** attempt)
# Попытка 1: 2 секунды
# Попытка 2: 4 секунды  
# Попытка 3: 8 секунд
```

### Условия для retry
Retry выполняется **только** для временных ошибок:
- `MS_UNAVAILABLE`
- `MS_MAX_CONCURRENT_REQ`
- `SERVICE_UNAVAILABLE`
- `GLOBAL_MAX_CONCURRENT_REQ`
- `TIMEOUT`

## Кэширование

### Кэшируются (1 час):
- ✅ Успешные проверки VAT
- ✅ Постоянные ошибки (`INVALID_INPUT`)
- ✅ HTTP ошибки (404, 500)

### НЕ кэшируются:
- ❌ Временные ошибки (MS_UNAVAILABLE, rate limits)
- ❌ Ошибки соединения

### Пример кэша:
```python
_cache = {
    'DE:123456789': (
        {
            'status': 'valid',
            'data': {...},
            'confidence': 0.95
        },
        datetime(2025, 11, 11, 15, 30)  # expiry
    )
}
```

## Код-примеры

### Основная логика retry
```python
for attempt in range(self.max_retries):
    try:
        response = requests.post(self.base_url, ...)
        result = self._parse_vies_response(response.text, response_time)
        
        # Проверка на retriable errors
        error_msg = str(result.get('error_message', ''))
        is_retriable_error = any(keyword in error_msg for keyword in [
            'MS_MAX_CONCURRENT_REQ',
            'MS_UNAVAILABLE', 
            'SERVICE_UNAVAILABLE',
            'GLOBAL_MAX_CONCURRENT_REQ',
            'TIMEOUT'
        ])
        
        if result.get('status') == 'error' and is_retriable_error:
            if attempt < self.max_retries - 1:
                delay = self.retry_delay * (2 ** attempt)
                logger.warning(f"VIES retriable error, retrying in {delay}s")
                time.sleep(delay)
                continue
        
        # Кэшируем только non-retriable results
        if not is_retriable_error:
            self._set_cache(cache_key, result)
        return result
```

### Парсинг ошибок
```python
if '<soap:Fault>' in response_xml:
    fault_message = self._extract_fault_message(response_xml)
    
    if 'MS_UNAVAILABLE' in fault_message:
        return self._create_error_response(
            "Der Validierungsservice für dieses Land ist vorübergehend nicht verfügbar",
            response_time
        )
```

## Мониторинг

### Логирование
```python
logger.warning(f"VIES retriable error, retrying in {delay}s (attempt {attempt + 1}/{self.max_retries}): {error_msg}")
logger.info(f"VIES cache hit for {cache_key}")
```

### Метрики (рекомендуется добавить)
- Количество retry по типу ошибки
- Hit rate кэша
- Время ответа VIES
- Процент успешных проверок

## Рекомендации для пользователей

### При MS_UNAVAILABLE:
1. Подождите 5-10 минут
2. Попробуйте снова
3. Если ошибка сохраняется > 1 час - проверьте [VIES status page](https://ec.europa.eu/taxation_customs/vies/)

### При GLOBAL_MAX_CONCURRENT_REQ:
1. VIES перегружен (обычно в рабочие часы ЕС)
2. Попробуйте в нерабочее время (вечер/ночь по CET)
3. Используйте альтернативные источники (Business Registries)

## Альтернативные стратегии

### Fallback на другие источники:
Если VIES недоступен, используем:
1. **Business Registries** (Handelsregister DE, ARES CZ, KRS PL)
2. **OSINT** (WHOIS, DNS, SSL сертификаты)
3. **Локальная валидация формата** VAT номера

### Пример из EnrichmentOrchestrator:
```python
# 1. Пробуем VIES
vat_result = self.vat_lookup.lookup(vat_number, country_code_hint)

# 2. Если VIES недоступен, используем registry
if vat_result.get('status') == 'error':
    registry_result = self.registry_manager.lookup(country_code_hint, company_name)
    prefills.update(registry_result.get('data', {}))
```

## Тестирование

### Тест-кейсы:
1. ✅ MS_UNAVAILABLE → 3 retry → возврат ошибки
2. ✅ MS_MAX_CONCURRENT_REQ → retry с exponential backoff
3. ✅ INVALID_INPUT → без retry, с кэшированием
4. ✅ Успешная проверка → кэширование на 1 час
5. ✅ Cache hit → без обращения к VIES

### Ручное тестирование:
```python
from services.vies import VIESService

service = VIESService()

# Тест 1: Валидный VAT
result = service.validate_vat('DE', '123456789')
print(result)

# Тест 2: Cache hit
result2 = service.validate_vat('DE', '123456789')  # Должен вернуть из кэша

# Тест 3: Неправильный формат
result3 = service.validate_vat('DE', 'INVALID')
print(result3)
```

## Обновления

**Последнее обновление:** 11 ноября 2025

**Изменения в версии 2.0:**
- ✅ Добавлена обработка `MS_UNAVAILABLE`
- ✅ Улучшена логика retry для всех временных ошибок
- ✅ Добавлены user-friendly сообщения на немецком
- ✅ Оптимизировано кэширование (не кэшируем retriable errors)
- ✅ Логирование retry attempts

**TODO:**
- [ ] Добавить метрики (Prometheus/Grafana)
- [ ] Dashboard для мониторинга VIES availability
- [ ] Автоматический fallback на Business Registries
- [ ] Rate limiting для предотвращения GLOBAL_MAX_CONCURRENT_REQ
