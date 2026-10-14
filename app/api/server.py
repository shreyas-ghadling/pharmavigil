"""Same-origin API and SPA host. Database secrets never enter frontend assets."""
import io
import os
import secrets
import hashlib
import logging
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Depends, HTTPException, Request, Response, UploadFile, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from pydantic import BaseModel, Field

from app.config import config
from app.database.mysql_client import mysql_client
from app.database.mongo_client import mongo_client
from app.services.sql_service import sql_service
from app.services.mongo_service import mongo_service
from app.services.report_generator import report_generator
from app.models.schemas import AdverseReportCreate
from app.utils.auth import verify_password, ALL_ROLES
from app.utils.exceptions import DatabaseConnectionError, PharmavigilException

app = FastAPI(title="Pharmavigil API", docs_url=None, redoc_url=None)
logger = logging.getLogger("pharmavigil.api")


def log_failure(request, exc):
    # Record error types/codes, never database URIs, SQL, passwords or clinical data.
    chain = []
    while exc is not None and len(chain) < 4:
        chain.append(f"{type(exc).__name__}(errno={getattr(exc, 'errno', None)})")
        exc = getattr(exc, "original_exception", None) or exc.__cause__
    logger.error("Request failed path=%s errors=%s", request.url.path, " -> ".join(chain))
SESSION_SECONDS = 8 * 3600
COOKIE = "pv_session"
ADMIN = "SAFETY_OFFICER_ADMIN"
DOCTOR = "DOCTOR_PATIENT"
PHARMACIST = "PHARMACIST"
secure_cookie = os.getenv("APP_ENV", "development") == "production"
session_secret = os.getenv("SESSION_SECRET", "")
if not session_secret:
    raise RuntimeError("SESSION_SECRET is required; set a random secret in backend configuration.")
signer = URLSafeTimedSerializer(session_secret, salt="pharmavigil-session-v1")


def error(status, message, fields=None):
    return JSONResponse({"message": message, "fields": fields or []}, status_code=status)


@app.middleware("http")
async def request_safety(request: Request, call_next):
    if request.url.path.startswith("/api/") and request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and urlsplit(origin).netloc != request.headers.get("host"):
            return error(403, "This request must come from Pharmavigil.")
        if request.url.path != "/api/auth/login":
            try:
                token = signer.loads(request.cookies.get(COOKIE, ""), max_age=SESSION_SECONDS)
            except (BadSignature, SignatureExpired):
                return error(401, "Please sign in again.")
            if not secrets.compare_digest(request.headers.get("x-csrf-token", ""), token.get("csrf", "")):
                return error(403, "Your session could not be verified. Refresh and try again.")
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "DENY"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return error(exc.status_code, exc.detail)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return error(422, "Check the highlighted fields.", [
        {"field": ".".join(str(x) for x in e["loc"][1:]), "message": e["msg"]}
        for e in exc.errors()
    ])


@app.exception_handler(DatabaseConnectionError)
async def database_error(request, exc):
    log_failure(request, exc)
    return error(503, "The database is temporarily unavailable. Please try again.")


@app.exception_handler(PharmavigilException)
async def domain_error(request, exc):
    return error(409, str(exc))


@app.exception_handler(ValueError)
async def input_error(request, exc):
    message = str(exc)
    return error(422, message if message.startswith(("Only ", "The selected batch")) else "The operation could not be completed. Check your inputs.")


@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    log_failure(request, exc)
    return error(503, "The operation is temporarily unavailable. Please try again.")


def account(username):
    return mysql_client.execute_one(
        "SELECT user_id, username, password_hash, role, full_name, email FROM users WHERE LOWER(username) = %s",
        (username.strip().lower(),),
    )


def public_user(row):
    return {k: row[k] for k in ("user_id", "username", "role", "full_name", "email")}


def current_user(request: Request):
    try:
        token = signer.loads(request.cookies.get(COOKIE, ""), max_age=SESSION_SECONDS)
    except (BadSignature, SignatureExpired):
        raise HTTPException(401, "Please sign in again.")
    row = account(token["username"])
    if not row or row["role"] not in ALL_ROLES:
        raise HTTPException(401, "This account is no longer available.")
    fingerprint = hashlib.sha256(row["password_hash"].encode()).hexdigest()
    if not secrets.compare_digest(fingerprint, token.get("fingerprint", "")):
        raise HTTPException(401, "Please sign in again.")
    return {**public_user(row), "csrf": token["csrf"]}


def access(*roles):
    def guard(user=Depends(current_user)):
        if user["role"] not in roles:
            raise HTTPException(403, "Your role cannot access this section.")
        return user
    return guard


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


@app.post("/api/auth/login")
def login(payload: Login, response: Response):
    row = account(payload.username)
    if not row or row["role"] not in ALL_ROLES or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(401, "Incorrect username or password.")
    csrf = secrets.token_urlsafe(32)
    token = signer.dumps({"username": row["username"], "csrf": csrf,
                          "fingerprint": hashlib.sha256(row["password_hash"].encode()).hexdigest()})
    response.set_cookie(COOKIE, token, httponly=True, secure=secure_cookie,
                        samesite="strict", max_age=SESSION_SECONDS, path="/")
    return {**public_user(row), "csrf": csrf}


@app.get("/api/auth/me")
def me(user=Depends(current_user)):
    return user


@app.post("/api/auth/logout")
def logout(response: Response, user=Depends(current_user)):
    response.delete_cookie(COOKIE, path="/", secure=secure_cookie, httponly=True, samesite="strict")
    return {"message": "Signed out."}


@app.get("/api/health")
def health(user=Depends(current_user)):
    try:
        mysql_client.execute_one("SELECT 1 AS alive")
        mysql_ok = True
    except Exception:
        mysql_ok = False
    return {"mysql": mysql_ok, "mongodb": mongo_client.ping()}


@app.get("/api/overview")
def overview(user=Depends(current_user)):
    result = {"inventory": [], "signals": [], "recalls": [], "warnings": []}
    jobs = []
    if user["role"] in {ADMIN, PHARMACIST}:
        jobs.append(("inventory", sql_service.get_inventory_stock_overview))
    if user["role"] == ADMIN:
        jobs.extend([("signals", mongo_service.execute_safety_signal_detection_pipeline),
                     ("recalls", sql_service.get_recall_audits)])
    for name, job in jobs:
        try:
            result[name] = job()
        except Exception:
            result["warnings"].append(f"{name.title()} is temporarily unavailable.")
    return result


@app.get("/api/medicines")
def medicines(user=Depends(current_user)):
    return sql_service.get_all_medicines()


@app.get("/api/batches")
def batches(medicine_id: int | None = None, only_active: bool = False, user=Depends(current_user)):
    return sql_service.get_batches(medicine_id, only_active)


@app.get("/api/hospitals")
def hospitals(user=Depends(current_user)):
    return sql_service.get_hospitals()


@app.get("/api/inventory")
def inventory(user=Depends(access(ADMIN, PHARMACIST))):
    return sql_service.get_inventory_stock_overview()


@app.post("/api/adverse-reports", status_code=201)
def adverse_report(payload: AdverseReportCreate, request: Request, user=Depends(access(ADMIN, DOCTOR, PHARMACIST))):
    data = payload.model_dump()
    med = next((m for m in sql_service.get_all_medicines() if m["medicine_id"] == payload.medicine_id), None)
    if not med:
        raise HTTPException(422, "Choose a registered medicine.")
    data["medicine_name"] = med["commercial_name"]
    data["submitted_by"] = {key: user[key] for key in ("user_id", "username", "full_name", "role")}
    key = request.headers.get("Idempotency-Key")
    if key and (len(key) > 100 or len(key) < 8):
        raise HTTPException(422, "Use a valid submission key.")
    data["submission_key"] = hashlib.sha256(f"{user['user_id']}:{key}".encode()).hexdigest() if key else None
    reference = (payload.case_reference or "").strip()
    data["case_reference"] = reference or None
    data["case_key"] = hashlib.sha256(f"{user['user_id']}:{reference.casefold()}".encode()).hexdigest() if reference else None
    return {"report_id": mongo_service.insert_adverse_report(data)}


@app.post("/api/inventory/import")
def import_csv(file: UploadFile, user=Depends(access(ADMIN, PHARMACIST))):
    content = file.file.read(2 * 1024 * 1024 + 1)
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(413, "Use a CSV file smaller than 2 MB.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(422, "Save your CSV with UTF-8 encoding.")
    count, errors = report_generator.ingest_batches_from_csv(io.StringIO(text))
    if errors:
        # Row errors may contain database internals: only expose safe validation lines.
        safe_errors = [e if e.startswith("Row ") else "No rows were saved. Check the file and try again." for e in errors]
        return JSONResponse({"count": 0, "errors": safe_errors}, status_code=422)
    return {"count": count, "errors": []}


class Dispatch(BaseModel):
    batch_number: str
    hospital_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=100000)
    dispatch_date: date


class Receipt(BaseModel):
    model_config = {"str_strip_whitespace": True}
    batch_number: str
    quantity: int = Field(gt=0, le=1000000)
    receipt_date: date
    reference: str = Field(min_length=3, max_length=100)


@app.post("/api/inventory/receipts", status_code=201)
def receive_stock(payload: Receipt, user=Depends(access(ADMIN, PHARMACIST))):
    return sql_service.receive_stock(payload.batch_number, payload.quantity, payload.receipt_date.isoformat(), payload.reference.strip(), user["username"])


@app.post("/api/inventory/dispatch", status_code=201)
def dispatch(payload: Dispatch, user=Depends(access(ADMIN, PHARMACIST))):
    sql_service.dispatch_batch_to_hospital(payload.batch_number, payload.hospital_id,
                                         payload.quantity, payload.dispatch_date.isoformat())
    return {"message": "Stock dispatched successfully."}


@app.get("/api/signals")
def signals(min_severity: float = Query(3, ge=1, le=5), min_incidents: int = Query(2, ge=1, le=10), window_days: int = Query(0, ge=0, le=365),
            user=Depends(access(ADMIN))):
    return mongo_service.execute_safety_signal_detection_pipeline(min_severity, min_incidents, window_days)


class PatternReview(BaseModel):
    model_config = {"str_strip_whitespace": True}
    medicine_key: str = Field(min_length=1, max_length=170)
    symptom: str = Field(min_length=2, max_length=100)
    window_days: int = Field(ge=0, le=365)
    revision: str = Field(min_length=64, max_length=64)
    status: str = Field(pattern="^(REVIEWED|CLOSED)$")
    notes: str = Field(min_length=5, max_length=1000)


@app.post("/api/signal-reviews")
def review_pattern(payload: PatternReview, user=Depends(access(ADMIN))):
    return mongo_service.review_pattern(payload.medicine_key, payload.symptom, payload.window_days,
                                       payload.revision, payload.status, payload.notes, user)


@app.get("/api/clinical-search")
def search(q: str = Query("", max_length=200), user=Depends(access(ADMIN))):
    return mongo_service.search_clinical_notes_text(q)


@app.get("/api/case-reviews")
def case_reviews(page: int = Query(1, ge=1), user=Depends(access(ADMIN))):
    return mongo_service.get_case_review_queue(page)


class CaseReview(BaseModel):
    model_config = {"str_strip_whitespace": True}
    report_id: str = Field(min_length=3, max_length=100)
    status: str = Field(pattern="^(REVIEWED|FOLLOW_UP)$")
    notes: str = Field(min_length=5, max_length=1000)


@app.post("/api/case-reviews")
def review_case(payload: CaseReview, user=Depends(access(ADMIN))):
    return mongo_service.review_case(payload.report_id, payload.status, payload.notes, user)


@app.get("/api/recalls")
def recalls(user=Depends(access(ADMIN))):
    return sql_service.get_recall_audits()


@app.get("/api/quarantine")
def quarantine(user=Depends(access(ADMIN))):
    return sql_service.get_high_risk_quarantine_trace()


class Recall(BaseModel):
    batch_number: str = Field(min_length=3)
    reason: str = Field(min_length=5, max_length=255)


@app.post("/api/recalls", status_code=201)
def recall(payload: Recall, user=Depends(access(ADMIN))):
    return sql_service.execute_emergency_recall(payload.batch_number, payload.reason, user["full_name"])


@app.get("/api/exports/sample.csv")
def sample(user=Depends(access(ADMIN, PHARMACIST))):
    return FileResponse(config.data_dir / "sample_batches.csv", filename="sample_batches.csv", media_type="text/csv")


@app.get("/api/exports/quarantine.csv")
def csv_export(user=Depends(access(ADMIN))):
    csv = report_generator.generate_csv_quarantine_manifest(sql_service.get_high_risk_quarantine_trace(),
                                                            sql_service.get_recall_audits())
    return Response(csv, media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="quarantine_manifest.csv"'})


@app.get("/api/exports/audit.pdf")
def pdf_export(user=Depends(access(ADMIN))):
    filename = f"audit-{secrets.token_hex(16)}.pdf"
    path = report_generator.generate_pdf_recall_manifest(sql_service.get_high_risk_quarantine_trace(),
                                                       sql_service.get_recall_audits(), filename)
    return FileResponse(path, filename="Safety_Audit_Recall_Manifest.pdf", media_type="application/pdf",
                        background=BackgroundTask(Path(path).unlink, missing_ok=True))


frontend = config.base_dir / "frontend" / "dist"
if frontend.exists():
    app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "API endpoint not found.")
        candidate = (frontend / path).resolve()
        if candidate.is_relative_to(frontend.resolve()) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(frontend / "index.html", headers={"Cache-Control": "no-cache"})
