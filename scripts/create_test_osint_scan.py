import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from application import create_app
from crm.osint_models import db, OsintScan, OsintFinding

app = create_app()
with app.app_context():
    scan = OsintScan(url='http://example.com', domain='example.com', email=None)
    db.session.add(scan)
    db.session.flush()
    findings = [
        {'service':'whois','status':'ok','notes':'whois ok','data':{'registrar':'Example Registrar'}},
        {'service':'dns','status':'ok','notes':'dns ok','data':{'A':'1.2.3.4'}}
    ]
    for r in findings:
        f = OsintFinding(scan_id=scan.id, service=r['service'], status=r['status'], notes=r['notes'], data=r['data'])
        db.session.add(f)
    db.session.commit()
    print('CREATED_SCAN_ID', scan.id)
