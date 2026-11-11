# Tawbah Guiden — Islamisk Ansvarlighed, Anger & Genopretning (Danish Islamic Accountability & Tawbah Web App)

> **"Tag ansvar. Søg tilgivelse. Gør det godt igen."**  
> *Fortæl, hvad du har gjort. Få hjælp til at forstå dine islamiske forpligtelser og de handlinger, du bør tage.*

En komplet, produktionsklar dansk webapplikation, der hjælper muslimer med at identificere synder, forstå deres islamiske forpligtelser (*Huqooq Allah* og *Huqooq al-Ibad*), foretage oprigtig *tawbah* (anger og omvendelse) og genoprette uret begået mod andre mennesker.

---

## 1. Kernefunktioner

1. **Stemmebekendelse & Skriftlig Bekendelse**:
   - Fremtrædende mikrofonoptager (`MediaRecorder` + live lydbølge-visualisering + timer).
   - Start, pause, genoptag, stop, lyt til optagelsen, eller slet og optag igen.
   - Dansk talegenkendelse i browseren (`SpeechRecognition` `da-DK`) samt serverside OpenAI Whisper API (`whisper-1`) med deterministisk udviklings-fallback.
   - Eksplicit samtykkekrav før overførsel eller analyse og fuld privatlivsforklaring baseret på *Al-Sitr* (islamisk hemmeligholdelse af private synder).
2. **Systematisk Islamisk Analyse (7-trins motor)**:
   - Adskiller sammensatte bekendelser i individuelle hændelser (`IncidentSplitter`).
   - Klassificerer hver hændelse i:
     - **Huqooq Allah** (Allahs rettigheder — f.eks. forsømte bønner, faste, private synder)
     - **Huqooq al-Ibad** (Menneskers rettigheder — f.eks. tyveri, bagtalelse, løgn, hærværk)
     - **Both** (Både Allahs og menneskers rettigheder)
   - Forklarer de 4 klassiske betingelser for oprigtig *tawbah* (ophør, fortrydelse, fast beslutning om ikke at vende tilbage, samt genopretning af menneskers rettigheder).
   - Skelner nuanceret mellem direkte undskyldning, anonym tilbagelevering af penge/ejendom (*Radd al-Mazalim*) og tilfælde hvor oplysning om bagtalelse (*Ghibah*) vil skabe større splid (*fitnah*).
3. **Verificeret Islamisk Vidensbase (Anti-Hallucination RAG)**:
   - Baseret på Koranen, *Sahih al-Bukhari*, *Sahih Muslim*, samt *Abu Dawud*, *Jami' at-Tirmidhi*, *An-Nasa'i* og *Ibn Majah* efter *Ahlus-Sunnah wal-Jama'ah*.
   - Alle citater verificeres deterministisk mod kuraterede datasæt (`app/knowledge/quran.json`, `hadith.json`, `duas.json`, `fiqh_rules.json`) med arabisk originaltekst, dansk oversættelse, kilde, nummer, autenticitetsgrad og relevansforklaring.
4. **Interaktivt Resultat & Personligt Ansvarlighedspanel**:
   - Nummereret interaktiv tjekliste (*Påkrævede handlinger / Wajib* og *Anbefalede handlinger / Mustahabb*) med automatisk lagring i SQLite.
   - Privat konto, historik over tidligere vurderinger, *Angerens Dagbog* (*Muhasabah* refleksioner), sletning af enkelte bekendelser og komplet nulstilling (*Panic Wipe*).
5. **Designsystem**:
   - Roligt, seriøst og respektfuldt design i dyb skovgrøn (`#16382B`), varm råhvid (`#FBF9F5`) og diskrete guldaccenter (`#C29B38`).

---

## 2. Hurtig Start

### Forudsætninger
- Python 3.10+ (SQLite i WAL-mode er indbygget)
- Pakker i `requirements.txt` (`fastapi`, `uvicorn`, `pydantic`, `python-multipart`, `httpx`)

### Installation & Kørsel
```powershell
pip install -r requirements.txt

# Start webserveren på http://127.0.0.1:8000
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Åbn derefter `http://127.0.0.1:8000` i din browser.

> **Bemærk om API-nøgler:** Hvis `OPENAI_API_KEY` eller `GEMINI_API_KEY` ikke er sat, kører applikationen automatisk i fuldt funktionel **udviklings- og demonstrationstilstand** via den deterministiske Ahlus-Sunnah regelmotor (`app/engine/rule_engine.py`) og transskriptions-fallback (`app/audio/transcriber.py`).

---

## 3. Automatiserede Tests (De 10 Scenarier & 4 Test-Tiers)

Kør hele testsuiten (148 tests på tværs af 4 tiers inkl. alle 10 obligatoriske bekendelsesscenarier):

```powershell
python tests/run_tests.py
```

Eller kør kun de 10 bekendelsesscenarier fra Sektion 13:

```powershell
python tests/run_tests.py --scenarios-only
```

---

## 4. Vigtig Islamisk Ansvarsfraskrivelse

Denne applikation er et pædagogisk og åndeligt selvhjælpsværktøj baseret på Koranen, autentisk Sunnah og anerkendt sunni-islamisk retslære (*Ahlus-Sunnah wal-Jama'ah*). Applikationen udsteder **ikke** bindende juridiske fatwaer og erstatter aldrig personlig rådgivning hos en kvalificeret islamisk lærd (*Alim* / *Mufti*).
