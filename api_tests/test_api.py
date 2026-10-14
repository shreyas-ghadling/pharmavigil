"""API contracts tested without database access or production mutations."""
import os
os.environ.setdefault("SESSION_SECRET", "isolated-api-test-secret-not-for-deployment")
import pytest
from fastapi.testclient import TestClient
from app.api import server
from app.utils.auth import hash_password
from app.utils.exceptions import DatabaseConnectionError, RecalledBatchOperationError

@pytest.fixture
def environment(monkeypatch):
    users = {}
    for role, username in [(server.ADMIN, "admin"), (server.DOCTOR, "doctor"), (server.PHARMACIST, "pharmacist")]:
        users[username] = {"user_id": len(users)+1, "username": username, "password_hash": hash_password("test-password"),
                           "role": role, "full_name": username.title(), "email": f"{username}@example.test"}
    monkeypatch.setattr(server, "account", lambda name: users.get(name))
    return users

@pytest.fixture
def client(environment):
    with TestClient(server.app, raise_server_exceptions=False) as c:
        yield c

def sign_in(client, username="admin"):
    response = client.post("/api/auth/login", json={"username": username, "password": "test-password"})
    assert response.status_code == 200
    return {"X-CSRF-Token": response.json()["csrf"]}

def test_passwords_and_hashes_never_returned(client):
    sign_in(client)
    data = client.get("/api/auth/me").json()
    assert data["role"] == server.ADMIN
    assert "password" not in data and "password_hash" not in data
    assert "httponly" in client.cookies.get("pv_session", "") or client.cookies.get("pv_session")

def test_invalid_login(client):
    assert client.post("/api/auth/login", json={"username": "admin", "password": "wrong"}).status_code == 401
    assert client.get("/api/auth/me").status_code == 401

def test_database_outage_never_falls_back(client, monkeypatch):
    def down(name):
        raise DatabaseConnectionError("mongodb://secret:password@private-host")
    monkeypatch.setattr(server, "account", down)
    r = client.post("/api/auth/login", json={"username": "admin", "password": "test-password"})
    assert r.status_code == 503
    assert "password@" not in r.text and "private-host" not in r.text

def test_cookie_security(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "test-password"})
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "max-age=28800" in cookie

def test_csrf_logout_and_cross_origin(client):
    headers = sign_in(client)
    assert client.post("/api/auth/logout").status_code == 403
    assert client.post("/api/auth/logout", headers={**headers, "Origin": "https://another.example"}).status_code == 403
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/auth/me").status_code == 401

@pytest.mark.parametrize("username", ["doctor", "pharmacist"])
@pytest.mark.parametrize("path", ["/api/signals", "/api/clinical-search", "/api/recalls", "/api/quarantine", "/api/exports/audit.pdf", "/api/exports/quarantine.csv"])
def test_admin_endpoints_reject_other_roles(client, username, path):
    sign_in(client, username)
    assert client.get(path).status_code == 403

def test_reporting_and_inventory_roles(client):
    headers=sign_in(client,"doctor")
    assert client.get("/api/inventory").status_code == 403
    assert client.post("/api/inventory/dispatch",headers=headers,json={"batch_number":"BCH-X-1","hospital_id":1,"quantity":1,"dispatch_date":"2026-10-12"}).status_code == 403

def test_roles_rechecked_each_request(client,environment):
    sign_in(client)
    environment["admin"]["role"]=server.PHARMACIST
    assert client.get("/api/recalls").status_code == 403

def test_password_change_and_expiry_invalidate_session(client,environment,monkeypatch):
    sign_in(client)
    environment["admin"]["password_hash"]=hash_password("new-test-password")
    assert client.get("/api/auth/me").status_code == 401
    sign_in(client,"doctor")
    monkeypatch.setattr(server,"SESSION_SECONDS",-1)
    assert client.get("/api/auth/me").status_code == 401

def test_recall_attributed_to_authenticated_user(client,monkeypatch):
    recorded=[]
    monkeypatch.setattr(server.sql_service,"execute_emergency_recall",lambda *args:recorded.append(args) or {"status":"RECALLED"})
    headers=sign_in(client)
    r=client.post("/api/recalls",headers=headers,json={"batch_number":"BCH-TEST-1","reason":"Safety concern","recalled_by":"spoof"})
    assert r.status_code == 201 and recorded[0][2] == "Admin"

def test_repeat_recall_returns_actionable_conflict(client,monkeypatch):
    def already(*args): raise RecalledBatchOperationError("BCH-TEST-1")
    monkeypatch.setattr(server.sql_service,"execute_emergency_recall",already)
    r=client.post("/api/recalls",headers=sign_in(client),json={"batch_number":"BCH-TEST-1","reason":"Safety concern"})
    assert r.status_code == 409

def test_invalid_dispatch_rejected_before_service_call(client):
    r=client.post("/api/inventory/dispatch",headers=sign_in(client),json={"batch_number":"BCH-X-1","hospital_id":1,"quantity":-1,"dispatch_date":"2026-10-12"})
    assert r.status_code == 422 and r.json()["fields"]

def test_import_errors_return_no_saved_rows(client,monkeypatch):
    monkeypatch.setattr(server.report_generator,"ingest_batches_from_csv",lambda *args:(0,["Row 1 rejected: Duplicate batch number 'BCH-X-1'."]))
    r=client.post("/api/inventory/import",headers=sign_in(client),files={"file":("batch.csv",b"batch_number\nBCH-X-1","text/csv")})
    assert r.status_code == 422 and r.json()["count"] == 0

def test_missing_api_route_does_not_serve_spa(client):
    assert client.get("/api/not-a-route").status_code == 404
    assert client.get("/inventory").status_code == 200


def reporting_payload():
    return {
        "medicine_id": 101, "medicine_name": "Cardiomax", "batch_number": None,
        "reporter_type": "PATIENT", "patient_demographics": {"age": 0, "gender": "Female"},
        "symptoms": [{"name": "Nausea", "onset_minutes": 0}], "severity_score": 1,
    }


@pytest.mark.parametrize("field", ["reporter_type", "age", "gender", "onset_minutes", "severity_score"])
def test_clinical_fields_are_not_guessed_when_missing(client, field):
    payload = reporting_payload()
    if field in {"age", "gender"}:
        payload["patient_demographics"].pop(field)
    elif field == "onset_minutes":
        payload["symptoms"][0].pop(field)
    else:
        payload.pop(field)
    response = client.post("/api/adverse-reports", headers=sign_in(client, "doctor"), json=payload)
    assert response.status_code == 422
    assert any(field in item["field"] for item in response.json()["fields"])


def test_explicit_zero_age_onset_and_unknown_batch_are_accepted(client, monkeypatch):
    recorded = []
    monkeypatch.setattr(server.sql_service, "get_all_medicines", lambda: [{"medicine_id": 101, "commercial_name": "Cardiomax"}])
    monkeypatch.setattr(server.mongo_service, "insert_adverse_report", lambda data: recorded.append(data) or "ADR-TEST")
    response = client.post("/api/adverse-reports", headers=sign_in(client, "doctor"), json=reporting_payload())
    assert response.status_code == 201
    assert recorded[0]["batch_number"] is None
    assert recorded[0]["patient_demographics"]["age"] == 0
    assert recorded[0]["symptoms"][0]["onset_minutes"] == 0


@pytest.mark.parametrize("onset", [None, 10080])
def test_unknown_or_delayed_onset_is_accepted(client, monkeypatch, onset):
    recorded = []
    monkeypatch.setattr(server.sql_service, "get_all_medicines", lambda: [{"medicine_id": 101, "commercial_name": "Cardiomax"}])
    monkeypatch.setattr(server.mongo_service, "insert_adverse_report", lambda data: recorded.append(data) or "ADR-TEST")
    payload = reporting_payload()
    payload["symptoms"][0]["onset_minutes"] = onset
    response = client.post("/api/adverse-reports", headers=sign_in(client, "doctor"), json=payload)
    assert response.status_code == 201
    assert recorded[0]["symptoms"][0]["onset_minutes"] == onset


@pytest.mark.parametrize("criteria", [None, [], ["HOSPITALIZATION"], ["DEATH", "LIFE_THREATENING"]])
def test_serious_outcomes_are_independent_of_intensity(client, monkeypatch, criteria):
    recorded = []
    monkeypatch.setattr(server.sql_service, "get_all_medicines", lambda: [{"medicine_id": 101, "commercial_name": "Cardiomax"}])
    monkeypatch.setattr(server.mongo_service, "insert_adverse_report", lambda data: recorded.append(data) or "ADR-TEST")
    payload = {**reporting_payload(), "seriousness_criteria": criteria}
    response = client.post("/api/adverse-reports", headers=sign_in(client, "doctor"), json=payload)
    assert response.status_code == 201
    assert recorded[0]["seriousness_criteria"] == criteria
    assert recorded[0]["severity_score"] == 1
