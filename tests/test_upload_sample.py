from fastapi.testclient import TestClient
from backend.main import app
from backend.db import Base, engine
import os

client = TestClient(app)

def setup_module(module):
    Base.metadata.create_all(bind=engine)

def teardown_module(module):
    Base.metadata.drop_all(bind=engine)

def test_sample_csv_upload():
    sample_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'sample_transactions.csv')
    sample_path = os.path.abspath(sample_path)
    with open(sample_path, 'rb') as f:
        files = {'file': ('sample_transactions.csv', f, 'text/csv')}
        r = client.post('/upload', files=files)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data['records'] >= 5