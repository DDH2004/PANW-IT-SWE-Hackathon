from fastapi.testclient import TestClient
from backend.main import app
from backend.db import Base, engine, SessionLocal
from backend.models.transaction import Transaction
from datetime import date

client = TestClient(app)

def setup_module(module):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.add_all([
        Transaction(date=date.today(), description='Random Item', amount=-12.3, merchant='ShopX', category=None),
        Transaction(date=date.today(), description='Coffee latte', amount=-4.5, merchant='Starbucks', category=None),
    ])
    db.commit()
    db.close()

def teardown_module(module):
    Base.metadata.drop_all(bind=engine)

def test_enrichment_flow():
    r = client.post('/enrich/?limit=10')
    assert r.status_code == 200
    data = r.json()
    assert data['enriched'] >= 1
    latest = client.get('/enrich/latest').json()
    assert len(latest) >= 1