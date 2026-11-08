"""
app/models.py

Domain entity models, dataclasses, and SQLite Row mapping helpers
for the Islamic Tawbah App.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def parse_json_field(value: Any, default: Any = None) -> Any:
    """Safely decodes an SQLite TEXT JSON field into a Python structure."""
    if default is None:
        default = []
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        val_str = value.strip()
        if not val_str:
            return default
        try:
            return json.loads(val_str)
        except json.JSONDecodeError:
            return default
    return default


def dump_json_field(value: Any) -> str:
    """Encodes a Python list/dict into a JSON string for SQLite storage."""
    if value is None:
        return "[]"
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


@dataclass
class User:
    id: str
    username: str
    password_hash: str
    email: Optional[str] = None
    is_guest: bool = False
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_login: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row | Dict[str, Any]) -> User:
        return cls(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            email=row["email"] if "email" in row.keys() else None,
            is_guest=bool(row["is_guest"]),
            is_active=bool(row["is_active"]) if "is_active" in row.keys() else True,
            created_at=row["created_at"],
            last_login=row["last_login"] if "last_login" in row.keys() else None,
        )

    def to_dict(self, include_hash: bool = False) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_guest": self.is_guest,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "last_login": self.last_login,
        }
        if include_hash:
            data["password_hash"] = self.password_hash
        return data


@dataclass
class UserSession:
    token: str
    user_id: str
    created_at: str
    expires_at: str
    is_guest: bool = False

    @classmethod
    def from_row(cls, row: sqlite3.Row | Dict[str, Any]) -> UserSession:
        return cls(
            token=row["token"],
            user_id=row["user_id"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            is_guest=bool(row["is_guest"]) if "is_guest" in row.keys() else False,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token": self.token,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "is_guest": self.is_guest,
        }


@dataclass
class ActionItem:
    id: str
    user_id: str
    confession_id: str
    category: str  # 'wajib' | 'mustahabb'
    description: str
    explanation: Optional[str] = None
    target_party: Optional[str] = None
    completed: bool = False
    incident_id: Optional[str] = None
    action_type: Optional[str] = None
    title: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def from_row(cls, row: sqlite3.Row | Dict[str, Any]) -> ActionItem:
        raw_cat = row["category"]
        raw_action_type = row["action_type"] if "action_type" in row.keys() else None

        # Safe normalization if legacy row stored a granular type in category column
        if raw_cat in {"sadaqah", "extra_prayers", "dua", "self_discipline"}:
            category = "mustahabb"
            action_type = raw_action_type or raw_cat
        elif raw_cat in {"tawbah_allah", "restitution", "apology", "rectification"}:
            category = "wajib"
            action_type = raw_action_type or raw_cat
        else:
            category = raw_cat
            action_type = raw_action_type

        return cls(
            id=row["id"],
            user_id=row["user_id"],
            confession_id=row["confession_id"],
            incident_id=row["incident_id"] if "incident_id" in row.keys() else None,
            category=category,
            action_type=action_type,
            title=row["title"] if "title" in row.keys() else None,
            description=row["description"],
            explanation=row["explanation"] if "explanation" in row.keys() else None,
            target_party=row["target_party"] if "target_party" in row.keys() else None,
            completed=bool(row["completed"]),
            completed_at=row["completed_at"] if "completed_at" in row.keys() else None,
            created_at=row["created_at"] if "created_at" in row.keys() else "",
        )

    @classmethod
    def from_schema(
        cls,
        schema: Any,
        user_id: str,
        confession_id: str,
        incident_id: Optional[str] = None,
    ) -> ActionItem:
        """Constructs an ActionItem entity from an ActionItemSchema, normalizing category to 'wajib'/'mustahabb'."""
        category = getattr(schema, "legal_category", "wajib" if schema.category != "mustahabb" else "mustahabb")
        action_type = getattr(schema, "granular_type", schema.action_type or schema.category)
        return cls(
            id=schema.id,
            user_id=user_id,
            confession_id=confession_id,
            incident_id=incident_id,
            category=category,
            action_type=action_type,
            title=getattr(schema, "title", None),
            description=schema.description,
            explanation=schema.explanation,
            target_party=schema.target_party,
            completed=schema.completed,
        )

    def to_schema_dict(self) -> Dict[str, Any]:
        """Returns a dictionary formatted for ActionItemSchema instantiation."""
        return {
            "id": self.id,
            "category": self.category,
            "action_type": self.action_type,
            "title": self.title,
            "description": self.description,
            "explanation": self.explanation,
            "target_party": self.target_party,
            "completed": self.completed,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "confession_id": self.confession_id,
            "incident_id": self.incident_id,
            "category": self.category,
            "action_type": self.action_type,
            "title": self.title,
            "description": self.description,
            "explanation": self.explanation,
            "target_party": self.target_party,
            "completed": self.completed,
            "completed_at": self.completed_at,
            "created_at": self.created_at,
        }


@dataclass
class Incident:
    id: str
    confession_id: str
    incident_title: str
    sin_classification: str  # 'huqooq_allah' | 'huqooq_al_ibad' | 'both'
    description: str
    affected_parties: List[str] = field(default_factory=list)
    allah_rights: List[str] = field(default_factory=list)
    people_rights: List[str] = field(default_factory=list)
    apology_guidance: Optional[str] = None
    restitution_guidance: Optional[str] = None
    severity_explanation: Optional[str] = None
    incident_order: int = 1
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def from_row(cls, row: sqlite3.Row | Dict[str, Any]) -> Incident:
        return cls(
            id=row["id"],
            confession_id=row["confession_id"],
            incident_order=row["incident_order"] if "incident_order" in row.keys() else 1,
            incident_title=row["incident_title"],
            sin_classification=row["sin_classification"],
            description=row["description"],
            affected_parties=parse_json_field(row["affected_parties"]),
            allah_rights=parse_json_field(row["allah_rights"]),
            people_rights=parse_json_field(row["people_rights"]),
            apology_guidance=row["apology_guidance"] if "apology_guidance" in row.keys() else None,
            restitution_guidance=row["restitution_guidance"] if "restitution_guidance" in row.keys() else None,
            severity_explanation=row["severity_explanation"] if "severity_explanation" in row.keys() else None,
            created_at=row["created_at"] if "created_at" in row.keys() else "",
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "confession_id": self.confession_id,
            "incident_order": self.incident_order,
            "incident_title": self.incident_title,
            "sin_classification": self.sin_classification,
            "description": self.description,
            "affected_parties": self.affected_parties,
            "allah_rights": self.allah_rights,
            "people_rights": self.people_rights,
            "apology_guidance": self.apology_guidance,
            "restitution_guidance": self.restitution_guidance,
            "severity_explanation": self.severity_explanation,
            "created_at": self.created_at,
        }


@dataclass
class Confession:
    id: str
    user_id: str
    raw_input_type: str  # 'text' | 'voice'
    raw_text: str
    transcript: Optional[str] = None
    audio_path: Optional[str] = None
    consent_given: bool = True
    status: str = "completed"
    summary: Optional[str] = None
    sin_classification: Optional[str] = None
    confidence_level: Optional[str] = "high"
    scholar_consultation_required: bool = False
    analysis_json: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def from_row(cls, row: sqlite3.Row | Dict[str, Any]) -> Confession:
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            raw_input_type=row["raw_input_type"],
            raw_text=row["raw_text"],
            transcript=row["transcript"] if "transcript" in row.keys() else None,
            audio_path=row["audio_path"] if "audio_path" in row.keys() else None,
            consent_given=bool(row["consent_given"]) if "consent_given" in row.keys() else True,
            status=row["status"] if "status" in row.keys() else "completed",
            summary=row["summary"] if "summary" in row.keys() else None,
            sin_classification=row["sin_classification"] if "sin_classification" in row.keys() else None,
            confidence_level=row["confidence_level"] if "confidence_level" in row.keys() else "high",
            scholar_consultation_required=bool(row["scholar_consultation_required"]) if "scholar_consultation_required" in row.keys() else False,
            analysis_json=row["analysis_json"] if "analysis_json" in row.keys() else None,
            created_at=row["created_at"] if "created_at" in row.keys() else "",
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "raw_input_type": self.raw_input_type,
            "raw_text": self.raw_text,
            "transcript": self.transcript,
            "audio_path": self.audio_path,
            "consent_given": self.consent_given,
            "status": self.status,
            "summary": self.summary,
            "sin_classification": self.sin_classification,
            "confidence_level": self.confidence_level,
            "scholar_consultation_required": self.scholar_consultation_required,
            "created_at": self.created_at,
        }


@dataclass
class JournalEntry:
    id: str
    user_id: str
    content: str
    title: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row | Dict[str, Any]) -> JournalEntry:
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            title=row["title"] if "title" in row.keys() else None,
            content=row["content"],
            tags=parse_json_field(row["tags"]),
            created_at=row["created_at"] if "created_at" in row.keys() else "",
            updated_at=row["updated_at"] if "updated_at" in row.keys() else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
