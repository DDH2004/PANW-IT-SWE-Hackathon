from fastapi.testclient import TestClient
from backend.main import app
from backend.db import Base, engine
import pytest

client = TestClient(app)

@pytest.fixture(autouse=True, scope="module")
def create_tables():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_upload_and_transactions():
    csv_content = "date,description,amount,merchant\n2025-01-01,Coffee,-3.50,Starbucks\n"
    files = {"file": ("test.csv", csv_content, "text/csv")}
    r = client.post('/upload', files=files)
    assert r.status_code == 200
    data = r.json()
    assert data['records'] == 1
    txns = client.get('/transactions').json()
    assert any(t['description'] == 'Coffee' for t in txns)

def test_coach_validation():
    r = client.post('/coach', json={"message": "hi"})
    # 'hi' too short (min_length=3) => 422
    assert r.status_code == 422
