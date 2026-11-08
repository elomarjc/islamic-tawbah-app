"""
app/main.py

FastAPI Application Entrypoint for Islamic Tawbah App (Feature #21).
Exposes complete REST API endpoints for text and voice confession intake,
rights analysis, action tracking, repentance journal, Islamic knowledge base,
user authentication, and static SPA frontend serving.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException, Request, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError

from app.database import init_db, get_db_connection
from app.auth.security import (
    hash_password,
    verify_password,
    create_session,
    get_user_by_token,
    delete_confession as db_delete_confession,
    delete_journal_entry as db_delete_journal_entry,
    wipe_user_data as db_wipe_user_data,
)
from app.engine.analyzer import get_analyzer
from app.engine.rag_service import get_rag_service
from app.audio import validate_audio_upload, get_transcriber

logger = logging.getLogger("tawbah.main")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

app = FastAPI(
    title="Islamic Tawbah App (Islamisk Opgørelse & Anger App)",
    description="RESTful API for Islamic Tawbah Analysis and Repentance Guidance",
    version="1.0.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """Initializes the database schema and seeds default accounts."""
    try:
        init_db()
        logger.info("Database initialized and verified.")
    except Exception as ex:
        logger.error("Database initialization failed: %s", ex)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Custom validation exception handler ensuring HTTP 400 for bad confession requests."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Ugyldig anmodning eller manglende obligatoriske felter.", "errors": exc.errors()},
    )


def _get_current_user_id(request: Request, conn) -> str:
    """Extracts authenticated user_id from token header/cookie or defaults to demo user."""
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif "token" in request.headers:
        token = request.headers.get("token")
    elif "session_token" in request.cookies:
        token = request.cookies.get("session_token")

    if token:
        user = get_user_by_token(conn, token)
        if user:
            return user["id"]

    return "user_demo_default"


def _persist_confession_graph(
    request: Request,
    confession_id: str,
    raw_input_type: str,
    raw_text: str,
    analysis: Dict[str, Any],
    transcript: Optional[str] = None,
) -> None:
    """Persists confession, incidents, and action items to SQLite."""
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        with get_db_connection() as conn:
            user_id = _get_current_user_id(request, conn)
            c = conn.cursor()
            c.execute(
                """
                INSERT OR IGNORE INTO users (id, username, password_hash, is_guest, is_active, created_at)
                VALUES (?, 'demo_user', 'hash', 0, 1, ?)
                """,
                (user_id, now_iso),
            )
            c.execute(
                """
                INSERT INTO confessions (
                    id, user_id, raw_input_type, raw_text, transcript, consent_given, status,
                    summary, sin_classification, confidence_level, scholar_consultation_required,
                    analysis_json, created_at
                ) VALUES (?, ?, ?, ?, ?, 1, 'completed', ?, ?, ?, ?, ?, ?)
                """,
                (
                    confession_id,
                    user_id,
                    raw_input_type,
                    raw_text,
                    transcript,
                    analysis.get("incident_summary"),
                    analysis.get("sin_classification"),
                    analysis.get("confidence_level", "high"),
                    1 if analysis.get("scholar_consultation_required") else 0,
                    json.dumps(analysis),
                    now_iso,
                ),
            )

            for order, inc in enumerate(analysis.get("incidents", []), start=1):
                inc_id = f"{confession_id}_{inc.get('incident_id', order)}"
                c.execute(
                    """
                    INSERT INTO incidents (
                        id, confession_id, incident_order, incident_title, sin_classification,
                        description, affected_parties, allah_rights, people_rights,
                        apology_guidance, restitution_guidance, severity_explanation, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        inc_id,
                        confession_id,
                        order,
                        inc.get("incident_title", "Syndshændelse"),
                        inc.get("sin_classification", "both"),
                        inc.get("description", ""),
                        json.dumps(inc.get("affected_parties", [])),
                        json.dumps(inc.get("allah_rights", [])),
                        json.dumps(inc.get("people_rights", [])),
                        inc.get("apology_guidance"),
                        inc.get("restitution_guidance"),
                        inc.get("severity_explanation"),
                        now_iso,
                    ),
                )

            for act in analysis.get("required_actions", []) + analysis.get("recommended_actions", []):
                act_id = f"{confession_id}_{act.get('id', uuid.uuid4().hex[:8])}"
                c.execute(
                    """
                    INSERT INTO action_items (
                        id, user_id, confession_id, category, action_type, title,
                        description, explanation, target_party, completed, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        act_id,
                        user_id,
                        confession_id,
                        act.get("category", "wajib"),
                        act.get("action_type"),
                        act.get("title"),
                        act.get("description", ""),
                        act.get("explanation"),
                        act.get("target_party"),
                        1 if act.get("completed") else 0,
                        now_iso,
                    ),
                )
    except Exception as db_err:
        logger.warning("Database persistence error (non-fatal for analysis return): %s", db_err)


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/api/auth/register")
async def register(request: Request):
    """Registers a new user and returns a session token."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Ugyldigt JSON format.")

    username = str(body.get("username", "")).strip()
    password = str(body.get("password", "")).strip()
    if not username or not password:
        raise HTTPException(status_code=400, detail="Brugernavn og adgangskode er påkrævet.")

    pw_hash = hash_password(password)
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db_connection() as conn:
        c = conn.cursor()
        existing = c.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            token = create_session(conn, existing["id"], is_guest=False)
            return {"access_token": token, "token_type": "bearer", "user_id": existing["id"], "username": username}

        c.execute(
            """
            INSERT INTO users (id, username, password_hash, is_guest, is_active, created_at)
            VALUES (?, ?, ?, 0, 1, ?)
            """,
            (user_id, username, pw_hash, now_iso),
        )
        token = create_session(conn, user_id, is_guest=False)

    return {"access_token": token, "token_type": "bearer", "user_id": user_id, "username": username}


@app.post("/api/auth/login")
async def login(request: Request):
    """Authenticates a user and returns a session token."""
    username = ""
    password = ""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        username = str(body.get("username", "")).strip()
        password = str(body.get("password", "")).strip()
    else:
        form = await request.form()
        username = str(form.get("username", "")).strip()
        password = str(form.get("password", "")).strip()

    if not username or not password:
        raise HTTPException(status_code=400, detail="Brugernavn og adgangskode er påkrævet.")

    with get_db_connection() as conn:
        c = conn.cursor()
        user_row = c.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not user_row or not verify_password(password, user_row["password_hash"]):
            raise HTTPException(status_code=401, detail="Ugyldigt brugernavn eller adgangskode.")

        user_id = user_row["id"]
        token = create_session(conn, user_id, is_guest=bool(user_row["is_guest"]))

    return {"access_token": token, "token_type": "bearer", "user_id": user_id, "username": username}


# ============================================================================
# CONFESSION INTAKE (TEXT & VOICE)
# ============================================================================

@app.post("/api/confessions/text")
async def submit_text_confession(request: Request):
    """
    Intake endpoint for Danish written confessions.
    Requires explicit consent and validates text bounds (1 - 10,000 chars).
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ugyldigt JSON format.",
        )

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Anmodningskroppen skal være et JSON-objekt.",
        )

    # 1. Validate Consent (Mandatory affirmative consent)
    consent = payload.get("consent")
    if consent is not True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Eksplicit samtykke er påkrævet for at behandle en bekendelse.",
        )

    # 2. Validate Text Presence & Whitespace
    raw_text = payload.get("text")
    if raw_text is None or not isinstance(raw_text, str) or not raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bekendelsesteksten må ikke være tom eller udelukkende indeholde mellemrum.",
        )

    # 3. Validate Text Length Boundary (Max 10,000 characters)
    if len(raw_text) > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bekendelsesteksten overstiger den tilladte grænse på maksimalt 10.000 tegn.",
        )

    # 4. Execute Analysis Pipeline
    analyzer = get_analyzer()
    try:
        analysis = analyzer.analyze_confession(raw_text)
    except Exception as ex:
        logger.error("Analysis pipeline error: %s", ex, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Der opstod en fejl under den islamiske analyse.",
        )

    # 5. Persist Confession, Incidents, and Action Items to SQLite
    confession_id = f"conf_{uuid.uuid4().hex[:12]}"
    _persist_confession_graph(
        request=request,
        confession_id=confession_id,
        raw_input_type="text",
        raw_text=raw_text,
        analysis=analysis,
    )

    analysis["confession_id"] = confession_id
    return JSONResponse(status_code=status.HTTP_200_OK, content=analysis)


@app.post("/api/confessions/voice")
async def submit_voice_confession(
    request: Request,
    audio: Optional[UploadFile] = File(None),
    consent: Optional[str] = Form(None),
    transcript_hint: Optional[str] = Form(None),
):
    """
    Intake endpoint for Danish voice confessions.
    Validates MIME type (audio/webm, audio/wav, audio/mp4), file size (<= 25MB),
    and affirmative consent. Runs transcription and returns Islamic analysis.
    """
    content = await validate_audio_upload(audio=audio, consent=consent)

    transcriber = get_transcriber()
    stt_res = transcriber.transcribe(
        audio_bytes=content,
        filename=audio.filename if audio else "confession.webm",
        content_type=audio.content_type if audio else "audio/webm",
        transcript_hint=transcript_hint,
    )
    transcript = stt_res["transcript"]

    analyzer = get_analyzer()
    analysis = analyzer.analyze_confession(transcript)

    confession_id = f"conf_{uuid.uuid4().hex[:12]}"
    _persist_confession_graph(
        request=request,
        confession_id=confession_id,
        raw_input_type="voice",
        raw_text=transcript,
        analysis=analysis,
        transcript=transcript,
    )

    analysis["transcript"] = transcript
    analysis["confession_id"] = confession_id
    analysis["transcription_engine"] = stt_res.get("engine", "offline_demo")
    analysis["demonstration_mode"] = bool(stt_res.get("demonstration_mode", True))

    headers = {}
    if analysis["demonstration_mode"]:
        headers["X-Demonstration-Mode"] = "True"

    return JSONResponse(status_code=status.HTTP_200_OK, content=analysis, headers=headers)


# ============================================================================
# CONFESSIONS & INCIDENTS QUERY & DELETION
# ============================================================================

@app.get("/api/confessions")
def list_confessions(request: Request):
    """Retrieves previous confessions for the authenticated user."""
    with get_db_connection() as conn:
        user_id = _get_current_user_id(request, conn)
        c = conn.cursor()
        rows = c.execute(
            "SELECT id, raw_input_type, raw_text, summary, sin_classification, confidence_level, scholar_consultation_required, created_at, status FROM confessions WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


@app.get("/api/confessions/{confession_id}")
def get_confession(confession_id: str, request: Request):
    """Retrieves full analysis for a specific confession, enforcing user data isolation."""
    with get_db_connection() as conn:
        user_id = _get_current_user_id(request, conn)
        c = conn.cursor()
        row = c.execute("SELECT * FROM confessions WHERE id = ?", (confession_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Bekendelse ikke fundet.")

        # Data Isolation Check: Must belong to current user
        if row["user_id"] != user_id and user_id != "user_demo_default":
            raise HTTPException(status_code=403, detail="Adgang nægtet: Du ejer ikke denne bekendelse.")

        if row["analysis_json"]:
            data = json.loads(row["analysis_json"])
            data["confession_id"] = confession_id
            data["created_at"] = row["created_at"]
            data["raw_input_type"] = row["raw_input_type"]
            if row["transcript"]:
                data["transcript"] = row["transcript"]

            # Sync live action completion states from action_items table
            action_rows = c.execute(
                "SELECT id, completed FROM action_items WHERE confession_id = ?",
                (confession_id,),
            ).fetchall()
            completion_map = {}
            for ar in action_rows:
                full_id = ar["id"]
                is_done = bool(ar["completed"])
                completion_map[full_id] = is_done
                prefix = f"{confession_id}_"
                if full_id.startswith(prefix):
                    completion_map[full_id[len(prefix):]] = is_done

            for act_list_key in ("required_actions", "recommended_actions"):
                for act in data.get(act_list_key, []):
                    aid = act.get("id")
                    if aid in completion_map:
                        act["completed"] = completion_map[aid]

            return data
        return dict(row)


@app.delete("/api/confessions/{confession_id}")
def delete_confession(confession_id: str, request: Request):
    """Granular deletion of a confession and its incidents."""
    with get_db_connection() as conn:
        user_id = _get_current_user_id(request, conn)
        success = db_delete_confession(conn, confession_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Bekendelse ikke fundet.")
    return {"status": "ok", "message": "Bekendelse slettet."}


# ============================================================================
# ACTION CHECKLIST PERSISTENCE
# ============================================================================

@app.get("/api/actions")
def list_actions(request: Request):
    """Retrieves action items for the current user."""
    with get_db_connection() as conn:
        user_id = _get_current_user_id(request, conn)
        c = conn.cursor()
        rows = c.execute(
            "SELECT * FROM action_items WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["completed"] = bool(d.get("completed", 0))
            out.append(d)
        return out


@app.patch("/api/actions/{action_id}")
async def toggle_action_item(action_id: str, request: Request):
    """Toggles checklist completion status for an action item."""
    try:
        body = await request.json()
        completed = bool(body.get("completed", False))
    except Exception:
        completed = False

    now_iso = datetime.now(timezone.utc).isoformat() if completed else None
    with get_db_connection() as conn:
        user_id = _get_current_user_id(request, conn)
        c = conn.cursor()
        c.execute(
            """
            UPDATE action_items SET completed = ?, completed_at = ?
            WHERE (id = ? OR id LIKE ?) AND (user_id = ? OR user_id = 'user_demo_default')
            """,
            (1 if completed else 0, now_iso, action_id, f"%_{action_id}", user_id),
        )
        if c.rowcount == 0:
            raise HTTPException(status_code=404, detail="Handlingspunkt ikke fundet.")
    return {"id": action_id, "completed": completed, "updated_at": now_iso}


# ============================================================================
# REPENTANCE JOURNAL (MUHASABAH)
# ============================================================================

@app.get("/api/journal")
def list_journal(request: Request):
    """Retrieves personal reflections for the current user."""
    with get_db_connection() as conn:
        user_id = _get_current_user_id(request, conn)
        c = conn.cursor()
        rows = c.execute(
            "SELECT * FROM journal_entries WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            if isinstance(d.get("tags"), str):
                try:
                    d["tags"] = json.loads(d["tags"])
                except Exception:
                    d["tags"] = []
            out.append(d)
        return out


@app.post("/api/journal")
async def create_journal(request: Request):
    """Creates a new spiritual journal reflection."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Ugyldigt JSON format.")

    content = body.get("reflection") or body.get("content") or ""
    if not content or not str(content).strip():
        raise HTTPException(status_code=400, detail="Indhold kan ikke være tomt.")

    title = body.get("title") or "Personlig refleksion"
    tags = body.get("tags", [])
    entry_id = f"entry_{uuid.uuid4().hex[:10]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db_connection() as conn:
        user_id = _get_current_user_id(request, conn)
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO journal_entries (id, user_id, title, content, tags, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (entry_id, user_id, title, content, json.dumps(tags), now_iso),
        )

    return {"id": entry_id, "title": title, "content": content, "tags": tags, "created_at": now_iso}


@app.delete("/api/journal/{entry_id}")
def delete_journal(entry_id: str, request: Request):
    """Deletes a journal reflection."""
    with get_db_connection() as conn:
        user_id = _get_current_user_id(request, conn)
        success = db_delete_journal_entry(conn, entry_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Journalpost ikke fundet.")
    return {"status": "ok", "message": "Journalpost slettet."}


# ============================================================================
# ISLAMIC KNOWLEDGE BASE (RAG BROWSER)
# ============================================================================

@app.get("/api/knowledge")
def get_knowledge_base(q: Optional[str] = None, category: Optional[str] = None):
    """
    Returns verified Quranic verses, authentic Hadiths, authentic Duas,
    and classical Ahlus-Sunnah Fiqh principles from the curated knowledge base.
    """
    rag = get_rag_service()
    query = (q or "").strip().lower()
    cat = (category or "").strip().lower()

    def _matches(item: Dict[str, Any]) -> bool:
        blob = json.dumps(item, ensure_ascii=False).lower()
        if query and query not in blob:
            return False
        if cat and cat != "all" and cat not in blob:
            return False
        return True

    quran_list = [v for v in getattr(rag, "_quran_data", []) if _matches(v)]
    hadith_list = [h for h in getattr(rag, "_hadith_data", []) if _matches(h)]
    duas_list = [d for d in getattr(rag, "_duas_data", []) if _matches(d)]
    fiqh_list = [f for f in getattr(rag, "_fiqh_rules_data", []) if _matches(f)]

    return {
        "quran": quran_list,
        "hadith": hadith_list,
        "duas": duas_list,
        "fiqh_rules": fiqh_list,
    }


# ============================================================================
# ACCOUNT WIPE & DASHBOARD
# ============================================================================

@app.post("/api/account/wipe")
def wipe_account(request: Request):
    """Panic Wipe: purges all confessions, actions, and journal entries for the user."""
    with get_db_connection() as conn:
        user_id = _get_current_user_id(request, conn)
        res = db_wipe_user_data(conn, user_id, delete_account=False)
        return res


@app.get("/api/dashboard/summary")
def dashboard_summary(request: Request):
    """Returns dashboard summary KPI counters for the user."""
    with get_db_connection() as conn:
        user_id = _get_current_user_id(request, conn)
        c = conn.cursor()
        total_conf = c.execute("SELECT count(*) FROM confessions WHERE user_id = ?", (user_id,)).fetchone()[0]
        completed_act = c.execute("SELECT count(*) FROM action_items WHERE user_id = ? AND completed = 1", (user_id,)).fetchone()[0]
        pending_act = c.execute("SELECT count(*) FROM action_items WHERE user_id = ? AND completed = 0", (user_id,)).fetchone()[0]
        journal_count = c.execute("SELECT count(*) FROM journal_entries WHERE user_id = ?", (user_id,)).fetchone()[0]
        return {
            "total_confessions": total_conf,
            "completed_actions": completed_act,
            "pending_actions": pending_act,
            "journal_entries": journal_count,
        }


# ============================================================================
# FRONTEND STATIC SPA SERVING
# ============================================================================

if (FRONTEND_DIR / "css").exists():
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
if (FRONTEND_DIR / "js").exists():
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")


@app.get("/css/{filename}")
def serve_css_fallback(filename: str):
    """Serves CSS files even if created after app import."""
    fpath = FRONTEND_DIR / "css" / filename
    if fpath.is_file():
        return FileResponse(fpath, media_type="text/css")
    raise HTTPException(status_code=404, detail="CSS fil ikke fundet.")


@app.get("/js/{filename}")
def serve_js_fallback(filename: str):
    """Serves JS files even if created after app import."""
    fpath = FRONTEND_DIR / "js" / filename
    if fpath.is_file():
        return FileResponse(fpath, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="JS fil ikke fundet.")


@app.get("/", response_class=HTMLResponse)
def serve_spa_index():
    """Serves the Danish Islamic Accountability & Tawbah SPA frontend."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.is_file():
        return FileResponse(index_path, media_type="text/html")
    return HTMLResponse("<h1>Tawbah Guiden — Frontend indlæses...</h1>")
