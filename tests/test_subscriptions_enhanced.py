from fastapi.testclient import TestClient
from backend.main import app
from backend.db import Base, engine
import os

client = TestClient(app)

def setup_module(module):
    Base.metadata.create_all(bind=engine)
    # Load rich sample for subscriptions
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'sample_transactions_rich.csv'))
    with open(path, 'rb') as f:
        client.post('/upload', files={'file': ('sample_transactions_rich.csv', f, 'text/csv')})

def teardown_module(module):
    Base.metadata.drop_all(bind=engine)

def test_enhanced_subscriptions_flags():
    r = client.get('/subscriptions')
    assert r.status_code == 200
    subs = r.json()['subscriptions']
    # Expect Spotify and Netflix present
    merchants = {s['merchant'] for s in subs}
    assert 'Spotify' in merchants
    assert 'Netflix' in merchants
    # Flags should include 'recurring'
    spotify = [s for s in subs if s['merchant']=='Spotify'][0]
    assert 'recurring' in spotify['flags']