"""
Test script to check CRM implementation
"""
from application import create_app
from auth.models import User, db
from crm.models import Counterparty, VerificationCheck, Alert

app = create_app()

with app.app_context():
    # Check users
    users = User.query.all()
    print(f"\n=== ПОЛЬЗОВАТЕЛИ ===")
    print(f"Найдено пользователей: {len(users)}")
    for u in users:
        print(f"  - {u.email} (ID: {u.id})")
    
    # Check counterparties
    counterparties = Counterparty.query.all()
    print(f"\n=== КОНТРАГЕНТЫ ===")
    print(f"Найдено контрагентов: {len(counterparties)}")
    for cp in counterparties:
        print(f"  - {cp.company_name} ({cp.country}) - User ID: {cp.user_id}")
    
    # Check verification checks
    checks = VerificationCheck.query.all()
    print(f"\n=== ПРОВЕРКИ ===")
    print(f"Найдено проверок: {len(checks)}")
    for check in checks[:5]:  # First 5
        print(f"  - Check ID: {check.id}, Date: {check.check_date}, Status: {check.overall_status}")
    
    # Check alerts
    alerts = Alert.query.all()
    print(f"\n=== АЛЕРТЫ ===")
    print(f"Найдено алертов: {len(alerts)}")
    for alert in alerts[:5]:  # First 5
        print(f"  - {alert.severity}: {alert.message} (Sent: {alert.is_sent})")
    
    print(f"\n=== ИТОГ ===")
    print(f"✓ База данных работает")
    print(f"✓ CRM модели загружены")
    print(f"✓ Всего записей: Users={len(users)}, Counterparties={len(counterparties)}, Checks={len(checks)}, Alerts={len(alerts)}")
