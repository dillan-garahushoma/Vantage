"""Pydantic schemas for the VALORA Intelligence layer.

Defines the exact contracts for:
- Weekly executive briefings
- Priority recommendations (ordered by expected cost avoidance)
- Ask VALORA structured Q&A
- Operational signals export for n8n workflow ingestion
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RecommendationKind = Literal[
    "PREVENTIVE MAINTENANCE",
    "EMERGING SERVICE RISK",
    "BUDGET & PROVIDER OPTIMISATION",
]

RecommendationConfidence = Literal["High", "Medium", "Low"]

_DTO_CONFIG = ConfigDict(
    from_attributes=True,
    populate_by_name=True,
    serialize_by_alias=True,
)


class RecommendationEvidence(BaseModel):
    model_config = _DTO_CONFIG

    label: str
    detail: str = ""
    source: str = ""


class WorkOrderDefaults(BaseModel):
    model_config = _DTO_CONFIG

    title: str
    asset: str | None = None
    provider: str | None = None
    priority: Literal["urgent", "high", "medium", "low"] = "medium"
    asset_class: str | None = Field(default=None, serialization_alias="assetClass")
    location: str | None = None
    cost_zar: float | None = Field(default=None, serialization_alias="costZar")
    description: str | None = None


class PriorityRecommendation(BaseModel):
    model_config = _DTO_CONFIG

    id: str
    kind: RecommendationKind
    title: str
    summary: str
    evidence: list[RecommendationEvidence] = Field(default_factory=list)
    confidence: RecommendationConfidence
    confidence_value: int = Field(..., serialization_alias="confidenceValue")
    impact: str
    savings_zar: float = Field(..., serialization_alias="savingsZar")
    suggested_action: str = Field(..., serialization_alias="suggestedAction")
    work_order_defaults: WorkOrderDefaults = Field(..., serialization_alias="workOrderDefaults")


class WeeklyBriefing(BaseModel):
    model_config = _DTO_CONFIG

    headline: str
    body: str
    window_label: str = Field(..., serialization_alias="windowLabel")
    signals_reviewed: int = Field(..., serialization_alias="signalsReviewed")
    sources: int
    avoidable_zar: float = Field(..., serialization_alias="avoidableZar")


class OperationalSignalCounts(BaseModel):
    model_config = _DTO_CONFIG

    open_complaints: int = 0
    work_orders_in_flight: int = 0
    unresolved_incidents: int = 0


class EstateIntelligenceResponse(BaseModel):
    model_config = _DTO_CONFIG

    estate_id: int
    estate_name: str
    as_of: datetime
    briefing: WeeklyBriefing
    recommendations: list[PriorityRecommendation]
    operational_signals: OperationalSignalCounts
    source: Literal["n8n", "live_llm", "sample_baseline"]


class AskValoraRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=3, max_length=500)
    estate_id: int = Field(..., gt=0)


class AskValoraResponse(BaseModel):
    model_config = _DTO_CONFIG

    summary: str
    evidence: list[str] = Field(default_factory=list)
    recommendation: str = ""
    related: list[str] = Field(default_factory=list)
    source: Literal["n8n", "estate-domain", "llm"]


class IngestIntelligencePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    briefing: WeeklyBriefing
    recommendations: list[PriorityRecommendation]


class EstateSignalItem(BaseModel):
    model_config = _DTO_CONFIG

    type: Literal["complaint", "work_order", "incident", "telemetry", "living_score"]
    id: int | str
    title: str
    status: str
    date: str
    detail: str


class EstateSignalsExport(BaseModel):
    model_config = _DTO_CONFIG

    estate_id: int
    estate_name: str
    generated_at: datetime
    counts: OperationalSignalCounts
    signals: list[EstateSignalItem]
