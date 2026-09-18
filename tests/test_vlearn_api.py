from fastapi.testclient import TestClient

from app.main import app


def test_health_and_dump_then_probe():
    with TestClient(app) as client:
        h = client.get("/health")
        assert h.status_code == 200
        body = h.json()
        assert "provider" in body
        assert body.get("cards", 0) >= 1

        r = client.post(
            "/api/chat",
            json={
                "user_id": "demo-moi-toanh",
                "session_id": "s-test-1",
                "text": "Self-attention là gì?",
                "selection": "self-attention",
                "lesson_id": "day01-self-attention",
            },
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["kind"] in ("explain", "no_source")

        r2 = client.post(
            "/api/chat",
            json={
                "user_id": "demo-moi-toanh",
                "session_id": "s-test-1",
                "text": "khó hiểu quá",
                "selection": "self-attention",
                "action": "confused",
                "lesson_id": "day01-self-attention",
            },
        )
        assert r2.status_code == 200, r2.text
        assert r2.json()["kind"] in ("survey", "explain")


def test_known_persona_explains():
    with TestClient(app) as client:
        r = client.post(
            "/api/chat",
            json={
                "user_id": "demo-vung",
                "session_id": "s-test-2",
                "text": "Self-attention là gì?",
                "selection": "self-attention",
            },
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["kind"] in ("explain", "survey")
