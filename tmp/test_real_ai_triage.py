import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.community.services.complaint_triage_service import ComplaintTriageService
from app.analytics.services.health_brief_service import HealthBriefService
from app.identity.models.user import User
from app.core.config import get_settings

async def run_live_ai_test():
    settings = get_settings()
    print("=== LIVE AI TEST ON ACTUAL DATABASE DATA ===")
    print(f"AI_ENABLED: {settings.AI_ENABLED}")
    print(f"AI_TRIAGE_ENABLED: {settings.AI_TRIAGE_ENABLED}")
    print(f"AI_INSIGHTS_ENABLED: {settings.AI_INSIGHTS_ENABLED}")
    print(f"AI_PROVIDER: {settings.AI_PROVIDER}")
    print(f"AI_MODEL: {settings.AI_MODEL}")

    async with AsyncSessionLocal() as session:
        # Find an open complaint in Estate 4 (Silverleaf Reserve) without an AI suggestion
        stmt = text("""
            SELECT c.complaint_id, c.estate_id, c.category, c.priority, c.description, c.status
            FROM complaints c
            LEFT JOIN complaint_ai_suggestions cas ON c.complaint_id = cas.complaint_id
            WHERE c.estate_id = 4 AND cas.suggestion_id IS NULL AND c.status IN ('submitted', 'reviewed')
            LIMIT 1
        """)
        row = (await session.execute(stmt)).fetchone()
        if not row:
            # Check any estate
            stmt = text("""
                SELECT c.complaint_id, c.estate_id, c.category, c.priority, c.description, c.status
                FROM complaints c
                LEFT JOIN complaint_ai_suggestions cas ON c.complaint_id = cas.complaint_id
                WHERE cas.suggestion_id IS NULL AND c.status IN ('submitted', 'reviewed')
                LIMIT 1
            """)
            row = (await session.execute(stmt)).fetchone()

        if not row:
            print("No un-triaged open complaints found! Checking an existing open complaint...")
            stmt = text("SELECT complaint_id, estate_id, category, priority, description, status FROM complaints WHERE status IN ('submitted', 'reviewed') LIMIT 1")
            row = (await session.execute(stmt)).fetchone()

        print(f"\nTarget Complaint for AI Triage: id={row.complaint_id}, estate={row.estate_id}, cat='{row.category}', pri='{row.priority}', status='{row.status}'")
        print(f"Description: {row.description[:120]}...")

        # Find the HOA admin user for this estate
        admin_row = (await session.execute(
            text("""
                SELECT u.user_id, u.email, u.full_name, u.role
                FROM users u
                JOIN estate_memberships em ON u.user_id = em.user_id
                WHERE em.estate_id = :eid AND em.membership_role = 'hoa_admin'
                LIMIT 1
            """),
            {"eid": row.estate_id}
        )).fetchone()
        admin = User(
            user_id=admin_row.user_id,
            email=admin_row.email,
            full_name=admin_row.full_name,
            role=admin_row.role
        )
        print(f"Acting HOA Admin: {admin.full_name} ({admin.email}, id={admin.user_id})")

        # Test ComplaintTriageService.generate()
        triage_svc = ComplaintTriageService(session, settings=settings)
        print("\n--> Calling ComplaintTriageService.generate()...")
        try:
            triage_res = await triage_svc.generate(
                complaint_id=row.complaint_id,
                estate_id=row.estate_id,
                admin=admin
            )
            print("Triage Response Success!")
            print(f"  Suggested Category: {triage_res.suggested_category}")
            print(f"  Suggested Priority: {triage_res.suggested_priority}")
            print(f"  Suggested Trade:    {triage_res.suggested_trade}")
            print(f"  Provider:           {triage_res.provider}")
            print(f"  Model:              {triage_res.model}")
            print(f"  Prompt Version:     {triage_res.prompt_version}")
        except Exception as e:
            print(f"Triage Exception: {type(e).__name__}: {e}")

        # Check the AI Call Events ledger
        ledger_res = (await session.execute(
            text("""
                SELECT event_id, estate_id, feature, provider, model, status, reason, latency_ms, input_chars, created_at
                FROM ai_call_events
                ORDER BY created_at DESC
                LIMIT 3
            """)
        )).fetchall()
        print("\n--- Recent AI Call Events Ledger ---")
        for ev in ledger_res:
            print(f"  Event {ev.event_id}: estate={ev.estate_id}, feat={ev.feature}, provider={ev.provider}, model={ev.model}, status={ev.status}, reason={ev.reason}, latency={ev.latency_ms}ms, chars={ev.input_chars}")

        # Test HealthBriefService.generate() for estate 4
        print("\n--> Testing HealthBriefService.generate() for Estate 4...")
        brief_svc = HealthBriefService(session, settings=settings)
        try:
            brief_res = await brief_svc.generate(estate_id=4, admin=admin)
            print("Health Brief Response Success!")
            print(f"  Source:           {brief_res.source}")
            print(f"  AI Unavailable:   {brief_res.ai_unavailable_reason}")
            print(f"  Provider:         {brief_res.provider}")
            print(f"  Model:            {brief_res.model}")
            print(f"  Headline:         {brief_res.output.headline}")
            print(f"  Summary:          {brief_res.output.summary[:150]}...")
            print(f"  Drivers:          {brief_res.output.drivers}")
            print(f"  Actions:          {brief_res.output.actions}")
        except Exception as e:
            print(f"Health Brief Exception: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(run_live_ai_test())
