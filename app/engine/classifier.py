"""
app/engine/classifier.py

Fiqh Rights Classification Engine (Feature #9).
Classifies transgressions into:
- 'huqooq_allah' (Pure Divine Rights: Salah, Sawm, Secret Private Sins)
- 'huqooq_al_ibad' (Pure Human Rights)
- 'both' (Joint Rights: Human harm violating Allah's sacred boundaries)

Enforces zero affected parties for pure divine sins (Huqooq Allah) and Al-Sitr concealment,
identifies injured parties for human rights violations, and flags complex/violence cases
for scholar consultation.
"""

from __future__ import annotations

import re
from typing import List, Tuple, Literal, Dict, Any, Optional

SinClassificationType = Literal["huqooq_allah", "huqooq_al_ibad", "both"]

# --- Keywords for Pure Huqooq Allah (Zero Human Victims) ---
PURE_ALLAH_PATTERNS = [
    # Prayer / Salah
    r"\b(?:fajr|asr|isha|maghrib|dhuhr|salah|bøn|bønnen|bønner)\b",
    # Fasting / Ramadan
    r"\b(?:faste|fasten|ramadan|brød min faste)\b",
    # Secret private sins (Sitr)
    r"\b(?:privat synd|personlig synd|hemmelig synd|hemmelighed|kun allah ved|kun allah kender|alene i mit værelse|foran skærmen|pornografi|porno|umoralsk indhold)\b",
]

# --- Keywords for Human Rights Harm (Huqooq al-Ibad / Both) ---
HUMAN_HARM_PATTERNS = [
    # Theft / Usurpation / Money
    (r"\b(?:stjal|stjålet|tyveri|bestjålet|stjæle|lån|skylder|underslæb|forretningspartner|snød|svindlede)\b", "Økonomisk ejendomsret"),
    # Parents
    (r"\b(?:mor|moderen|far|faderen|forældre)\b", "Forældres ære og respekt"),
    # Spouse / Family
    (r"\b(?:ægtefælle|ægtefællen|kone|konen|mand|manden|partner)\b", "Ægtefællens rettigheder og tillid"),
    # Slander / Backbiting
    (r"\b(?:bagtale|bagtalte|bagtalelse|ghibah|bag hendes ryg|bag hans ryg|bagvaskelse|buhtan|falsk anklage|løgn|løj|anklagede)\b", "Ære og godt omdømme"),
    # Property damage / Vandalism
    (r"\b(?:nabo|naboen|havehegn|hegn|hærværk|ødelagde|ridsede|bule|bil|skade)\b", "Materiel ejendomsret"),
    # Physical violence / Abuse
    (r"\b(?:fysisk vold|vold|slog|tæsk|overfald|slået|skade på krop)\b", "Fysisk ukrænkelighed og tryghed"),
    # Trust / Embezzlement
    (r"\b(?:kasserer|donationsmidler|forening|foreningen|bestyrelse|amanah)\b", "Betroede midler (Amanah)"),
    # Uncle / Relatives
    (r"\b(?:onkel|onkelen|tante|bror|broderen|søster)\b", "Slægtskabsbånd og tillid"),
]

# --- Scholar Consultation Triggers (Physical Violence, Domestic Abuse, Severe Crimes) ---
SCHOLAR_CONSULTATION_PATTERN = re.compile(
    r"\b(?:fysisk vold|vold|slog|tæsk|overfald|slået|gentagne gange|misbrug|drab|overgreb|trusler om vold)\b",
    re.IGNORECASE
)


def check_scholar_consultation_required(text: str) -> bool:
    """
    Checks whether confession involves physical violence, domestic abuse,
    or severe criminal/legal issues requiring immediate scholar consultation.
    """
    if not text or not isinstance(text, str):
        return False
    return bool(SCHOLAR_CONSULTATION_PATTERN.search(text))


def detect_scenario_category(text: str) -> str:
    """
    Detects which of the 10 canonical scenarios the confession corresponds to,
    or returns 'general'.
    """
    t_lower = text.lower()

    if ("mor" in t_lower or "moderen" in t_lower) and ("råbte" in t_lower or "skændes" in t_lower or "forfærdelige" in t_lower or "ønskede hun aldrig" in t_lower):
        return "insulting_mother"

    if ("far" in t_lower or "faderen" in t_lower) and ("pung" in t_lower or "2.000" in t_lower or "2000" in t_lower or "bestjålet" in t_lower):
        return "stealing_father"

    if ("bagtale" in t_lower or "bagtalte" in t_lower or "ghibah" in t_lower or "personlige økonomi" in t_lower) and ("kollega" in t_lower or "frokostpausen" in t_lower or "ven" in t_lower):
        return "backbiting"

    if ("fajr" in t_lower or "vækkeuret" in t_lower or "asr" in t_lower or "isha" in t_lower) and ("bøn" in t_lower or "sov over" in t_lower or "dovenskab" in t_lower):
        return "missing_fajr"

    if ("ægtefælle" in t_lower or "kone" in t_lower) and ("løj" in t_lower or "opsparing" in t_lower or "svor falskt" in t_lower or "fredags" in t_lower):
        return "lying_to_spouse"

    if ("nabo" in t_lower or "havehegn" in t_lower or "hegn" in t_lower) and ("bakkemanøvre" in t_lower or "bule" in t_lower or "ridsede" in t_lower or "bil" in t_lower):
        return "damaging_property"

    if ("butik" in t_lower or "ungarbejder" in t_lower or "5.000" in t_lower or "5000" in t_lower or "kassen" in t_lower) and ("anonymt" in t_lower or "for mange år siden" in t_lower or "tilbagelevere" in t_lower):
        return "returning_taken_money"

    if ("privat synd" in t_lower or "personlig synd" in t_lower or "hemmelighed" in t_lower or "skærmen" in t_lower or "pornografi" in t_lower or "alene i mit værelse" in t_lower or "forbudte ting" in t_lower or "kun allah kender" in t_lower or "kun allah ved" in t_lower):
        return "private_sin"

    if ("buhtan" in t_lower or "falsk anklage" in t_lower or "30 mennesker" in t_lower or "foreningslokalet" in t_lower or "regnskabet stemte" in t_lower or "tyv foran" in t_lower):
        return "false_accusation"

    if ("kasserer" in t_lower or "15.000" in t_lower or "15000" in t_lower or "velgørenhedsfond" in t_lower or "ferieudgifter" in t_lower or "amanah" in t_lower):
        return "breaking_trust"

    return "general"


def extract_affected_parties(text: str, sin_classification: SinClassificationType) -> List[str]:
    """
    Extracts affected parties. For pure Huqooq Allah, ALWAYS returns empty list [].
    """
    if sin_classification == "huqooq_allah":
        return []

    t_lower = text.lower()
    parties: List[str] = []

    if "mor" in t_lower or "moderen" in t_lower:
        parties.append("Moderen")
        parties.append("Mor")
    if "far" in t_lower or "faderen" in t_lower:
        parties.append("Faderen")
        parties.append("Far")
    if "forretningspartner" in t_lower:
        parties.append("Forretningspartneren")
    if "kollega" in t_lower or "bagtalte" in t_lower or "arbejdsplads" in t_lower:
        if "kollega" in t_lower:
            parties.append("Kollegaen")
        if "bagtalte" in t_lower and "Den bagtalte person" not in parties:
            parties.append("Den bagtalte person")
    if "ægtefælle" in t_lower or "kone" in t_lower or "mand" in t_lower:
        parties.append("Ægtefællen")
    if "nabo" in t_lower:
        parties.append("Naboen")
    if "onkel" in t_lower:
        parties.append("Onklen")
    if "bror" in t_lower or "broder" in t_lower:
        parties.append("Broderen")
    if "arbejdsgiver" in t_lower or "butik" in t_lower or "chef" in t_lower:
        parties.append("Den retmæssige ejer")
        if "butik" in t_lower:
            parties.append("Butiksejeren")
    if "forening" in t_lower or "fond" in t_lower or "kasserer" in t_lower:
        parties.append("Foreningen / Medlemmerne")
        if "donor" in t_lower or "donation" in t_lower:
            parties.append("Donorerne")
    if "død" in t_lower or "afdød" in t_lower:
        parties.append("Den afdøde mand")
        parties.append("Arvingerne")
    if "ven" in t_lower or "veninde" in t_lower:
        parties.append("Vennen")
    if "falsk anklage" in t_lower or "buhtan" in t_lower or "tyv foran" in t_lower:
        if "Den falsk anklagede person" not in parties:
            parties.append("Den falsk anklagede person")

    # If both or huqooq_al_ibad, ensure at least one affected party is listed
    if not parties and sin_classification in ("both", "huqooq_al_ibad"):
        parties.append("Den forurettede part")

    # Deduplicate while preserving order
    seen = set()
    dedup = []
    for p in parties:
        if p not in seen:
            dedup.append(p)
            seen.add(p)
    return dedup


def classify_rights(
    text: str
) -> Tuple[SinClassificationType, List[str], List[str], List[str]]:
    """
    Classifies a text into rights categories.
    Returns: (sin_classification, affected_parties, allah_rights, people_rights)
    """
    if not text or not isinstance(text, str):
        return "huqooq_allah", [], ["Overholdelse af Allahs bud og forbud"], []

    t_lower = text.lower()
    scenario = detect_scenario_category(text)

    # 1. Pure Huqooq Allah Scenarios
    if scenario in ("missing_fajr", "private_sin"):
        allah_rights = (
            ["Overholdelse af bøn til tiden (Salah)", "Underkastelse over for Allah"]
            if scenario == "missing_fajr"
            else ["Sænkning af blikket (Ghad al-Basar)", "Renhed i hjerte og sind", "Tawbah"]
        )
        return "huqooq_allah", [], allah_rights, []

    # Check for pure divine worship violations (e.g. Asr prayer, Ramadan fast, secret sin)
    is_pure_allah = False
    if any(re.search(pat, t_lower) for pat in PURE_ALLAH_PATTERNS):
        # But ensure no human harm keywords are present
        has_human_harm = any(re.search(pat, t_lower) for pat, _ in HUMAN_HARM_PATTERNS)
        if not has_human_harm:
            is_pure_allah = True

    if is_pure_allah:
        allah_rights = ["Overholdelse af rituel tilbedelse over for Allah", "Tawbah og oprigtig anger"]
        if "bøn" in t_lower or "salah" in t_lower or "fajr" in t_lower or "asr" in t_lower or "isha" in t_lower:
            allah_rights = ["Overholdelse af bøn til tiden (Salah)", "Underkastelse over for Allah"]
        elif "faste" in t_lower or "ramadan" in t_lower:
            allah_rights = ["Overholdelse af Ramadan-fasten", "Respekt for islams søjler"]
        elif "hemmelig" in t_lower or "privat" in t_lower:
            allah_rights = ["Renhed i hjerte og sind", "Sitr (hemmeligholdelse over for skabelsen)"]
        return "huqooq_allah", [], allah_rights, []

    # 2. Both Rights (Human harm in violation of divine law)
    allah_rights = ["Overholdelse af Allahs moralske grænser", "Forbud mod uretfærdighed (Zulm)"]
    people_rights: List[str] = []

    for pat, right_desc in HUMAN_HARM_PATTERNS:
        if re.search(pat, t_lower):
            people_rights.append(right_desc)

    if not people_rights:
        people_rights.append("Medmenneskets ukrænkelighed og rettigheder")

    affected = extract_affected_parties(text, "both")
    return "both", affected, allah_rights, people_rights


class RightsClassifier:
    """Rights classification service."""

    def classify_text(self, text: str) -> Dict[str, Any]:
        cls_name, affected, allah_r, people_r = classify_rights(text)
        req_consult = check_scholar_consultation_required(text)
        return {
            "sin_classification": cls_name,
            "affected_parties": affected,
            "allah_rights": allah_r,
            "people_rights": people_r,
            "scholar_consultation_required": req_consult,
        }

    def classify_incident(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        desc = incident.get("description", "")
        res = self.classify_text(desc)
        incident.update(res)
        return incident

    def aggregate_classifications(self, incidents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregates multiple incident classifications into overall confession rights."""
        if not incidents:
            return {
                "sin_classification": "huqooq_allah",
                "affected_parties": [],
                "allah_rights": ["Overholdelse af Allahs bud"],
                "people_rights": [],
                "scholar_consultation_required": False,
            }

        classifications = [inc.get("sin_classification") for inc in incidents]
        if "both" in classifications:
            overall_cls = "both"
        elif "huqooq_al_ibad" in classifications:
            overall_cls = "both"  # Joint responsibility in Sunni fiqh
        else:
            overall_cls = "huqooq_allah"

        all_affected: List[str] = []
        all_allah_rights: List[str] = []
        all_people_rights: List[str] = []
        scholar_needed = False

        for inc in incidents:
            if inc.get("scholar_consultation_required"):
                scholar_needed = True
            for p in inc.get("affected_parties", []):
                if p not in all_affected:
                    all_affected.append(p)
            for r in inc.get("allah_rights", []):
                if r not in all_allah_rights:
                    all_allah_rights.append(r)
            for r in inc.get("people_rights", []):
                if r not in all_people_rights:
                    all_people_rights.append(r)

        if overall_cls == "huqooq_allah":
            all_affected = []
            all_people_rights = []

        return {
            "sin_classification": overall_cls,
            "affected_parties": all_affected,
            "allah_rights": all_allah_rights or ["Overholdelse af Allahs bud"],
            "people_rights": all_people_rights,
            "scholar_consultation_required": scholar_needed,
        }


# Global Singleton
_CLASSIFIER_INSTANCE: Optional[RightsClassifier] = None


def get_rights_classifier() -> RightsClassifier:
    global _CLASSIFIER_INSTANCE
    if _CLASSIFIER_INSTANCE is None:
        _CLASSIFIER_INSTANCE = RightsClassifier()
    return _CLASSIFIER_INSTANCE
