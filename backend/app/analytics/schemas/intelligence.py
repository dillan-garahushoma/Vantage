"""Pydantic schemas for the VALORA Intelligence layer.

Defines the exact contracts for:
- Weekly executive briefings
- Evidence-based maintenance priorities (overdue jobs, then urgent complaints)
- Ask VALORA structured Q&A
- Estate-authorized operational metadata export
- Role-adaptive briefings (Resident, Service Provider, HOA Admin)
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

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
    confidence_value: int | None = Field(default=None, serialization_alias="confidenceValue")
    impact: str
    savings_zar: float | None = Field(default=None, serialization_alias="savingsZar")
    suggested_action: str = Field(..., serialization_alias="suggestedAction")
    work_order_defaults: WorkOrderDefaults = Field(..., serialization_alias="workOrderDefaults")


class WeeklyBriefing(BaseModel):
    model_config = _DTO_CONFIG

    headline: str
    body: str
    window_label: str = Field(..., serialization_alias="windowLabel")
    signals_reviewed: int = Field(..., serialization_alias="signalsReviewed")
    sources: int
    avoidable_zar: float | None = Field(default=None, serialization_alias="avoidableZar")


class OperationalSignalCounts(BaseModel):
    model_config = _DTO_CONFIG

    open_complaints: int = 0
    work_orders_in_flight: int = 0
    unresolved_incidents: int = 0


class ResidentUnitIssue(BaseModel):
    model_config = _DTO_CONFIG

    id: int | str
    title: str
    status: str
    logged_date: str
    category: str


class ResidentIntelligenceView(BaseModel):
    model_config = _DTO_CONFIG

    unit_issues: list[ResidentUnitIssue] = Field(default_factory=list)
    living_score_label: str = "Good"
    living_score_summary: str = ""
    community_notices: list[str] = Field(default_factory=list)


class ProviderWorkOrderSummary(BaseModel):
    model_config = _DTO_CONFIG

    id: int | str
    title: str
    priority: str
    status: str
    location: str
    due_date: str | None = None


class ProviderIntelligenceView(BaseModel):
    model_config = _DTO_CONFIG

    assigned_work_orders: list[ProviderWorkOrderSummary] = Field(default_factory=list)
    pending_count: int = 0
    urgent_count: int = 0
    instructions: str = ""


class EstateIntelligenceResponse(BaseModel):
    model_config = _DTO_CONFIG

    estate_id: int
    estate_name: str
    as_of: datetime
    briefing: WeeklyBriefing
    recommendations: list[PriorityRecommendation]
    operational_signals: OperationalSignalCounts
    source: Literal["n8n", "live_llm", "sample_baseline", "stored_records"]
    briefing_id: int | None = None
    template_version: str = "operational-v1"
    data_origin: Literal['demo', 'live'] = 'live'
    facts: dict = Field(default_factory=dict)
    evidence: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    role: str = "hoa_admin"
    resident_view: ResidentIntelligenceView | None = None
    provider_view: ProviderIntelligenceView | None = None


class AskValoraRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]
    estate_id: int = Field(..., gt=0, le=2147483647)


class AskValoraResponse(BaseModel):
    model_config = _DTO_CONFIG

    summary: str
    evidence: list[str] = Field(default_factory=list)
    recommendation: str = ""
    related: list[str] = Field(default_factory=list)
    source: Literal["n8n", "estate-domain", "llm"]
    as_of: datetime | None = None
    estate_id: int | None = None
    limitations: list[str] = Field(default_factory=list)


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
    limit_per_type: int = 50
    scope: str = 'Recent record metadata only; counts cover all matching records.'
