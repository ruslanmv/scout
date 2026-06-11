from fastapi.testclient import TestClient
from app.main import app


def test_frontend_bootstrap_contract():
    c = TestClient(app)
    data = c.get('/api/v1/ui/bootstrap?country=Italy&city=Rome&goal=build_portfolio&profile=developer').json()
    assert 'report' in data
    assert 'local_topics' in data
    assert 'global_topics' in data
    assert data['report']['summary']['top_topic']


def test_report_and_batches():
    c = TestClient(app)
    assert c.get('/api/v1/report').status_code == 200
    assert c.get('/api/v1/batches/latest?limit=2').status_code == 200
    assert c.get('/api/v1/models/status').status_code == 200
