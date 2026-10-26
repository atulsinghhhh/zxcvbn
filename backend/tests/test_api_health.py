"""Tests for GET /api/health."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_returns_200(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200


def test_health_response_schema(client):
    data = client.get("/api/health").json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


def test_health_content_type(client):
    resp = client.get("/api/health")
    assert "application/json" in resp.headers["content-type"]
