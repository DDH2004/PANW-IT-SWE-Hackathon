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

def test_upload_semicolon_and_synonyms():
    csv_content = "transaction_date;details;amount_usd;merchant_name\n2025-09-01;Test Purchase;-12.34;VendorX\n"
    r = client.post('/upload', files={'file':('alt.csv', csv_content, 'text/csv')})
    assert r.status_code == 200, r.text
    assert r.json()['records'] == 1
    txns = client.get('/transactions').json()
    assert any(t['description'] == 'Test Purchase' for t in txns)