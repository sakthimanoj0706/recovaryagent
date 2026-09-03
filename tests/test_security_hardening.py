import os
import pytest
from fastapi.testclient import TestClient
from api.server import app

# Unset RECOVERAI_ENV for these tests to simulate production
@pytest.fixture(autouse=True)
def mock_prod_env(monkeypatch):
    monkeypatch.setenv("RECOVERAI_ENV", "production")
    monkeypatch.setenv("RECOVERAI_ADMIN_KEY", "admin123")
    monkeypatch.setenv("RECOVERAI_VIEWER_KEY", "view123")

client = TestClient(app)

def test_unauthenticated_rejected():
    res = client.get("/api/system/health")
    assert res.status_code == 401
    assert res.json()["detail"] == "Authentication credentials were not provided."

def test_invalid_key_rejected():
    res = client.get("/api/system/health", headers={"X-API-Key": "wrong"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid API key."

def test_viewer_can_read():
    res = client.get("/api/system/health", headers={"X-API-Key": "view123"})
    assert res.status_code == 200

def test_viewer_cannot_execute():
    # POST to provider/test-connection is admin only
    res = client.post("/api/provider/test-connection", headers={"X-API-Key": "view123"})
    assert res.status_code == 403
    assert res.json()["detail"] == "You do not have permission to perform this action."

def test_admin_can_execute():
    res = client.post("/api/provider/test-connection", headers={"X-API-Key": "admin123"})
    # It might be 400 or 500 depending on network, but not 401/403
    assert res.status_code not in (401, 403)
