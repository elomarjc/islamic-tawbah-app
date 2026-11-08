"""
app/schemas.py

Pydantic v2 schemas strictly implementing the R2 contract from PROJECT.md
and test specifications across all 17 required analysis keys.
"""

from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator


SinClassificationType = Literal["huqooq_allah", "huqooq_al_ibad", "both"]
ConfidenceLevelType = Literal["high", "medium", "low"]
LegalRulingType = Literal["wajib", "mustahabb"]
GranularActionType = Literal[
    "tawbah_allah", "restitution", "apology", "rectification",
    "sadaqah", "extra_prayers", "dua", "self_discipline"
]
ActionCategoryType = Literal[
    "wajib",
    "mustahabb",
    "tawbah_allah",
    "restitution",
    "apology",
    "rectification",
    "sadaqah",
    "extra_prayers",
    "dua",
    "self_discipline"
]

WAJIB_ACTION_TYPES = frozenset({"wajib", "tawbah_allah", "restitution", "apology", "rectification"})
MUSTAHABB_ACTION_TYPES = frozenset({"mustahabb", "sadaqah", "extra_prayers", "dua", "self_discipline"})



class QuranReference(BaseModel):
    model_config = ConfigDict(extra="ignore")

    surah: str = Field(..., description="Surah name (e.g. 'Az-Zumar', 'Al-Isra')")
    ayah: int = Field(..., description="Ayah number")
    arabic_text: str = Field(..., description="Arabic text in Uthmani script")
    danish_translation: str = Field(..., description="Verified Danish translation")
    explanation: str = Field(..., description="Tafsir / contextual explanation")


class HadithReference(BaseModel):
    model_config = ConfigDict(extra="ignore")

    collection: str = Field(..., description="Collection name (e.g. 'Sahih al-Bukhari', 'Sahih Muslim')")
    hadith_number: str = Field(..., description="Hadith number as string or reference")
    authenticity_grading: str = Field(..., description="Grading: 'Sahih (Autentisk)', 'Hasan', etc.")
    arabic_text: Optional[str] = Field(None, description="Arabic original text if available")
    danish_translation: str = Field(..., description="Verified Danish translation")
    explanation: str = Field(..., description="Sharh / contextual explanation")


class RecommendedDua(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = Field(..., description="Title of the supplication in Danish")
    arabic_text: str = Field(..., description="Vocalized Arabic text")
    transliteration: str = Field(..., description="Phonetic transliteration")
    danish_translation: str = Field(..., description="Danish meaning and translation")
    source: str = Field(..., description="Authentic reference (e.g. Sahih al-Bukhari 6306)")
    context: str = Field(..., description="Usage context and spiritual virtues")


class ActionItemSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Unique action item identifier")
    category: ActionCategoryType = Field(..., description="Category: wajib, mustahabb, or granular action type")
    description: str = Field(..., description="Clear, non-judgmental action directive in Danish")
    explanation: Optional[str] = Field(None, description="Theological reasoning for this step")
    target_party: Optional[str] = Field(None, description="Allah, person, or organization")
    completed: bool = Field(False, description="Whether the action has been completed")
    action_type: Optional[str] = Field(None, description="Granular fiqh action type (e.g. tawbah_allah, restitution, apology)")
    title: Optional[str] = Field(None, description="Short action item title in Danish")

    @model_validator(mode="after")
    def sync_action_type(self) -> "ActionItemSchema":
        """Synchronizes action_type if only a granular category was supplied."""
        if not self.action_type and self.category not in {"wajib", "mustahabb"}:
            self.action_type = self.category
        return self

    @property
    def legal_category(self) -> Literal["wajib", "mustahabb"]:
        """Resolves canonical legal ruling: 'wajib' or 'mustahabb'."""
        if self.category == "mustahabb" or self.category in MUSTAHABB_ACTION_TYPES:
            return "mustahabb"
        return "wajib"

    @property
    def granular_type(self) -> str:
        """Resolves granular action type."""
        if self.action_type:
            return self.action_type
        if self.category in WAJIB_ACTION_TYPES or self.category in MUSTAHABB_ACTION_TYPES:
            if self.category not in {"wajib", "mustahabb"}:
                return self.category
        return "tawbah_allah" if self.legal_category == "wajib" else "dua"


class IncidentSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    incident_id: str = Field(..., description="Unique incident identifier (e.g. 'inc-001')")
    incident_title: Optional[str] = Field(None, description="Title of the sin incident in Danish")
    sin_classification: SinClassificationType = Field(..., description="Classification of violated rights")
    description: str = Field(..., description="Detailed non-judgmental description in Danish")
    affected_parties: List[str] = Field(default_factory=list, description="List of affected people/entities")
    allah_rights: List[str] = Field(default_factory=list, description="List of violated divine rights")
    people_rights: List[str] = Field(default_factory=list, description="List of violated human rights")
    required_actions: List[ActionItemSchema] = Field(default_factory=list, description="Mandatory actions (Wajib)")
    recommended_actions: List[ActionItemSchema] = Field(default_factory=list, description="Recommended actions (Mustahabb)")
    apology_guidance: Optional[str] = Field(None, description="Guidance on apology and fitnah avoidance")
    restitution_guidance: Optional[str] = Field(None, description="Guidance on financial/property restoration")


IncidentDetail = IncidentSchema


class AnalysisResultSchema(BaseModel):
    """
    Complete 17-field Pydantic schema meeting Requirement R2 contract in PROJECT.md.
    """
    model_config = ConfigDict(extra="ignore")

    incident_summary: str = Field(..., description="1. Non-judgmental Danish summary of the confession")
    incidents: List[IncidentSchema] = Field(default_factory=list, description="2. Atomic segmented incidents")
    sin_classification: SinClassificationType = Field(..., description="3. Overall rights classification")
    allah_rights: List[str] = Field(default_factory=list, description="4. Breakdown of Allah's violated rights")
    people_rights: List[str] = Field(default_factory=list, description="5. Breakdown of people's violated rights")
    affected_parties: List[str] = Field(default_factory=list, description="6. Distinct parties harmed")
    severity_explanation: str = Field(..., description="7. Theological explanation of gravity and consequences")
    required_actions: List[ActionItemSchema] = Field(default_factory=list, description="8. Obligatory corrective checklist (Wajib)")
    recommended_actions: List[ActionItemSchema] = Field(default_factory=list, description="9. Recommended meritorious steps (Mustahabb)")
    apology_guidance: Optional[str] = Field(None, description="10. Apology etiquette and fitnah avoidance rules")
    restitution_guidance: Optional[str] = Field(None, description="11. Restitution / anonymous return guidance")
    quran_references: List[QuranReference] = Field(default_factory=list, description="12. Verified Quranic verses with Arabic & Danish")
    hadith_references: List[HadithReference] = Field(default_factory=list, description="13. Verified authentic Hadiths with grading")
    recommended_duas: List[RecommendedDua] = Field(default_factory=list, description="14. Authentic repentance supplications")
    scholarly_disagreement: Optional[str] = Field(None, description="15. Transparent classical ikhtilaf disclosure")
    confidence_level: ConfidenceLevelType = Field("high", description="16. Confidence in assessment: high/medium/low")
    scholar_consultation_required: bool = Field(False, description="17. Flag if complex matter mandates qualified scholar")
    final_reminder: str = Field(..., description="Closing non-judgmental reminder instilling hope in Allah's mercy")


# REST API Request & Response Schemas

class TextConfessionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    text: str = Field(..., description="Confession text in Danish")
    consent: bool = Field(..., description="Explicit user consent to process confession")


class ActionToggleRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    completed: bool = Field(..., description="Target completion status")


class JournalCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    content: str = Field(..., description="Reflection content")
    title: Optional[str] = Field(None, description="Reflection title")
    tags: List[str] = Field(default_factory=list, description="Spiritual tags")


class UserRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=4)
    email: Optional[str] = None


class UserLoginRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    username: str
    password: str


class TokenResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    access_token: str
    token_type: str = "bearer"
    user_id: Optional[str] = None
    username: Optional[str] = None
    is_guest: bool = False


class WipeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: str
    message: str
    confessions_purged: int
    journal_purged: int
    account_deleted: bool
