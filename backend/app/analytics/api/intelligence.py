"""FastAPI routes for VALORA Intelligence (Weekly briefing, Priority recommendations, Ask VALORA, Signals export)."""
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.schemas.intelligence import (
    AskValoraRequest,
    AskValoraResponse,
    EstateIntelligenceResponse,
    EstateSignalsExport,
    IngestIntelligencePayload,
)
from app.analytics.services.intelligence_service import IntelligenceService
from app.db.session import get_db
from app.identity.api.dependencies import CurrentUser, get_current_user_optional
from app.identity.models.user import User

router = APIRouter(prefix="/intelligence", tags=["analytics"])


@router.get("", response_model=EstateIntelligenceResponse)
async def get_estate_intelligence(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
) -> EstateIntelligenceResponse:
    """Fetch the weekly executive briefing and priority recommendations for the specified estate."""
    return await IntelligenceService(db).get_intelligence(estate_id, current_user)


@router.post("/ask", response_model=AskValoraResponse)
async def ask_valora_endpoint(
    payload: AskValoraRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
) -> AskValoraResponse:
    """Ask VALORA a natural language question scoped to the selected estate."""
    return await IntelligenceService(db).ask_valora(
        estate_id=payload.estate_id,
        question=payload.question,
        actor=current_user,
    )


@router.get("/signals", response_model=EstateSignalsExport)
async def export_estate_signals(
    db: Annotated[AsyncSession, Depends(get_db)],
    estate_id: Annotated[int, Query(gt=0)],
    current_user: Annotated[User | None, Depends(get_current_user_optional)] = None,
    x_valora_secret: Annotated[str | None, Header(alias="X-Valora-Secret")] = None,
) -> EstateSignalsExport:
    """Export operational signals for n8n workflow synthesis.
    
    Accepts either an HOA admin session or an internal service secret header.
    """
    return await IntelligenceService(db).get_estate_signals(
        estate_id=estate_id,
        actor=current_user,
        internal_key=x_valora_secret,
    )


@router.post("/briefing")
async def ingest_intelligence_briefing(
    estate_id: Annotated[int, Query(gt=0)],
    payload: IngestIntelligencePayload,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_user_optional)] = None,
    x_valora_secret: Annotated[str | None, Header(alias="X-Valora-Secret")] = None,
) -> dict[str, str | int]:
    """Ingest a generated weekly briefing and recommendations payload from n8n."""
    await IntelligenceService(db).ingest_intelligence(
        estate_id=estate_id,
        payload=payload,
        actor=current_user,
        internal_key=x_valora_secret,
    )
    return {"status": "ok", "estate_id": estate_id}
