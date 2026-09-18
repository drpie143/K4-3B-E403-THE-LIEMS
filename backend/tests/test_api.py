from fastapi.testclient import TestClient

from app import main


def client(orch):
    main.app.dependency_overrides[main.get_orchestrator] = lambda: orch
    return TestClient(main.app)


def test_full_http_flow(orch):
    c = client(orch)
    assert c.get("/health").json()["provider"] == "fake"
    u = {"user_id": "demo-trung-binh", "session_id": "h1"}
    r = c.post("/api/chat", json={**u, "text": "Self-attention là gì?"}).json()
    assert r["kind"] == "explain" and r["answer"]["blocks"]
    r = c.post("/api/chat", json={**u, "text": "Mình chưa hiểu", "action": "confused", "concept_hint": "self_attention"}).json()
    assert r["kind"] == "survey"
    down = next(n for n in r["notices"] if n["kind"] == "down")
    r = c.post("/api/survey", json={**u, "concept": "self_attention", "levels": {"vector": "chua"}, "style": "vi_du"}).json()
    assert r["decision"]["level"] == "L1"
    r = c.post("/api/adjust", json={**u, "concept": "self_attention", "kind": "deeper"}).json()
    assert r["decision"]["level"] == "L2"
    fb = c.post("/api/feedback", json={**u, "concept": "self_attention", "value": "up"}).json()
    assert fb["next"] == "check"
    q = c.get("/api/check", params={**u, "concept": "self_attention"}).json()
    res = c.post("/api/check", json={**u, "concept": "self_attention", "question_id": q["id"], "answer": "B"}).json()
    assert res["correct"] and res["next"] == "done"
    prof = c.get("/api/profile", params={"user_id": u["user_id"]}).json()
    assert prof["concepts"]["vector"]["level"] == "chua"
    assert c.post("/api/profile/undo", json={"user_id": u["user_id"], "event_ids": down["event_ids"]}).json()["undone"]
    p = c.put("/api/profile", json={"user_id": u["user_id"], "concept": "token", "level": "chua"}).json()
    assert p["profile"]["concepts"]["token"]["level"] == "chua" and p["notices"]
    p = c.put("/api/profile", json={"user_id": u["user_id"], "memory_on": False}).json()
    assert p["profile"]["memory_on"] is False
    assert c.delete("/api/profile", params={"user_id": u["user_id"]}).json()["profile"]["concepts"] == {}
    assert c.post("/api/profile/reset", json={"user_id": u["user_id"]}).json()["profile"]["concepts"]["token"]["level"] == "hieu_ro"
    s = c.get("/api/sources/T06-131").json()
    assert s["mode"] == "summary" and "Key" in s["text"]
    assert c.get("/api/sources/T00-000").status_code == 404
    assert c.post("/api/adjust", json={"user_id": "x", "session_id": "none", "concept": "self_attention", "kind": "easier"}).status_code == 404
    assert c.post("/api/handoff", json={**u}).json()["draft"]
    main.app.dependency_overrides.clear()


def test_mock_is_served(orch):
    c = client(orch)
    r = c.get("/", follow_redirects=False)
    assert r.status_code in (302, 307) and "mode=live" in r.headers["location"]
    assert c.get("/app/index.html").status_code == 200
    assert c.get("/app/js/api.js").status_code == 200
    main.app.dependency_overrides.clear()
