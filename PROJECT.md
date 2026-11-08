# Project: Islamic Tawbah App (Islamisk Opgørelse & Anger App)

## Architecture
- **Backend**: Python FastAPI with SQLite (WAL mode), Pydantic v2 schemas for strict contract enforcement, and an async RESTful API.
- **Frontend**: Lightweight Semantic SPA (HTML5, modular ES6 JavaScript, responsive modern CSS) served directly by FastAPI static mount. Zero build toolchain dependencies, instant hot reload, native `MediaRecorder` audio recording.
- **Islamic Engine**: Dual-engine architecture:
  1. *Online Mode*: LLM client with structured JSON output enforcing strict Pydantic schemas.
  2. *Deterministic Rule-Based Expert Engine (Offline / Development Mode)*: Pure Python rule-based expert system grounded in Ahlus-Sunnah wal-Jama'ah jurisprudence, guaranteeing 100% reliable, zero-API-key realistic demonstration responses for all 10 confession scenarios and edge cases.
- **Audio Pipeline**: Browser MediaRecorder -> FastAPI endpoint -> Whisper API (online) with transparent fallback to local `faster-whisper` and deterministic mock transcriber (development mode).
- **Core Knowledge Base (RAG)**: Immutable curated JSON datasets (`quran.json`, `hadith.json`, `duas.json`, `fiqh_rules.json`) strictly preventing hallucination of religious texts.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | SQLite Database & Schema | SQLite WAL mode database with User, Confession, Incident, ActionItem, and Journal models | M1 | Survey 3 |
| 2 | Auth & Data Isolation | Session tokens, password hashing, and strict user data isolation (`WHERE user_id = :current_user`) | M1 | Survey 1, 3 |
| 3 | Per-Item Deletion & Wipe | Granular deletion of individual confessions, actions, journal entries, and panic data wipe | M1 | Survey 1 |
| 4 | Curated Quran Knowledge Base | Curated authentic Quranic verses with Arabic Uthmani text, Danish translation, Surah/Ayah | M1 | Survey 2 |
| 5 | Curated Hadith Knowledge Base | Authentic Hadith from Bukhari, Muslim, and the 4 Sunan with collection, number, grading, Arabic & Danish | M1 | Survey 2 |
| 6 | Curated Authentic Duas | Authentic Duas (Sayyid al-Istighfar, Yunus, etc.) with Arabic text, transliteration, Danish meaning | M1 | Survey 2 |
| 7 | Anti-Hallucination RAG Service | Deterministic evidence retrieval and strict citation verification against canonical database | M1 | Survey 2 |
| 8 | Multi-Sin Incident Splitting | Segmentation of compound confessions into discrete atomic incident objects | M2 | Survey 2 |
| 9 | Rights Classification Engine | Classification of sins into `huqooq_allah`, `huqooq_al_ibad`, or `both` | M2 | Survey 2, 3 |
| 10 | Core Tawbah Conditions (Allah) | Enforcement of 3 conditions: cessation (`iqla'`), remorse (`nadam`), resolve never to return (`azm`) | M2 | Survey 2 |
| 11 | Restitution Engine (People) | Enforcement of 4th condition: *radd al-mazalim* (property return, compensation, forgiveness) | M2 | Survey 2, 3 |
| 12 | Apology & Disclosure Rules | Fiqh logic: direct apology if victim knows vs dua/charity if disclosure causes greater fitnah | M2 | Survey 2, 3 |
| 13 | Anonymous Restitution Engine | Guidance on returning usurped property/funds anonymously without self-incrimination | M2 | Survey 2, 3 |
| 14 | Complete JSON Schema (17 fields) | Pydantic model and JSON schema covering all 17 required keys | M2 | Survey 2, 3 |
| 15 | Scholarly Disagreement Engine | Transparent disclosure of classical differences of opinion (*ikhtilaf*) without dogmatic bias | M2 | Survey 2 |
| 16 | Scholar Consultation Flag | Automated trigger for complex legal, criminal, domestic, or severe cases | M2 | Survey 2 |
| 17 | Mercy & Hope Balance Engine | Non-judgmental Danish reflection instilling hope in Allah's limitless forgiveness | M2 | Survey 2 |
| 18 | Deterministic Fallback Engine | 100% offline rule-based expert engine generating realistic analysis for development mode | M2 | Survey 3 |
| 19 | Voice Upload & Validation | Audio ingestion endpoint with MIME (`audio/webm`, `audio/wav`, `audio/mp4`) and size checks | M3 | Survey 1, 3 |
| 20 | Speech-to-Text Pipeline | Whisper API transcriber with local `faster-whisper` and deterministic mock fallback | M3 | Survey 3 |
| 21 | Confession REST Endpoints | API endpoints for submitting text/voice confessions and retrieving past assessments | M3 | Survey 3 |
| 22 | Action Item REST Endpoints | API endpoints for toggling checklist status (Wajib/Mustahabb) with persistence | M3 | Survey 1, 3 |
| 23 | Repentance Journal API | API endpoints for creating, reading, and deleting personal reflections (*Muhasabah*) | M3 | Survey 1 |
| 24 | Design System & Tokens | CSS design tokens: Dark Forest Green (`#16382B`), Sand/Off-White (`#FBF9F5`), Subtle Gold (`#C29B38`) | M4 | Survey 1 |
| 25 | 6-Page Navigation Framework | Responsive header and bottom navigation for Hjem, Ny opgørelse, Mine handlinger, Historik, Viden, Indstillinger | M4 | Survey 1 |
| 26 | Voice Confession Interface | Browser MediaRecorder: record, pause, resume, playback scrub, delete/rerecord | M4 | Survey 1 |
| 27 | Explicit Consent Guard & Modal | Mandatory affirmative consent checkbox and expandable Danish privacy & data handling modal | M4 | Survey 1 |
| 28 | Text Confession Editor | Auto-resizing textarea with Danish character support, live counter, and draft autosave | M4 | Survey 1 |
| 29 | Private Dashboard UI | Overview KPI cards (completed vs outstanding actions, rights breakdown), recent assessments | M4 | Survey 1 |
| 30 | Repentance Journal UI | Clean, private interface for recording and reviewing spiritual reflections | M4 | Survey 1 |
| 31 | Interactive Result Page | Incident cards, dual classification badges, and structured Danish guidance | M4 | Survey 1 |
| 32 | Interactive Action Checklist UI | Numbered interactive checkboxes (Wajib vs Mustahabb) with instant state toggle and persistence | M4 | Survey 1 |
| 33 | Restitution & Apology Drawers | Expandable UI cards with step-by-step guidance on returning money and safe apologies | M4 | Survey 1 |
| 34 | Quran, Hadith & Dua Cards | Dignified cards with Arabic vocalized text (`Amiri`), Danish translation, source, and grading | M4 | Survey 1 |
| 35 | Final Uplifting Reminder UI | Calm, reassuring closing card preventing spiritual despair | M4 | Survey 1 |
| 36 | Islamic Knowledge Browser UI | Searchable directory explaining Tawbah conditions, rights of people, and authentic Duas | M4 | Survey 1 |
| 37 | Settings & Privacy UI | User preferences, data management, and "Nulstil al historik og slet data" panic button | M4 | Survey 1 |
| 38 | Automated CLI Test Runner | Standalone test runner (`python tests/run_tests.py`) with zero external test dependencies | M5 | Survey 3 |
| 39 | 10 Confession Scenarios Suite | Comprehensive automated tests for all 10 required confession scenarios from Section 13 | M5 | Survey 3 |
| 40 | Schema & Rights Boundary Tests | Unit tests verifying Pydantic schema adherence and accurate rights classification | M5 | Survey 3 |
| 41 | Adversarial Coverage Hardening | Tier 5 challenger-driven tests verifying edge cases, audio corruptions, and security boundaries | M5 | Project Pattern |

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Core Backend Data, Auth & Knowledge Base | Database models, SQLite pool, user authentication, data isolation, per-item deletion, canonical Quran/Hadith/Dua JSON datasets, and anti-hallucination RAG service. | none | DONE |
| M2 | Islamic Analysis Engine & Rule-Based Expert System | Multi-sin incident splitter, rights classifier, 4 conditions of Tawbah engine, apology & restitution jurisprudence, scholarly disagreement engine, Pydantic schema validation (17 keys), and 100% offline deterministic fallback engine. | M1 | DONE |
| M3 | Voice Transcription Pipeline & REST API | Audio file validation, Whisper API + mock fallback transcriber, confession intake endpoints, action checklist persistence endpoints, and journal endpoints. | M1, M2 | DONE |
| M4 | Frontend Web Application & Responsive UI | Single-page application shell, Forest Green/Sand/Gold design system, 6 core pages, voice recorder with playback and explicit consent, text editor, dashboard, and interactive result page with persistent checklist. | M1, M2, M3 | DONE |
| M5 | Final Milestone: Full E2E Test Suite & Adversarial Hardening | Phase 1: 100% pass of E2E test suite (Tiers 1-4, verifying all 10 required confession scenarios). Phase 2: Adversarial coverage hardening (Tier 5). | M1, M2, M3, M4 | DONE |

## Parallel Track: E2E Testing Track
- **Test Orchestrator**: Runs in parallel with Implementation Track.
- **Scope**: Requirements-driven, opaque-box E2E test suite covering Tiers 1-4.
- **Output**: `TEST_INFRA.md` and `TEST_READY.md`.

## Interface Contracts

### 1. Analysis Engine Schema Contract (`app/schemas.py`)
```python
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class QuranReference(BaseModel):
    surah: str
    ayah: int
    arabic_text: str
    danish_translation: str
    explanation: str

class HadithReference(BaseModel):
    collection: str
    hadith_number: str
    authenticity_grading: str
    arabic_text: Optional[str] = None
    danish_translation: str
    explanation: str

class RecommendedDua(BaseModel):
    title: str
    arabic_text: str
    transliteration: str
    danish_translation: str
    source: str
    context: str

class ActionItemSchema(BaseModel):
    id: str
    category: Literal["wajib", "mustahabb"]
    description: str
    explanation: str
    target_party: Optional[str] = None
    completed: bool = False

class IncidentSchema(BaseModel):
    incident_id: str
    incident_title: str
    sin_classification: Literal["huqooq_allah", "huqooq_al_ibad", "both"]
    description: str
    affected_parties: List[str]
    allah_rights: List[str]
    people_rights: List[str]
    required_actions: List[ActionItemSchema]
    recommended_actions: List[ActionItemSchema]
    apology_guidance: Optional[str] = None
    restitution_guidance: Optional[str] = None

class AnalysisResultSchema(BaseModel):
    incident_summary: str
    incidents: List[IncidentSchema]
    sin_classification: Literal["huqooq_allah", "huqooq_al_ibad", "both"]
    allah_rights: List[str]
    people_rights: List[str]
    affected_parties: List[str]
    severity_explanation: str
    required_actions: List[ActionItemSchema]
    recommended_actions: List[ActionItemSchema]
    apology_guidance: Optional[str] = None
    restitution_guidance: Optional[str] = None
    quran_references: List[QuranReference]
    hadith_references: List[HadithReference]
    recommended_duas: List[RecommendedDua]
    scholarly_disagreement: Optional[str] = None
    confidence_level: Literal["high", "medium", "low"]
    scholar_consultation_required: bool
    final_reminder: str
```

### 2. Confession REST API Endpoints
- `POST /api/confessions/text`: Accepts `{"text": str, "consent": bool}`. Returns `AnalysisResultSchema` + `confession_id`.
- `POST /api/confessions/voice`: Accepts `multipart/form-data` with `audio` file and `consent=true`. Returns transcription and `AnalysisResultSchema`.
- `GET /api/confessions`: Returns user's past confession summaries.
- `GET /api/confessions/{id}`: Returns full assessment for a confession.
- `DELETE /api/confessions/{id}`: Granular deletion of a confession and its incidents.
- `PATCH /api/actions/{action_id}`: Accepts `{"completed": bool}`. Persists toggle status.
- `GET /api/journal`: Returns list of journal entries.
- `POST /api/journal`: Accepts `{"reflection": str, "tags": List[str]}`. Creates journal entry.
- `DELETE /api/journal/{id}`: Deletes journal entry.
- `POST /api/account/wipe`: Wipes all confessions, actions, and journal entries for the current user.

## Code Layout
```
islamic_tawbah_app/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application entrypoint
│   ├── config.py                   # App settings and fallback flags
│   ├── database.py                 # SQLite WAL connection and migration init
│   ├── models.py                   # SQLAlchemy / SQLite database entities
│   ├── schemas.py                  # Pydantic v2 data contracts
│   ├── auth/                       # Password hashing and session management
│   ├── engine/                     # Islamic Analysis Engine
│   │   ├── analyzer.py             # Orchestrator switching LLM and Rule Engine
│   │   ├── rule_engine.py          # Deterministic expert system (offline fallback)
│   │   ├── incident_splitter.py    # Segmentation of compound confessions
│   │   ├── classifier.py           # Huqooq Allah vs Huqooq al-Ibad classification
│   │   └── rag_service.py          # Evidence retrieval and anti-hallucination verification
│   ├── audio/                      # Audio upload validation & transcription pipeline
│   └── knowledge/                  # Curated authentic religious datasets (JSON)
│       ├── quran.json
│       ├── hadith.json
│       ├── duas.json
│       └── fiqh_rules.json
├── frontend/                       # Semantic SPA
│   ├── index.html
│   ├── css/
│   │   ├── variables.css
│   │   ├── layout.css
│   │   └── components.css
│   └── js/
│       ├── app.js
│       ├── api.js
│       ├── audio_recorder.js
│       └── ui.js
├── tests/                          # Automated Test Suite
│   ├── run_tests.py                # Standalone CLI test runner
│   ├── test_scenarios.py           # 10 Required Confession Scenarios
│   ├── test_schema_compliance.py   # R2 JSON schema tests
│   ├── test_rights_classification.py# Fiqh rights boundary tests
│   └── test_audio_pipeline.py      # Audio validation and mock fallback tests
├── data/                           # SQLite database storage directory
├── requirements.txt
└── README.md
```
