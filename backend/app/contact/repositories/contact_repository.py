from sqlalchemy.ext.asyncio import AsyncSession

from app.contact.models.contact_message import ContactMessage


class ContactRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        *,
        name: str,
        email: str,
        phone: str | None,
        subject: str | None,
        message: str,
    ) -> ContactMessage:
        contact_message = ContactMessage(
            name=name,
            email=email,
            phone=phone,
            subject=subject,
            message=message,
        )
        self._db.add(contact_message)
        await self._db.commit()
        await self._db.refresh(contact_message)
        return contact_message
