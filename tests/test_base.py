"""
Base test utilities, schema contracts, and test fixtures for Islamic Tawbah App.
Zero external test framework dependencies (uses standard library unittest).
"""

import os
import sys
import unittest
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Check if application package 'app' and FastAPI entrypoint are importable
APP_AVAILABLE = False
APP_IMPORT_ERROR = None

try:
    import app
    import app.schemas
    import app.main
    if hasattr(app.main, "app"):
        APP_AVAILABLE = True
    else:
        APP_IMPORT_ERROR = "app.main does not define 'app' FastAPI instance"
except (ImportError, ModuleNotFoundError) as err:
    APP_AVAILABLE = False
    APP_IMPORT_ERROR = str(err)


# --- Tier Marking Decorator ---

def tier(level: int):
    """
    Decorator to mark a test method or class with its test tier (1, 2, 3, or 4).
    """
    def decorator(obj):
        obj._test_tier = level
        return obj
    return decorator


def requires_app(test_item):
    """
    Decorator that skips tests when the application 'app' package is not yet implemented.
    Ensures progressive testability during parallel multi-agent development.
    """
    return unittest.skipUnless(
        APP_AVAILABLE,
        f"Application package 'app' not yet implemented ({APP_IMPORT_ERROR})"
    )(test_item)


# --- Canonical Pydantic Reference Models (Contract Specification) ---
# Derived from PROJECT.md § Interface Contracts (lines 76-142)

class ReferenceQuranReference(BaseModel):
    surah: str
    ayah: int
    arabic_text: str
    danish_translation: str
    explanation: str


class ReferenceHadithReference(BaseModel):
    collection: str
    hadith_number: str
    authenticity_grading: str
    arabic_text: Optional[str] = None
    danish_translation: str
    explanation: str


class ReferenceRecommendedDua(BaseModel):
    title: str
    arabic_text: str
    transliteration: str
    danish_translation: str
    source: str
    context: str


class ReferenceActionItemSchema(BaseModel):
    id: str
    category: Literal["wajib", "mustahabb", "tawbah_allah", "restitution", "apology", "rectification", "sadaqah", "extra_prayers", "dua", "self_discipline"]
    description: str
    explanation: Optional[str] = None
    target_party: Optional[str] = None
    completed: bool = False


class ReferenceIncidentSchema(BaseModel):
    incident_id: str
    incident_title: Optional[str] = None
    sin_classification: Literal["huqooq_allah", "huqooq_al_ibad", "both"]
    description: str
    affected_parties: List[str] = []
    allah_rights: List[str] = []
    people_rights: List[str] = []
    required_actions: List[ReferenceActionItemSchema] = []
    recommended_actions: List[ReferenceActionItemSchema] = []
    apology_guidance: Optional[str] = None
    restitution_guidance: Optional[str] = None


class ReferenceAnalysisResultSchema(BaseModel):
    incident_summary: str
    incidents: List[ReferenceIncidentSchema]
    sin_classification: Literal["huqooq_allah", "huqooq_al_ibad", "both"]
    allah_rights: List[str]
    people_rights: List[str]
    affected_parties: List[str]
    severity_explanation: str
    required_actions: List[ReferenceActionItemSchema]
    recommended_actions: List[ReferenceActionItemSchema]
    apology_guidance: Optional[str] = None
    restitution_guidance: Optional[str] = None
    quran_references: List[ReferenceQuranReference]
    hadith_references: List[ReferenceHadithReference]
    recommended_duas: List[ReferenceRecommendedDua]
    scholarly_disagreement: Optional[str] = None
    confidence_level: Literal["high", "medium", "low"]
    scholar_consultation_required: bool
    final_reminder: str


# --- Authoritative Specification for the 10 Required Confession Scenarios ---
# Derived from Section 13 / R5 and Survey 2 & 3 Analysis

TEN_SCENARIOS: Dict[int, Dict[str, Any]] = {
    1: {
        "id": 1,
        "title": "Fornærmelse af moderen (Insulting mother)",
        "input_text": (
            "Jeg kom op at skændes med min mor i går aftes. I raseri råbte jeg ad hende, "
            "kaldte hende forfærdelige ting og sagde, at jeg ønskede hun aldrig var min mor. "
            "Hun græd og gik ind på sit værelse. Jeg føler en enorm skyldfølelse og smerte i hjertet. "
            "Hvordan gør jeg tawbah over for Allah og over for min mor?"
        ),
        "expected_classification": "both",
        "affected_parties": ["Moderen"],
        "primary_rights_allah": ["Lydighed mod forældre (Birr al-Walidayn)", "Forbud mod ulydighed (Uqooq)"],
        "primary_rights_people": ["Moderens ære", "Beskyttelse mod verbal overlast"],
        "nuance": "Direct humble apology required (kissing head/hands). No fitnah nuance excuses withholding apology.",
        "mandatory_actions_keywords": ["anger", "undskyld", "tilgivelse", "mor", "iqla", "nadam"],
        "quran_surah": "Al-Isra",
        "quran_ayah": 23,
        "hadith_collection": "Sahih al-Bukhari",
        "hadith_number": "5971",
    },
    2: {
        "id": 2,
        "title": "Tyveri fra faderen (Stealing from father)",
        "input_text": (
            "For to uger siden tog jeg 2.000 kroner fra min fars pung uden hans viden eller samtykke, "
            "fordi jeg skyldte penge til en ven. Min far tror nu, han har tabt pengene og leder efter dem. "
            "Jeg skammer mig dybt over at have bestjålet min egen far. "
            "Hvad kræver Allah af mig for at min anger accepteres?"
        ),
        "expected_classification": "both",
        "affected_parties": ["Faderen"],
        "primary_rights_allah": ["Forbud mod tyveri (Sariqah)", "Ærlighed og retskaffenhed"],
        "primary_rights_people": ["Faderens ejendomsret", "Økonomisk godtgørelse"],
        "nuance": "Mandatory financial restitution. Secret/anonymous return is valid if direct confession destroys family ties.",
        "mandatory_actions_keywords": ["tilbagebetal", "restitution", "penge", "far", "2000"],
        "quran_surah": "Al-Ma'idah",
        "quran_ayah": 38,
        "hadith_collection": "Sahih al-Bukhari",
        "hadith_number": "2449",
    },
    3: {
        "id": 3,
        "title": "Bagtalelse (Backbiting / Ghibah)",
        "input_text": (
            "Jeg sad sammen med nogle kolleger i frokostpausen og begyndte at bagtale en anden kollega, "
            "som ikke var til stede. Jeg spredte historier om hans personlige økonomi og kritiserede hans evner, "
            "hvilket fik de andre til at grine ad ham. Han ved ikke, at vi har talt om ham. "
            "Skal jeg gå til ham og fortælle det, eller skaber det mere splid?"
        ),
        "expected_classification": "both",
        "affected_parties": ["Den bagtalte person", "Kollegaen"],
        "primary_rights_allah": ["Forbud mod bagtalelse (Ghibah)", "Vogte over tungen"],
        "primary_rights_people": ["Kollegaens ære og ry"],
        "nuance": "If victim does not know and confession causes fitnah/strife, do not tell them; make dua and praise them instead.",
        "mandatory_actions_keywords": ["dua", "bøn", "tilgivelse", "ære", "fitnah", "bagtale"],
        "quran_surah": "Al-Hujurat",
        "quran_ayah": 12,
        "hadith_collection": "Sahih Muslim",
        "hadith_number": "2589",
    },
    4: {
        "id": 4,
        "title": "Manglende Fajr-bøn bevidst (Missing Fajr intentionally)",
        "input_text": (
            "Jeg blev oppe hele natten og spillede computerspil. Da vækkeuret ringede til Fajr-bønnen kl. 04:30, "
            "hørte jeg det tydeligt, men slog det bevidst fra og vendte mig om for at sove videre af dovenskab. "
            "Jeg vågnede først kl. 10:00 med solen højt på himlen. Jeg forsømte Allahs obligatoriske bøn med vilje. "
            "Hvad er min bod og hvordan råder jeg bod på denne store synd?"
        ),
        "expected_classification": "huqooq_allah",
        "affected_parties": [],
        "primary_rights_allah": ["Overholdelse af bøn til tiden (Salah)", "Underkastelse over for Allah"],
        "primary_rights_people": [],
        "nuance": "Pure Huqooq Allah. Zero human restitution or apology. Immediate Qada prayer required.",
        "mandatory_actions_keywords": ["qada", "bøn", "fajr", "anger", "indhent", "forsinket"],
        "quran_surah": "Maryam",
        "quran_ayah": 59,
        "hadith_collection": "Sahih Muslim",
        "hadith_number": "684",
    },
    5: {
        "id": 5,
        "title": "Løgn overfor ægtefælle (Lying to spouse)",
        "input_text": (
            "Jeg løj over for min ægtefælle om, hvor jeg var i fredags, og hemmeligholdt, "
            "at jeg brugte en stor sum fælles opsparing på personlig gæld. Min ægtefælle spurgte mig direkte, "
            "og jeg svor falskt for at dække over sandheden. Samvittigheden nager mig voldsomt. "
            "Hvordan redder jeg mit ægteskab islamisk og gør sand tawbah?"
        ),
        "expected_classification": "both",
        "affected_parties": ["Ægtefællen"],
        "primary_rights_allah": ["Forbud mod løgn (Kidhb)", "Forbud mod falsk ed"],
        "primary_rights_people": ["Ægtefællens tillid", "Fællesøkonomiske rettigheder"],
        "nuance": "Direct apology, truthful disclosure, and reconciliation required to rebuild marital trust.",
        "mandatory_actions_keywords": ["sandhed", "ærlighed", "ægtefælle", "undskyld", "tillid"],
        "quran_surah": "At-Tawbah",
        "quran_ayah": 119,
        "hadith_collection": "Sahih al-Bukhari",
        "hadith_number": "6094",
    },
    6: {
        "id": 6,
        "title": "Hærværk / Skade på naboens ejendom (Damaging property)",
        "input_text": (
            "Under en heftig bakkemanøvre i min bil ramte jeg naboens havehegn og ridsede hans parkerede bil. "
            "I panik skyndte jeg mig væk uden at efterlade en seddel eller give mig til kende. "
            "Hegnet er knækket, og bilen har en stor bule. Naboen ved ikke, hvem der gjorde det. "
            "Hvad påbyder islam mig at gøre for at rette op på skaden?"
        ),
        "expected_classification": "both",
        "affected_parties": ["Naboen"],
        "primary_rights_allah": ["Naboens særlige rettigheder (Huqooq al-Jar)", "Forbud mod skade (La darar)"],
        "primary_rights_people": ["Naboens materielle ejendom", "Fuld erstatning for skader"],
        "nuance": "Full financial compensation or repair required. Anonymous payment/repair valid if physical conflict feared.",
        "mandatory_actions_keywords": ["erstatning", "reparation", "nabo", "hegn", "skade", "daman"],
        "quran_surah": "An-Nisa",
        "quran_ayah": 36,
        "hadith_collection": "Sahih al-Bukhari",
        "hadith_number": "6018",
    },
    7: {
        "id": 7,
        "title": "Tilbagelevering af uretmæssigt tilegnede penge (Returning taken money anonymously)",
        "input_text": (
            "For mange år siden, da jeg var yngre og umoden, tog jeg 5.000 kroner fra kassen i den butik, "
            "hvor jeg arbejdede som ungarbejder. Chefen opdagede aldrig manglen. Nu praktiserer jeg min religion, "
            "og tanken om disse haram-penge holder mig vågen om natten. Hvis jeg står frem personligt, "
            "bliver jeg politianmeldt og mister mit nuværende job og min sociale anseelse. "
            "Må jeg tilbagelevere pengene anonymt?"
        ),
        "expected_classification": "both",
        "affected_parties": ["Den retmæssige ejer", "Butiksejeren"],
        "primary_rights_allah": ["Forbud mod at fortære andres ejendom uretmæssigt (Batil)"],
        "primary_rights_people": ["Ejerens økonomiske krav (Radd al-Mazalim)"],
        "nuance": "Shariah explicitly permits returning money anonymously. Public self-incrimination is not required.",
        "mandatory_actions_keywords": ["anonym", "tilbagelevering", "5000", "ejer", "mazalim", "sadaqah"],
        "quran_surah": "An-Nisa",
        "quran_ayah": 58,
        "hadith_collection": "Sahih al-Bukhari",
        "hadith_number": "2449",
    },
    8: {
        "id": 8,
        "title": "Privat synd mellem tjener og Allah (Private personal sin)",
        "input_text": (
            "Jeg er faldet i en privat synd alene i mit værelse sent om aftenen foran skærmen, "
            "hvor jeg har set på forbudte ting (pornografi og umoralsk indhold). Ingen mennesker ved det. "
            "Bør jeg betro mig til min kone eller en imam i moskeen for at få vejledning, "
            "eller skal jeg holde det hemmeligt og angre direkte over for Allah?"
        ),
        "expected_classification": "huqooq_allah",
        "affected_parties": [],
        "primary_rights_allah": ["Sænkning af blikket (Ghad al-Basar)", "Renhed i hjerte og sind", "Tawbah"],
        "primary_rights_people": [],
        "nuance": "Mandatory Sitr (concealment). Strictly haram to expose to wife, imam, or anyone. Tawbah + good deeds.",
        "mandatory_actions_keywords": ["hemmelighold", "sitr", "skjul", "anger", "ingen", "bøn"],
        "quran_surah": "Az-Zumar",
        "quran_ayah": 53,
        "hadith_collection": "Sahih al-Bukhari",
        "hadith_number": "6069",
    },
    9: {
        "id": 9,
        "title": "Falsk anklage / Bagvaskelse (False accusation / Buhtan)",
        "input_text": (
            "I et ophedet skænderi i foreningslokalet anklagede jeg offentligt en bror for at have svindlet "
            "med foreningens penge og kaldte ham en tyv foran 30 mennesker. Jeg vidste inderst inde, "
            "at jeg ikke havde faste beviser, og senere opdagede jeg, at regnskabet stemte fuldstændigt. "
            "Hans ry i lokalsamfundet er nu ødelagt på grund af mine ord. Hvordan gør jeg bod for buhtan?"
        ),
        "expected_classification": "both",
        "affected_parties": ["Den falsk anklagede person"],
        "primary_rights_allah": ["Forbud mod bagvaskelse og falske beskyldninger (Buhtan)"],
        "primary_rights_people": ["Offerets ære og renhed foran forsamlingen"],
        "nuance": "Mandatory public retraction to the exact audience where rumor spread, clearing his name, plus personal apology.",
        "mandatory_actions_keywords": ["offentlig", "træk", "tilbage", "ære", "rense", "undskyld", "buhtan"],
        "quran_surah": "An-Nur",
        "quran_ayah": 19,
        "hadith_collection": "Sahih Muslim",
        "hadith_number": "2589",
    },
    10: {
        "id": 10,
        "title": "Brud på tillid / Underslæb (Breaking trust / Embezzlement)",
        "input_text": (
            "Jeg var kasserer i en lokal velgørenhedsfond og misbrugte min stilling til at overføre "
            "15.000 kroner af de indsamlede donationsmidler til min egen private konto for at dække ferieudgifter. "
            "Jeg forfalskede kvitteringer for at skjule uregelmæssighederne over for bestyrelsen. "
            "Jeg frygter Allahs straf på Dommedag. Hvordan råder jeg bod på dette svigt af amanah?"
        ),
        "expected_classification": "both",
        "affected_parties": ["Foreningen / Medlemmerne", "Donorerne"],
        "primary_rights_allah": ["Forbud mod forræderi mod betroet gods (Khiyanat al-Amanah)"],
        "primary_rights_people": ["Foreningens og donorenes midler", "Gennemsigtighed og sandhed"],
        "nuance": "Mandatory full restitution into the treasury, correction of financial ledgers, and stepping down from position.",
        "mandatory_actions_keywords": ["restitution", "tilbagebetal", "amanah", "15000", "bestyrelse", "regnskab"],
        "quran_surah": "Al-Anfal",
        "quran_ayah": 27,
        "hadith_collection": "Sahih al-Bukhari",
        "hadith_number": "33",
    },
}
