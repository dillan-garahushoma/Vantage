from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.contact.schemas.contact import ContactRequest, ContactResponse
from app.contact.services.contact_service import ContactService
from app.db.session import get_db

router = APIRouter(prefix="/contact", tags=["contact"])


@router.post("", response_model=ContactResponse, status_code=201)
async def submit_contact_message(
    payload: ContactRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ContactResponse:
    return await ContactService(db).submit(payload)
