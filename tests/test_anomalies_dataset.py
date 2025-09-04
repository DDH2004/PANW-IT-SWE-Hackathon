from fastapi.testclient import TestClient
from backend.main import app
from backend.db import Base, engine
import os, io, csv

client = TestClient(app)

def setup_module(module):
    Base.metadata.create_all(bind=engine)

def teardown_module(module):
    Base.metadata.drop_all(bind=engine)

def test_anomaly_sample_dataset():
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'sample_anomalies.csv'))
    with open(path, 'rb') as f:
        r = client.post('/upload', files={'file': ('sample_anomalies.csv', f, 'text/csv')})
    assert r.status_code == 200, r.text
    a = client.get('/anomalies')
    assert a.status_code == 200
    data = a.json()
    # Expect at least one outlier (the -400) and a duplicate group (3 coffees)
    assert any(abs(o['amount']) >= 400 for o in data['outliers'])
    assert any(d['merchant'] == 'Starbucks' and d['count'] >= 2 for d in data['duplicates'])