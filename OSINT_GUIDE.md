# 🔍 OSINT Scanner - Інструкція користувача

## 📍 Доступ до OSINT Scanner

### На Production (Render):
**https://vat-bot-1.onrender.com/osint/scan**

### Локально:
**http://localhost:5000/osint/scan**

---

## 🎯 Як використовувати:

### 1. Авторизуйтесь у системі
- Перейдіть на https://vat-bot-1.onrender.com/auth/login
- Введіть ваш email та пароль

### 2. Відкрийте OSINT Scanner
Два способи:
- **Через навігацію**: Клік на "OSINT Scanner" у верхньому меню
- **Пряме посилання**: https://vat-bot-1.onrender.com/osint/scan

### 3. Заповніть форму сканування

**Обов'язкові поля:**
- ✅ **Домен** (обов'язково): `google.com`, `example.com`

**Опційні поля:**
- 🌐 **URL**: `https://google.com` (для аналізу headers та соцмереж)
- 📧 **E-mail**: `info@example.com` (для валідації формату)

### 4. Натисніть "Запустити сканування"

Система виконає 7 перевірок:
- ⏱️ Час виконання: ~10-30 секунд
- 🔄 Індикатор прогресу: спінер на кнопці

### 5. Перегляньте результати

**Швидкий перегляд:**
- З'явиться картка з результатами кожної перевірки
- Кольорові індикатори: ✅ (ok), ⚠️ (warn), ❌ (error)

**Повні деталі:**
- Клік на "Переглянути повні результати"
- Відкриється сторінка з JSON даними кожного адаптера

---

## 📊 Що перевіряє кожен адаптер:

### 1. **WHOIS** ✅
- Реєстратор домену
- Дати реєстрації та закінчення
- Статус домену
- Name servers

### 2. **DNS** ✅
- A/AAAA записи (IPv4/IPv6)
- MX записи (mail servers)
- NS записи (name servers)
- TXT записи (SPF, DKIM, DMARC)
- ⚠️ Попередження якщо немає MX записів (не бізнес-домен)

### 3. **SSL Labs** ✅
- Оцінка SSL сертифікату (A+, A, B, C, F)
- Статус готовності
- Кількість endpoints

### 4. **Security Headers** ⚠️
Перевіряє наявність заголовків безпеки:
- Content-Security-Policy (CSP)
- Strict-Transport-Security (HSTS)
- X-Content-Type-Options
- X-Frame-Options
- Referrer-Policy
- Permissions-Policy

### 5. **Robots & Sitemap** ✅
- Наявність `/robots.txt`
- Директиви Disallow
- Знайдені sitemap.xml файли

### 6. **Social Links** ✅
Пошук посилань на соцмережі:
- LinkedIn
- Facebook
- Instagram
- YouTube
- Telegram
- X (Twitter)

### 7. **Email Validation** ✅
- Валідація формату згідно RFC
- Перевірка доменної частини
- Локальна частина (без SMTP проби)

---

## 🌐 Публічний доступ до результатів

Результати сканування **доступні без авторизації** за прямим посиланням:

**Формат:**
```
https://vat-bot-1.onrender.com/osint/scan/<scan_id>
```

**Приклади:**
- https://vat-bot-1.onrender.com/osint/scan/1
- https://vat-bot-1.onrender.com/osint/scan/2

---

## 🔒 Безпека та обмеження

### Пасивне сканування
- ✅ Не робить активних атак
- ✅ Не використовує вразливості
- ✅ Не вимагає автентифікації до цільового домену
- ✅ Не залишає слідів в логах цілі

### Без платних API ключів
Всі перевірки безкоштовні:
- WHOIS: python-whois
- DNS: dnspython
- SSL Labs: публічне API (без ключа)
- Headers: прямі HTTP запити
- Robots/Sitemap: HTTP GET
- Social Links: BeautifulSoup парсинг
- Email: email-validator бібліотека

### Rate Limits
SSL Labs API має обмеження:
- ~25 сканувань на годину з одного IP
- Кешування результатів на 24 години

---

## 💡 Приклади використання

### Перевірка нового контрагента
```
Домен: company-name.de
URL: https://company-name.de
Email: info@company-name.de
```

### Швидка перевірка домену
```
Домен: example.com
(URL та Email залиште порожніми)
```

### Аналіз email домену
```
Домен: gmail.com
Email: test@gmail.com
```

---

## 🐛 Відомі обмеження

1. **SSL Labs повільний** (~20-30 сек на перше сканування)
2. **WHOIS може бути приватним** (privacy protection)
3. **Social Links** знаходить тільки публічні посилання на HTML сторінці
4. **Email validation** не перевіряє існування mailbox (тільки формат)
5. **DNS** може повертати кешовані дані (TTL залежить від провайдера)

---

## 📞 Підтримка

Виникли проблеми? Перевірте:
1. ✅ Домен введено правильно (без `http://` або `www.`)
2. ✅ URL починається з `https://` або `http://`
3. ✅ Email має правильний формат `user@domain.com`

---

**Створено:** October 18, 2025  
**Версія:** 1.0.0  
**Сервіс:** https://vat-bot-1.onrender.com
