"""FastAPI routes for VALORA Intelligence (Weekly briefing, Priority recommendations, Ask VALORA, Signals export)."""
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.schemas.intelligence import (
    AskValoraRequest,
    AskValoraResponse,
    EstateIntelligenceResponse,
    EstateSignalsExport,
    IngestIntelligencePayload,
)
from app.analytics.services.intelligence_service import IntelligenceService
from app.common.pagination import Page, PaginationParams
from app.db.session import get_db
from app.identity.api.dependencies import CurrentUser, get_current_user_optional
from app.identity.models.user import User

router = APIRouter(prefix="/intelligence", tags=["analytics"])


@router.post('/briefing/generate', response_model=EstateIntelligenceResponse, status_code=201)
async def generate_briefing(
    db: Annotated[AsyncSession, Depends(get_db)], current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0, le=2147483647)],
) -> EstateIntelligenceResponse:
    """Save an immutable summary of authorized stored estate facts."""
    return await IntelligenceService(db).generate(estate_id, current_user)


@router.get('/history', response_model=Page[EstateIntelligenceResponse])
async def intelligence_history(
    db: Annotated[AsyncSession, Depends(get_db)], current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0, le=2147483647)],
    pagination: Annotated[PaginationParams, Depends()],
) -> Page[EstateIntelligenceResponse]:
    return await IntelligenceService(db).history(estate_id, current_user, page=pagination.page, size=pagination.size)


@router.get('/history/{briefing_id}', response_model=EstateIntelligenceResponse)
async def intelligence_history_detail(
    briefing_id: Annotated[int, Path(gt=0, le=2147483647)], db: Annotated[AsyncSession, Depends(get_db)], current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0, le=2147483647)],
) -> EstateIntelligenceResponse:
    return await IntelligenceService(db).get_history(estate_id, briefing_id, current_user)


@router.get("", response_model=EstateIntelligenceResponse)
async def get_estate_intelligence(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0, le=2147483647)],
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
    estate_id: Annotated[int, Query(gt=0, le=2147483647)],
    current_user: Annotated[User | None, Depends(get_current_user_optional)] = None,
    x_valora_secret: Annotated[str | None, Header(alias="X-Valora-Secret")] = None,
) -> EstateSignalsExport:
    """Export operational signals for n8n workflow synthesis.

    Requires an authenticated HOA administrator with matching estate membership.
    """
    return await IntelligenceService(db).get_estate_signals(
        estate_id=estate_id,
        actor=current_user,
        internal_key=x_valora_secret,
    )


@router.post("/briefing")
async def ingest_intelligence_briefing(
    estate_id: Annotated[int, Query(gt=0, le=2147483647)],
    payload: IngestIntelligencePayload,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_user_optional)] = None,
    x_valora_secret: Annotated[str | None, Header(alias="X-Valora-Secret")] = None,
) -> dict[str, str | int]:
    """Accept only the grounded current projection, with estate HOA authorization."""
    await IntelligenceService(db).ingest_intelligence(
        estate_id=estate_id,
        payload=payload,
        actor=current_user,
        internal_key=x_valora_secret,
    )
    return {"status": "ok", "estate_id": estate_id}
