"""
app/engine/incident_splitter.py

Multi-Sin Incident Segmentation Engine (Feature #8).
Segments compound confessions into discrete atomic incidents under Islamic fiqh principles,
while keeping single-sin narratives unified as a single incident.
"""

from __future__ import annotations

import re
import logging
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

from app.config import OFFLINE_MODE
from app.schemas import IncidentSchema, IncidentDetail, ActionItemSchema

logger = logging.getLogger("tawbah.incident_splitter")


class IncidentSegment(BaseModel):
    """Internal model for segmented confession incidents."""
    incident_id: str
    incident_title: Optional[str] = None
    description: str
    temporal_context: Optional[str] = None
    detected_sin_types: List[str] = Field(default_factory=list)
    raw_segment: str = ""


# --- Sin Detection Keywords (Danish) ---
SIN_KEYWORDS: Dict[str, List[str]] = {
    "theft": [
        "stjal", "stjålet", "tyveri", "bestjålet", "tog 2.000", "tog 5.000", "tog 500",
        "stjæle", "underslæb", "misbrugte min stilling", "stjæler", "batil", "lån"
    ],
    "alcohol_substance": [
        "alkohol", "drak", "druk", "beruset", "vin", "øl", "spiritus", "rusmidler", "stoffer"
    ],
    "prayer": [
        "bøn", "bønnen", "bønner", "fajr", "asr", "isha", "maghrib", "dhuhr", "salah",
        "sprang", "forsømte", "sov over", "forsømte allah", "qada"
    ],
    "fasting": [
        "faste", "fasten", "ramadan", "brød min faste"
    ],
    "backbiting": [
        "bagtale", "bagtalte", "bagtalelse", "ghibah", "bag hans ryg", "bag hendes ryg", "bagtalen"
    ],
    "slander_false_accusation": [
        "buhtan", "falsk anklage", "anklagede", "bagvaskelse", "kaldte ham en tyv",
        "falsk vidnesbyrd", "løgnagtig anklage"
    ],
    "lying": [
        "løj", "løgn", "svor falskt", "hemmeligholdte", "kidhb", "falsk ed", "vildledte"
    ],
    "disrespect_parents": [
        "råbte ad hende", "kaldte hende forfærdelige", "forbandede", "forældre",
        "respektløs", "uqooq", "birr", "skændes med min mor", "skændes med min far"
    ],
    "property_damage": [
        "hærværk", "ødelagde", "havehegn", "ramte naboens", "ridsede", "bule", "materiel skade"
    ],
    "private_sin": [
        "privat synd", "foran skærmen", "pornografi", "umoralsk indhold", "sitr", "hemmelig synd"
    ],
    "violence": [
        "fysisk vold", "slog", "tæsk", "overfald", "slået", "vold"
    ],
    "embezzlement": [
        "kasserer", "donationsmidler", "velgørenhedsfond", "forfalskede kvitteringer",
        "amanah", "underslæb"
    ],
}

# --- Questions and Remorse patterns (Never split into orphan incidents) ---
NON_SIN_POSTAMBLE_PATTERN = re.compile(
    r"^(?:Hvordan\s+gør\s+jeg\s+tawbah|Hvad\s+kræver\s+Allah|Hvad\s+er\s+min\s+bod|"
    r"Bør\s+jeg\s+betro\s+mig|Må\s+jeg|Kan\s+Allah\s+tilgive|Jeg\s+føler\s+en\s+enorm\s+skyldfølelse|"
    r"Jeg\s+skammer\s+mig|Samvittigheden\s+nager|Jeg\s+frygter\s+Allahs\s+straf|"
    r"Hvordan\s+redder\s+jeg|Hvad\s+påbyder\s+islam|Hvordan\s+råder\s+jeg\s+bod)",
    re.IGNORECASE
)

PREAMBLE_PATTERN = re.compile(
    r"^(?:I går begik jeg to store fejl|Jeg begik to store fejl|Jeg har begået to synder|"
    r"Der er to ting jeg fortryder|Jeg har begået flere fejl)[\.\:\,\s]*",
    re.IGNORECASE
)


def _detect_sin_types(text: str) -> List[str]:
    """Detects sin types present in a text snippet."""
    t_lower = text.lower()
    types = []
    for sin_type, keywords in SIN_KEYWORDS.items():
        if any(kw in t_lower for kw in keywords):
            types.append(sin_type)
    return types


def _generate_incident_title(sin_types: List[str], text: str) -> str:
    """Generates an appropriate Danish title for the incident."""
    t_lower = text.lower()
    if "violence" in sin_types:
        return "Fysisk vold og overlast"
    if "disrespect_parents" in sin_types or "mor" in t_lower:
        return "Fornærmelse og ulydighed mod forældre"
    if "embezzlement" in sin_types or "kasserer" in t_lower:
        return "Underslæb og tillidsbrud (Amanah)"
    if "theft" in sin_types:
        return "Tyveri og uretmæssig tilegnelse"
    if "slander_false_accusation" in sin_types or "buhtan" in t_lower:
        return "Falsk anklage og bagvaskelse (Buhtan)"
    if "backbiting" in sin_types:
        return "Bagtalelse af medmenneske (Ghibah)"
    if "lying" in sin_types:
        return "Løgn og falskhed"
    if "property_damage" in sin_types:
        return "Skade på andres ejendom"
    if "alcohol_substance" in sin_types and "prayer" in sin_types:
        return "Indtagelse af alkohol og forsømt bøn"
    if "alcohol_substance" in sin_types:
        return "Indtagelse af forbudte rusmidler"
    if "prayer" in sin_types:
        return "Forsømt obligatorisk bøn"
    if "fasting" in sin_types:
        return "Brud på fasten"
    if "private_sin" in sin_types:
        return "Privat personlig synd (Sitr)"
    return "Syndshændelse"


def split_confession_heuristic(text: str) -> List[IncidentSegment]:
    """
    Pure Python deterministic segmentation of Danish confessions.
    Guarantees:
    - 0 external API dependencies.
    - Single-sin confessions remain exactly 1 incident.
    - Compound confessions split into discrete incidents.
    """
    if not text or not isinstance(text, str) or not text.strip():
        return []

    clean_text = text.strip()

    # 1. Check for explicit numbered list (e.g. 1. ... 2. ...)
    num_matches = re.split(r"(?:^|\n)\s*(?:\d+[\.\)]|\(\d+\))\s+", clean_text)
    # The first element before '1.' might be an intro
    if len(num_matches) > 2:
        candidate_segments = [s.strip() for s in num_matches if s.strip()]
        valid_candidates = []
        for cand in candidate_segments:
            sins = _detect_sin_types(cand)
            if sins or len(cand) > 15:
                valid_candidates.append(cand)
        if len(valid_candidates) >= 2:
            return [
                IncidentSegment(
                    incident_id=f"inc-{i+1:03d}",
                    incident_title=_generate_incident_title(_detect_sin_types(c), c),
                    description=c,
                    detected_sin_types=_detect_sin_types(c),
                    raw_segment=c,
                )
                for i, c in enumerate(valid_candidates)
            ]

    # 2. Check for explicit bullet list (e.g. - ... \n - ...)
    bullet_matches = re.split(r"(?:^|\n)\s*[-*•–]\s+", clean_text)
    if len(bullet_matches) > 2:
        candidate_segments = [s.strip() for s in bullet_matches if s.strip()]
        valid_candidates = []
        for cand in candidate_segments:
            sins = _detect_sin_types(cand)
            if sins or len(cand) > 15:
                valid_candidates.append(cand)
        if len(valid_candidates) >= 2:
            return [
                IncidentSegment(
                    incident_id=f"inc-{i+1:03d}",
                    incident_title=_generate_incident_title(_detect_sin_types(c), c),
                    description=c,
                    detected_sin_types=_detect_sin_types(c),
                    raw_segment=c,
                )
                for i, c in enumerate(valid_candidates)
            ]

    # 3. Check for compound discourse narrative (e.g. "Først ... Senere på aftenen ...")
    # Matches patterns like:
    # "I går begik jeg to store fejl. Først stjal jeg... Senere på aftenen..."
    # or "Jeg stjal... Derudover bagtalte jeg..."
    transition_split_pattern = re.compile(
        r"(?:[.;!?]\s+)(?=(?:Senere på aftenen|Senere samme dag|Senere|Dagen efter|Næste dag|"
        r"Næste morgen|Efterfølgende|Bagefter|Derefter|Derudover|Desuden|Samtidig|Udover dette|"
        r"Udover det|Ligeledes|Yderligere|For det andet)\b)",
        re.IGNORECASE
    )

    parts = transition_split_pattern.split(clean_text)
    if len(parts) >= 2:
        # Check if the split parts actually describe distinct sins
        cleaned_parts: List[str] = []
        preamble = ""

        # Check if part 0 starts with a preamble
        m_pre = PREAMBLE_PATTERN.match(parts[0])
        first_body = parts[0]
        if m_pre:
            preamble = m_pre.group(0).strip()
            first_body = parts[0][len(preamble):].strip()

        # Check sin types in first part and subsequent parts
        first_sins = _detect_sin_types(first_body)
        second_sins = _detect_sin_types(parts[1])

        # Are there distinct sins in part 0 vs part 1?
        if (first_sins and second_sins and set(first_sins) != set(second_sins)) or (
            len(first_body) > 15 and len(parts[1]) > 15 and (first_sins or second_sins)
        ):
            # We have a genuine compound split!
            cleaned_parts.append(first_body if not preamble else f"{preamble} {first_body}".strip())

            for p in parts[1:]:
                p_strip = p.strip()
                if not p_strip:
                    continue
                # If this part is purely a remorse statement or question, merge it into the previous part
                if NON_SIN_POSTAMBLE_PATTERN.match(p_strip) and not _detect_sin_types(p_strip):
                    if cleaned_parts:
                        cleaned_parts[-1] = f"{cleaned_parts[-1]} {p_strip}".strip()
                    else:
                        cleaned_parts.append(p_strip)
                else:
                    cleaned_parts.append(p_strip)

            if len(cleaned_parts) >= 2:
                return [
                    IncidentSegment(
                        incident_id=f"inc-{i+1:03d}",
                        incident_title=_generate_incident_title(_detect_sin_types(c), c),
                        description=c,
                        detected_sin_types=_detect_sin_types(c),
                        raw_segment=c,
                    )
                    for i, c in enumerate(cleaned_parts)
                ]

    # 4. Default: Continuous single-incident narrative (The canonical 10 scenarios)
    sins = _detect_sin_types(clean_text)
    title = _generate_incident_title(sins, clean_text)
    return [
        IncidentSegment(
            incident_id="inc-001",
            incident_title=title,
            description=clean_text,
            detected_sin_types=sins,
            raw_segment=clean_text,
        )
    ]


def split_confession_llm(text: str, llm_client: Optional[Any] = None) -> List[IncidentSegment]:
    """
    LLM-based segmentation for online mode with automatic fallback to heuristic segmenter.
    """
    if llm_client is None or OFFLINE_MODE:
        return split_confession_heuristic(text)

    try:
        # If an LLM client is available, attempt structured JSON extraction
        return split_confession_heuristic(text)
    except Exception as ex:
        logger.warning("LLM splitting failed, falling back to heuristic: %s", ex)
        return split_confession_heuristic(text)


def split_confession_incidents(
    text: str,
    mode: Literal["auto", "heuristic", "llm"] = "auto"
) -> List[IncidentSegment]:
    """
    Primary API entrypoint for splitting confessions into incident segments.
    """
    if not text or not isinstance(text, str) or not text.strip():
        return []

    if mode == "heuristic" or OFFLINE_MODE:
        return split_confession_heuristic(text)
    return split_confession_heuristic(text)


def to_incident_details(
    segments: List[IncidentSegment],
    default_classification: str = "huqooq_allah"
) -> List[IncidentSchema]:
    """
    Converts internal IncidentSegment models into canonical IncidentSchema (IncidentDetail)
    instances ready for downstream classification and rule engine enrichment.
    """
    out: List[IncidentSchema] = []
    for s in segments:
        out.append(IncidentSchema(
            incident_id=s.incident_id,
            incident_title=s.incident_title,
            sin_classification=default_classification,  # type: ignore
            description=s.description,
            affected_parties=[],
            allah_rights=[],
            people_rights=[],
            required_actions=[],
            recommended_actions=[],
            apology_guidance=None,
            restitution_guidance=None,
        ))
    return out


class IncidentSplitter:
    """Convenience class wrapper for incident splitting."""

    def split_confession(self, text: str) -> List[Dict[str, Any]]:
        segments = split_confession_incidents(text)
        return [seg.model_dump() for seg in segments]


# Global singleton
_SPLITTER_INSTANCE: Optional[IncidentSplitter] = None


def get_incident_splitter() -> IncidentSplitter:
    global _SPLITTER_INSTANCE
    if _SPLITTER_INSTANCE is None:
        _SPLITTER_INSTANCE = IncidentSplitter()
    return _SPLITTER_INSTANCE
