from sqlalchemy.ext.asyncio import AsyncSession

from app.contact.repositories.contact_repository import ContactRepository
from app.contact.schemas.contact import ContactRequest, ContactResponse


class ContactService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = ContactRepository(db)

    async def submit(self, payload: ContactRequest) -> ContactResponse:
        contact_message = await self._repo.create(
            name=payload.name.strip(),
            email=str(payload.email).strip().lower(),
            phone=payload.phone,
            subject=payload.subject,
            message=payload.message.strip(),
        )
        return ContactResponse.model_validate(contact_message)
