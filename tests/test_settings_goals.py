from fastapi.testclient import TestClient
from backend.main import app
from backend.db import Base, engine, SessionLocal
from backend.models import Transaction
from datetime import date

client = TestClient(app)


def setup_module(module):
    Base.metadata.create_all(bind=engine)


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)


def seed_transactions():
    db = SessionLocal()
    db.add_all([
        Transaction(date=date.today().replace(day=1), description="Paycheck", amount=3000, category="Income", merchant="Employer"),
        Transaction(date=date.today().replace(day=2), description="Groceries", amount=-150.25, category="Groceries", merchant="Store"),
    ])
    db.commit()
    db.close()


def test_settings_and_dashboard_budget():
    seed_transactions()
    # Upsert budget
    r = client.put('/settings/MONTHLY_BUDGET', json={'value': '2000'})
    assert r.status_code == 200
    # Dashboard should reflect
    d = client.get('/dashboard')
    data = d.json()
    assert data['monthly_budget'] == 2000.0
    assert data['budget_used_pct'] is not None


def test_goal_lifecycle():
    # create
    r = client.post('/goals/', json={"name": "Emergency Fund", "target_amount": 5000})
    assert r.status_code == 200
    gid = r.json()['id']
    # list
    r2 = client.get('/goals/')
    assert any(g['id'] == gid for g in r2.json())
    # update
    r3 = client.patch(f'/goals/{gid}', json={"current_amount": 1200})
    assert r3.status_code == 200
    assert r3.json()['current_amount'] == 1200
    # sync (no matching transactions so remains same)
    r4 = client.post(f'/goals/{gid}/sync')
    assert r4.status_code == 200
    # delete
    r5 = client.delete(f'/goals/{gid}')
    assert r5.status_code == 200