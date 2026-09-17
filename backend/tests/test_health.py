from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_check() -> None:
    """Verifies that the health check endpoint returns 200 OK and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
