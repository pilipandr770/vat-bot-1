# 🚀 OSINT Scanner - Quick Access

## 🌐 Production URL

### **https://vat-bot-1.onrender.com/osint/scan**

---

## 📋 Quick Start (3 кроки)

### 1. Авторизуйтеся
👉 https://vat-bot-1.onrender.com/auth/login

### 2. Клікніть "OSINT Scanner" в меню
Або відкрийте прямо: https://vat-bot-1.onrender.com/osint/scan

### 3. Введіть домен і натисніть "Запустити"
Приклад: `google.com`

---

## 🎯 Що перевіряє (7 адаптерів)

| # | Адаптер | Що перевіряє | API ключі |
|---|---------|--------------|-----------|
| 1 | **WHOIS** | Реєстратор, дати, nameservers | ❌ Не потрібні |
| 2 | **DNS** | A, MX, NS, TXT записи | ❌ Не потрібні |
| 3 | **SSL Labs** | Оцінка SSL сертифікату (A+ до F) | ❌ Публічне API |
| 4 | **Headers** | CSP, HSTS, X-Frame, тощо | ❌ Не потрібні |
| 5 | **Robots** | robots.txt, sitemap.xml | ❌ Не потрібні |
| 6 | **Social** | LinkedIn, FB, Instagram, YouTube | ❌ Не потрібні |
| 7 | **Email** | RFC валідація формату | ❌ Не потрібні |

---

## 📊 Приклад результатів

```
✅ WHOIS: ok
   Registrar: MarkMonitor, Inc.
   Expiration: 2028-09-14

✅ DNS: ok
   A records: 1
   MX records: 1

✅ SSL_LABS: ok
   Grade: B
   Status: READY

⚠️ SECURITY_HEADERS: warn
   Missing: CSP, HSTS, X-Content-Type-Options

✅ ROBOTS_SITEMAP: ok
   robots.txt: present

✅ SOCIAL_LINKS: ok
   Found: 1 link (YouTube)

❌ EMAIL_BASIC: error
   Notes: email empty
```

---

## 🔗 Корисні посилання

- **Інструкція користувача**: [OSINT_GUIDE.md](./OSINT_GUIDE.md)
- **Тестування**: [OSINT_TESTING.md](./OSINT_TESTING.md)
- **Приклад результатів**: https://vat-bot-1.onrender.com/osint/scan/2

---

## 💡 Швидкі тести

### Тест 1: Google
```
Домен: google.com
URL: https://google.com
```

### Тест 2: GitHub
```
Домен: github.com
URL: https://github.com
```

### Тест 3: Ваш контрагент
```
Домен: company-name.de
URL: https://company-name.de
Email: info@company-name.de
```

---

## ⚡ Час виконання

- **WHOIS**: ~1-2 сек
- **DNS**: ~1-2 сек
- **SSL Labs**: ~20-30 сек (перший раз, потім кеш)
- **Headers**: ~1-2 сек
- **Robots**: ~1 сек
- **Social**: ~2-3 сек
- **Email**: <1 сек

**Загальний час**: 10-30 секунд

---

## 🎉 Готово до використання!

Відкрийте 👉 **https://vat-bot-1.onrender.com/osint/scan**
