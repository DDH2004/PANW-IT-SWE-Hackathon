from fastapi.testclient import TestClient
from backend.main import app
from backend.db import SessionLocal, Base, engine
from backend.models.transaction import Transaction
from datetime import date

import pytest

client = TestClient(app)

@pytest.fixture(autouse=True, scope="module")
def create_tables():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def seed():
    db = SessionLocal()
    db.add_all([
        Transaction(date=date.today(), description='Salary', amount=3000, merchant='Employer', category='Income'),
        Transaction(date=date.today(), description='Coffee', amount=-4.5, merchant='Starbucks', category='Food & Drink'),
        Transaction(date=date.today(), description='Groceries', amount=-55.2, merchant='WholeFoods', category='Groceries'),
    ])
    db.commit()
    db.close()

def test_coach_with_snapshot(monkeypatch):
    seed()
    # Monkeypatch httpx post to avoid calling real Ollama
    import httpx
    async def fake_post(self, url, json):
        class R:
            status_code = 200
            def raise_for_status(self):
                pass
            def json(self):
                return {"response": "Based on your snapshot net is positive."}
        return R()
    async def fake_get(self, url):
        class R:
            status_code = 200
            def json(self):
                return {"models": [{"name": "phi3:mini"}]}
        return R()
    monkeypatch.setattr(httpx.AsyncClient, 'post', fake_post, raising=True)
    monkeypatch.setattr(httpx.AsyncClient, 'get', fake_get, raising=True)
    r = client.post('/coach', json={"message": "Any tips?", "include_data": True})
    assert r.status_code == 200
    assert 'response' in r.json()