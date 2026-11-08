# Test Infrastructure Specification: Islamic Tawbah App

## 1. Test Philosophy

The testing infrastructure for the Islamic Tawbah App (*Islamisk Opgørelse & Anger App*) is constructed according to five core architectural tenets:

1. **Opaque-Box Requirement-Driven Testing**: Tests interact strictly with public contracts (REST API HTTP endpoints, Pydantic data schemas, and CLI commands) without coupling to private internal implementation methods. Expected behaviors are derived directly from `ORIGINAL_REQUEST.md` (R1–R5), classical Ahlus-Sunnah wal-Jama'ah jurisprudence, and `PROJECT.md` specifications.
2. **Zero-Toolchain Dependency Harness**: The test suite executes directly through the Python standard library (`unittest`), requiring zero specialized test frameworks to run, while maintaining full discovery compatibility with `pytest`. It features a custom ANSI-colored CLI test runner (`python tests/run_tests.py`) providing tier filtering, failure isolation, and exit codes for CI/CD integration.
3. **Progressive Testability & Graceful Readiness**: Test modules are designed with progressive testability. As milestones advance (M1 through M5), tests cleanly execute against implemented modules or report clear readiness status, preventing catastrophic collection crashes during parallel multi-agent development.
4. **Deterministic Verification (Zero External API Dependency)**: All theological scenarios, audio pipeline validations, and rights classifications can be verified completely offline using the deterministic rule-based expert engine and mock speech transcriber. No external LLM or Whisper API keys are required for automated test execution.
5. **Adversarial & Boundary Rigor**: Beyond standard happy paths, the suite tests Danish diacritics (`æ, ø, å`), SQL injection strings, cross-user isolation boundaries, maximum text limits (10,000 characters), unsupported audio formats, and fiqh edge cases (e.g., prohibition of public sin confession under *Sitr*).

---

## 2. 4-Tier Test Architecture

The test suite is structured into four progressive tiers:

- **Tier 1: Feature Coverage in Isolation**:
  - Independent unit and contract verification for individual features.
  - Pydantic schema validation across all 17 required JSON fields.
  - Isolated classification of pure *Huqooq Allah* and pure *Huqooq al-Ibad*.
  - Audio MIME type and payload size validation.
  - Canonical knowledge base loading and anti-hallucination reference verification.
  - Personal repentance journal entry creation and deletion.
- **Tier 2: Boundary & Corner Cases**:
  - Empty text, whitespace-only, and maximum-length (10,000 character) confessions.
  - Missing or negative explicit user consent (`consent=False`).
  - Unsupported audio MIME types (`text/plain`, `image/png`, `application/pdf`) and corrupt audio bytes.
  - Danish diacritics (`æ, ø, å, Æ, Ø, Å`), emojis, and special character robustness.
  - Missing fields in JSON payloads and non-existent entity IDs (404 handling).
- **Tier 3: Cross-Feature Interactions & System Contracts**:
  - Compound confessions: multi-sin incident splitting combined with multi-class rights categorization.
  - Interactive action checklist persistence across sessions (toggling status persists in SQLite WAL database).
  - Strict user data isolation: ensuring User A cannot read, toggle, or delete User B's confessions or action items.
  - Account panic wipe (`POST /api/account/wipe`): purging all user records while preserving other accounts.
  - Audio pipeline to Islamic analysis integration: speech-to-text transcript seamlessly analyzed.
- **Tier 4: The 10 Required Confession Scenarios (Section 13 / R5)**:
  - Complete, end-to-end validation of the 10 real-world theological confession scenarios defined in Section 13 and Acceptance Criterion R5.
  - Verifies exact classification, affected parties, mandatory Tawbah conditions, nuanced apology/restitution rulings (anonymous return, fitnah avoidance, public slander retraction, private sitr), and authentic Quran/Hadith citations.

---

## 3. Feature Inventory Test Matrix (41 Features)

| Feature # | Feature Name | Milestone | Test File | Test Tier | Primary Test Method | Verification Strategy |
|---|---|---|---|---|---|---|
| 1 | SQLite Database & Schema | M1 | `tests/test_auth_isolation.py` | Tier 1 | `test_database_schema_initialization` | SQLite tables (User, Confession, Incident, ActionItem, Journal) exist with foreign keys. |
| 2 | Auth & Data Isolation | M1 | `tests/test_auth_isolation.py` | Tier 3 | `test_user_data_isolation_across_accounts` | Confessions and actions of User A return 404/forbidden for User B. |
| 3 | Per-Item Deletion & Wipe | M1 | `tests/test_auth_isolation.py` | Tier 1, 3 | `test_granular_deletion_and_account_wipe` | Deleting single confession removes related incidents/actions; wipe purges all records. |
| 4 | Curated Quran Knowledge Base | M1 | `tests/test_schema_compliance.py` | Tier 1 | `test_quran_canonical_database_integrity` | `quran.json` contains valid Surah, Ayah, Arabic text, and Danish translations. |
| 5 | Curated Hadith Knowledge Base | M1 | `tests/test_schema_compliance.py` | Tier 1 | `test_hadith_canonical_database_integrity` | `hadith.json` contains authentic Sahih Bukhari/Muslim citations with gradings. |
| 6 | Curated Authentic Duas | M1 | `tests/test_schema_compliance.py` | Tier 1 | `test_duas_canonical_database_integrity` | `duas.json` contains authentic Duas with Arabic, transliteration, and Danish translation. |
| 7 | Anti-Hallucination RAG Service | M1 | `tests/test_schema_compliance.py` | Tier 1 | `test_anti_hallucination_citation_verification` | Engine rejects or flags unverified citations not present in canonical datasets. |
| 8 | Multi-Sin Incident Splitting | M2 | `tests/test_rights_classification.py` | Tier 3 | `test_compound_confession_incident_splitting` | Compound confession (e.g. theft + missed prayer) splits into discrete incident objects. |
| 9 | Rights Classification Engine | M2 | `tests/test_rights_classification.py` | Tier 1 | `test_rights_classification_taxonomy` | Correctly assigns `huqooq_allah`, `huqooq_al_ibad`, or `both`. |
| 10 | Core Tawbah Conditions (Allah) | M2 | `tests/test_rights_classification.py` | Tier 1 | `test_core_tawbah_conditions_presence` | Sincere remorse (`nadam`), cessation (`iqla'`), and resolve (`azm`) present in required actions. |
| 11 | Restitution Engine (People) | M2 | `tests/test_rights_classification.py` | Tier 1 | `test_restitution_engine_for_property_rights` | Property usurpation mandates 4th condition: *radd al-mazalim* (restitution). |
| 12 | Apology & Disclosure Rules | M2 | `tests/test_rights_classification.py` | Tier 3 | `test_apology_vs_fitnah_avoidance_rules` | Distinguishes between direct apology and silent expiation when disclosure causes greater fitnah. |
| 13 | Anonymous Restitution Engine | M2 | `tests/test_rights_classification.py` | Tier 3 | `test_anonymous_restitution_guidance` | Provides step-by-step guidance on returning stolen goods anonymously without self-incrimination. |
| 14 | Complete JSON Schema (17 fields) | M2 | `tests/test_schema_compliance.py` | Tier 1 | `test_complete_17_field_schema_compliance` | Pydantic response contains all 17 required keys with exact types. |
| 15 | Scholarly Disagreement Engine | M2 | `tests/test_rights_classification.py` | Tier 1 | `test_scholarly_disagreement_disclosure` | Nuanced cases disclose classical differences of opinion (*ikhtilaf*) transparently. |
| 16 | Scholar Consultation Flag | M2 | `tests/test_rights_classification.py` | Tier 1 | `test_scholar_consultation_flag_trigger` | Complex legal, domestic, or severe cases trigger `scholar_consultation_required: true`. |
| 17 | Mercy & Hope Balance Engine | M2 | `tests/test_schema_compliance.py` | Tier 1 | `test_mercy_and_hope_final_reminder` | Non-judgmental Danish reflection instills hope in Allah's mercy and forbids despair (*qunut*). |
| 18 | Deterministic Fallback Engine | M2 | `tests/test_scenarios.py` | Tier 1 | `test_deterministic_fallback_offline_execution` | Offline expert system produces valid, realistic analysis without external API calls. |
| 19 | Voice Upload & Validation | M3 | `tests/test_audio_pipeline.py` | Tier 1, 2 | `test_voice_upload_mime_and_size_validation` | Accepts WebM, WAV, MP4; rejects invalid MIME types and files > 25MB. |
| 20 | Speech-to-Text Pipeline | M3 | `tests/test_audio_pipeline.py` | Tier 1 | `test_transcription_pipeline_mock_fallback` | Audio upload returns realistic Danish transcript with fallback notice. |
| 21 | Confession REST Endpoints | M3 | `tests/test_schema_compliance.py` | Tier 1 | `test_confession_text_rest_endpoint` | `POST /api/confessions/text` returns confession ID and structured analysis. |
| 22 | Action Item REST Endpoints | M3 | `tests/test_auth_isolation.py` | Tier 1, 3 | `test_action_item_toggle_persistence` | `PATCH /api/actions/{id}` toggles `completed` state and persists to database. |
| 23 | Repentance Journal API | M3 | `tests/test_auth_isolation.py` | Tier 1 | `test_repentance_journal_crud_endpoints` | `POST /api/journal`, `GET /api/journal`, `DELETE /api/journal/{id}` work correctly. |
| 24 | Design System & Tokens | M4 | `tests/test_schema_compliance.py` | Tier 1 | `test_design_system_token_specifications` | Verify frontend CSS defines Forest Green (`#16382B`), Sand (`#FBF9F5`), Gold (`#C29B38`). |
| 25 | 6-Page Navigation Framework | M4 | `tests/test_schema_compliance.py` | Tier 1 | `test_frontend_routes_and_views_structure` | Verify index.html contains the 6 required core view sections in Danish. |
| 26 | Voice Confession Interface | M4 | `tests/test_audio_pipeline.py` | Tier 1 | `test_voice_recorder_interface_contract` | MediaRecorder payload contract matches backend multipart ingestion specification. |
| 27 | Explicit Consent Guard & Modal | M4 | `tests/test_schema_compliance.py` | Tier 2 | `test_confession_submission_requires_explicit_consent` | Submission rejected with 400 Bad Request if `consent` is False or missing. |
| 28 | Text Confession Editor | M4 | `tests/test_schema_compliance.py` | Tier 2 | `test_text_confession_danish_and_length_limits` | Text editor contract accepts Danish text up to 10,000 characters. |
| 29 | Private Dashboard UI | M4 | `tests/test_auth_isolation.py` | Tier 1 | `test_dashboard_kpi_summary_contract` | User summary reflects total confessions, pending actions, and completed actions. |
| 30 | Repentance Journal UI | M4 | `tests/test_auth_isolation.py` | Tier 1 | `test_journal_entry_data_isolation` | Journal reflection interface displays only authenticated user's reflections. |
| 31 | Interactive Result Page | M4 | `tests/test_schema_compliance.py` | Tier 1 | `test_result_page_payload_contract` | Result payload maps directly to incident cards, badges, and action lists. |
| 32 | Interactive Action Checklist UI | M4 | `tests/test_auth_isolation.py` | Tier 3 | `test_checklist_wajib_mustahabb_categorization` | Actions separate into Wajib (mandatory) and Mustahabb (recommended) categories. |
| 33 | Restitution & Apology Drawers | M4 | `tests/test_rights_classification.py` | Tier 1 | `test_restitution_and_apology_drawer_content` | Drawers provide step-by-step guidance for monetary return and safe apologies. |
| 34 | Quran, Hadith & Dua Cards | M4 | `tests/test_schema_compliance.py` | Tier 1 | `test_quran_hadith_dua_card_contract` | Verifies presence of Arabic vocalized text, Danish translation, and source metadata. |
| 35 | Final Uplifting Reminder UI | M4 | `tests/test_schema_compliance.py` | Tier 1 | `test_final_reminder_card_content` | Verifies Danish uplifting message preventing spiritual despair. |
| 36 | Islamic Knowledge Browser UI | M4 | `tests/test_schema_compliance.py` | Tier 1 | `test_knowledge_browser_corpus_contract` | Knowledge base endpoints provide searchable directory of Tawbah conditions. |
| 37 | Settings & Privacy UI | M4 | `tests/test_auth_isolation.py` | Tier 1 | `test_settings_and_privacy_reset_contract` | Panic reset endpoint purges all data with affirmative confirmation. |
| 38 | Automated CLI Test Runner | M5 | `tests/run_tests.py` | Tier 1 | `test_runner_self_verification` | Runner executes all suites, formats ANSI output, and returns exit code 0 or 1. |
| 39 | 10 Confession Scenarios Suite | M5 | `tests/test_scenarios.py` | Tier 4 | `test_scenario_1_through_10` | Full theological verification of all 10 confession scenarios. |
| 40 | Schema & Rights Boundary Tests | M5 | `tests/test_rights_classification.py` | Tier 2 | `test_rights_boundary_edge_cases` | Edge cases on rights classification, Sitr, and fitnah prevention. |
| 41 | Adversarial Coverage Hardening | M5 | `tests/test_schema_compliance.py` | Tier 2, 3 | `test_adversarial_inputs_and_payload_hardening` | Fuzz testing on unicode, Danish diacritics, SQL injection strings, and large payloads. |

---

## 4. Test Runner Invocation (`tests/run_tests.py`)

The test suite is executed using the standalone test runner:

```bash
# Run all test tiers (Tiers 1-4)
python tests/run_tests.py

# Run a specific tier
python tests/run_tests.py --tier 1
python tests/run_tests.py --tier 2
python tests/run_tests.py --tier 3
python tests/run_tests.py --tier 4

# Run only the 10 required confession scenarios (Section 13 / R5)
python tests/run_tests.py --scenarios-only

# Verbose output with timing and test docstrings
python tests/run_tests.py -v

# Fail-fast mode (stops on first failure)
python tests/run_tests.py --failfast

# Run using pytest (fully compatible)
pytest tests/
```

### Exit Codes:
- `0`: All executed tests passed.
- `1`: One or more tests failed or encountered errors.

---

## 5. Real-World Application Scenarios (Tier 4: Section 13 / R5)

The Tier 4 test suite (`tests/test_scenarios.py`) evaluates the application against 10 canonical confession scenarios:

### Scenario 1: Fornærmelse af moderen (Insulting Mother)
- **Input Context**: User confessed shouting, insulting, and being insolent toward their mother during an argument.
- **Sin Classification**: `both` (Huqooq Allah & Huqooq al-Ibad).
- **Affected Parties**: `["Moderen"]`.
- **Mandatory Actions**:
  - Sincere repentance before Allah (Nadam, Iqla', Azm) for violating *Birr al-Walidayn*.
  - Direct, humble in-person apology to mother; kissing her head/hands and seeking her pardon (*Rida*).
  - Explicit rule: No fitnah nuance permits withholding an apology from one's mother.
- **Evidence**: Surah Al-Isra (17:23–24); Sahih al-Bukhari 5971 / Sahih Muslim 85.

### Scenario 2: Tyveri fra faderen (Stealing from Father)
- **Input Context**: User stole 2,000 DKK from father's wallet without knowledge or permission.
- **Sin Classification**: `both` (Huqooq Allah & Huqooq al-Ibad).
- **Affected Parties**: `["Faderen"]`.
- **Mandatory Actions**:
  - Repentance before Allah for theft (*Sariqah*).
  - Mandatory financial restitution of full amount (*Radd al-Mazalim*).
  - **Fiqh Nuance**: If direct confession will destroy familial relations, secret/anonymous restitution (e.g., placing money back in wallet or account) is legally valid. The Hadith *"You and your wealth belong to your father"* does NOT permit stealing.
- **Evidence**: Surah Al-Ma'idah (5:38); Sahih al-Bukhari 2449.

### Scenario 3: Bagtalelse (Backbiting / Ghibah)
- **Input Context**: User spoke ill behind a colleague's back, criticizing their character and competence to coworkers.
- **Sin Classification**: `both` (Huqooq Allah & Huqooq al-Ibad).
- **Affected Parties**: `["Den bagtalte person"]`.
- **Mandatory Actions**:
  - Repentance before Allah for *Ghibah*.
  - **Apology vs. Fitnah Nuance**: If victim already knows, seek direct forgiveness. If victim does NOT know and disclosure will cause pain, anger, or severed ties, disclosure is strictly avoided (Ibn Taymiyyah/Ibn Qayyim ruling). The required expiation (*kaffarah*) is: praise the victim in the same gatherings and make earnest dua and istighfar for them.
- **Evidence**: Surah Al-Hujurat (49:12); Sahih Muslim 2589.

### Scenario 4: Manglende Fajr-bøn bevidst (Missing Fajr Intentionally)
- **Input Context**: User deliberately stayed up late gaming, heard the alarm, and consciously turned it off to sleep through Fajr.
- **Sin Classification**: `huqooq_allah` (Rights of Allah only).
- **Affected Parties**: `[]` (Empty list; zero human victims).
- **Mandatory Actions**:
  - Sincere repentance before Allah for deliberately neglecting prayer.
  - Perform *Qada* (make-up prayer) immediately upon waking/remembering.
  - Practical precautions: sleep early, wudu, multiple alarms.
  - Explicit rule: Zero restitution or human apology required.
- **Evidence**: Surah Maryam (19:59); Surah An-Nisa (4:103); Sahih Muslim 684.

### Scenario 5: Løgn overfor ægtefælle (Lying to Spouse)
- **Input Context**: User lied to spouse regarding financial transactions, whereabouts, and hidden debts.
- **Sin Classification**: `both` (Huqooq Allah & Huqooq al-Ibad).
- **Affected Parties**: `["Ægtefællen"]`.
- **Mandatory Actions**:
  - Repentance before Allah for dishonesty (*Kidhb*).
  - Direct confession, apology, and truthful reconciliation to repair marital trust.
  - Fiqh clarification: Minor pleasantries to foster love are excused; deceit concealing harm or financial betrayal must be rectified.
- **Evidence**: Surah At-Tawbah (9:119); Sahih al-Bukhari 6094.

### Scenario 6: Hærværk / Skade på naboens ejendom (Damaging Neighbor's Property)
- **Input Context**: User damaged neighbor's fence and parked car during an angry outburst and fled.
- **Sin Classification**: `both` (Huqooq Allah & Huqooq al-Ibad).
- **Affected Parties**: `["Naboen"]`.
- **Mandatory Actions**:
  - Repentance before Allah for aggression and property destruction.
  - Full financial compensation or professional repair of all damages (*Daman*).
  - Sanctity of neighbor rights (*Ihsan ila al-Jar*). If physical retaliation is genuinely feared, anonymous repair/payment is permissible provided neighbor is fully indemnified.
- **Evidence**: Surah An-Nisa (4:36); Sahih al-Bukhari 6018 / Sahih Muslim 48; Sunan Ibn Majah 2340 (*La darar wa la dirar*).

### Scenario 7: Tilbagelevering af uretmæssigt tilegnede penge (Anonymous Financial Restitution)
- **Input Context**: User took 5,000 DKK from a former acquaintance years ago and now wishes to make Tawbah without suffering social disgrace.
- **Sin Classification**: `both` (Huqooq Allah & Huqooq al-Ibad).
- **Affected Parties**: `["Den retmæssige ejer"]`.
- **Mandatory Actions**:
  - Repentance before Allah.
  - **Anonymous Restitution**: Shariah mandates returning the exact value (*Radd al-Mazalim*). It does NOT require public self-humiliation. Money may be returned via bank transfer, postal envelope, intermediary, or disguised as a gift/payment.
  - If owner cannot be located after diligent search, donate full amount to charity (*Sadaqah*) in their name.
- **Evidence**: Surah An-Nisa (4:58); Sahih al-Bukhari 2449.

### Scenario 8: Privat synd mellem tjener og Allah (Private Personal Sin)
- **Input Context**: User indulged in private sinful viewing / habits alone behind closed doors.
- **Sin Classification**: `huqooq_allah` (Rights of Allah only).
- **Affected Parties**: `[]` (Empty list; zero human victims).
- **Mandatory Actions**:
  - Sincere personal repentance alone with Allah (Nadam, Iqla', Azm).
  - **Mandatory Sitr (Concealment)**: Strictly haram to confess or expose this sin to anyone (spouse, parents, friends, imam).
  - Wipe out sin with good deeds: *Salat al-Tawbah* (2 voluntary rak'ahs), Quran, Sadaqah.
- **Evidence**: Surah Az-Zumar (39:53); Sahih al-Bukhari 6069 / Sahih Muslim 2990 (*Mujahirun* warning).

### Scenario 9: Falsk anklage / Bagvaskelse (False Accusation / Buhtan)
- **Input Context**: User spread false rumors accusing an innocent community member of theft and fraudulent conduct.
- **Sin Classification**: `both` (Huqooq Allah & Huqooq al-Ibad).
- **Affected Parties**: `["Den falsk anklagede person"]`.
- **Mandatory Actions**:
  - Repentance before Allah for severe sin of slander (*Buhtan*).
  - **Mandatory Public Retraction**: Because the false claim spread publicly, repentance requires going directly to the recipients and explicitly retracting the accusation, clearing the victim's honor.
  - Personal apology to victim seeking their forgiveness.
- **Evidence**: Surah An-Nur (24:19, 24:23); Surah Al-Ahzab (33:58); Sahih Muslim 2589.

### Scenario 10: Brud på tillid / Underslæb (Breaking Trust / Embezzlement)
- **Input Context**: User embezzled funds from a community sports club / charity treasury where they served as treasurer.
- **Sin Classification**: `both` (Huqooq Allah & Huqooq al-Ibad).
- **Affected Parties**: `["Foreningen / Medlemmerne"]`.
- **Mandatory Actions**:
  - Repentance before Allah for betraying trust (*Khiyanat al-Amanah*).
  - Full financial restitution of all embezzled funds into the organization's account.
  - Rectification of financial ledgers; stepping down from treasurer position to prevent recurrence.
  - Trigger `scholar_consultation_required: true` if legal / contractual complexities exist.
- **Evidence**: Surah Al-Anfal (8:27); Sahih al-Bukhari 33 / Sahih Muslim 59.

---

## 6. Coverage Thresholds & Quality Gates

To guarantee production quality, the following quality gates are enforced:

1. **Scenario Pass Rate**: 100% (10 of 10 confession scenarios must pass all assertions).
2. **Schema Adherence**: 100% compliance with the 17-field `AnalysisResultSchema` specification.
3. **Rights Differentiation**: 0 false classifications (pure *Huqooq Allah* must never require human restitution; property usurpation must always mandate restitution).
4. **Sitr & Fitnah Compliance**: 0 violations (private sins must never advise human confession; backbiting without victim knowledge must prioritize fitnah avoidance).
5. **Boundary & Input Resilience**: Zero unhandled 500 errors on empty inputs, Danish characters (`æ, ø, å`), SQL characters, or payloads up to 10,000 characters.
6. **Data Isolation Security**: 100% prevention of cross-user data leakage.
