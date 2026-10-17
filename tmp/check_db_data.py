import asyncio
from sqlalchemy import text
from app.db.session import engine

async def check():
    async with engine.connect() as conn:
        print("=== ESTATES IN DB ===")
        res = await conn.execute(text("SELECT estate_id, name, is_demo, is_public, show_living_score, created_at FROM estates ORDER BY estate_id"))
        estates = res.fetchall()
        for e in estates:
            print(f"Estate {e.estate_id}: {e.name} (demo={e.is_demo}, public={e.is_public}, score_visible={e.show_living_score})")

        demo_estate_ids = [e.estate_id for e in estates if e.estate_id >= 4]
        print(f"\nDemo estate IDs: {demo_estate_ids}")

        for eid in demo_estate_ids:
            name = next(e.name for e in estates if e.estate_id == eid)
            units = (await conn.execute(text("SELECT count(*) FROM properties WHERE estate_id = :eid"), {"eid": eid})).scalar()
            members = (await conn.execute(text("SELECT count(*) FROM estate_memberships WHERE estate_id = :eid"), {"eid": eid})).scalar()
            residents = (await conn.execute(text("SELECT count(*) FROM estate_memberships WHERE estate_id = :eid AND membership_role = 'resident'"), {"eid": eid})).scalar()
            admins = (await conn.execute(text("SELECT count(*) FROM estate_memberships WHERE estate_id = :eid AND membership_role = 'hoa_admin'"), {"eid": eid})).scalar()
            join_codes = (await conn.execute(text("SELECT count(*) FROM estate_join_codes WHERE estate_id = :eid AND revoked_at IS NULL"), {"eid": eid})).scalar()
            
            complaints_total = (await conn.execute(text("SELECT count(*) FROM complaints WHERE estate_id = :eid"), {"eid": eid})).scalar()
            complaints_resolved = (await conn.execute(text("SELECT count(*) FROM complaints WHERE estate_id = :eid AND status = 'resolved'"), {"eid": eid})).scalar()
            complaint_events = (await conn.execute(text("SELECT count(*) FROM complaint_events ce JOIN complaints c ON ce.complaint_id = c.complaint_id WHERE c.estate_id = :eid"), {"eid": eid})).scalar()
            ai_sugg = (await conn.execute(text("SELECT count(*) FROM complaint_ai_suggestions cas JOIN complaints c ON cas.complaint_id = c.complaint_id WHERE c.estate_id = :eid"), {"eid": eid})).scalar()
            
            wos_total = (await conn.execute(text("SELECT count(*) FROM maintenance_work_orders WHERE estate_id = :eid"), {"eid": eid})).scalar()
            wos_completed = (await conn.execute(text("SELECT count(*) FROM maintenance_work_orders WHERE estate_id = :eid AND status = 'completed'"), {"eid": eid})).scalar()
            ratings_count = (await conn.execute(text("SELECT count(*) FROM maintenance_work_orders WHERE estate_id = :eid AND resident_rating IS NOT NULL"), {"eid": eid})).scalar()
            avg_rating = (await conn.execute(text("SELECT avg(resident_rating) FROM maintenance_work_orders WHERE estate_id = :eid AND resident_rating IS NOT NULL"), {"eid": eid})).scalar()
            
            incidents = (await conn.execute(text("SELECT count(*) FROM security_incidents WHERE estate_id = :eid"), {"eid": eid})).scalar()
            announcements = (await conn.execute(text("SELECT count(*) FROM announcements WHERE estate_id = :eid"), {"eid": eid})).scalar()
            photos = (await conn.execute(text("SELECT count(*) FROM estate_photos WHERE estate_id = :eid"), {"eid": eid})).scalar()
            featured_photos = (await conn.execute(text("SELECT count(*) FROM estate_photos WHERE estate_id = :eid AND position = 0"), {"eid": eid})).scalar()
            
            scores = (await conn.execute(text("SELECT count(*) FROM living_score_snapshots WHERE estate_id = :eid"), {"eid": eid})).scalar()
            latest_score = (await conn.execute(text(
                "SELECT overall_score, status, as_of, resolution_score, frequency_score, security_score, satisfaction_score, infrastructure_score "
                "FROM living_score_snapshots WHERE estate_id = :eid ORDER BY as_of DESC LIMIT 1"
            ), {"eid": eid})).fetchone()

            print(f"\n==========================================")
            print(f"Estate {eid}: {name}")
            print(f"==========================================")
            print(f"  Units: {units}")
            print(f"  Memberships: {members} (HOA Admins: {admins}, Residents: {residents})")
            print(f"  Active Join Codes: {join_codes}")
            print(f"  Complaints: {complaints_total} (Resolved: {complaints_resolved}, Open: {complaints_total - complaints_resolved})")
            print(f"  Complaint Audit Events: {complaint_events}")
            print(f"  Complaint AI Suggestions: {ai_sugg}")
            print(f"  Work Orders: {wos_total} (Completed: {wos_completed}, Pending/Assigned: {wos_total - wos_completed})")
            print(f"  Work Order Ratings: {ratings_count} rated (Average: {float(avg_rating or 0):.2f})")
            print(f"  Security Incidents: {incidents}")
            print(f"  Announcements: {announcements}")
            print(f"  Photos: {photos} (Featured Hero: {featured_photos})")
            if latest_score:
                print(f"  Latest Living Score: {latest_score.overall_score} (status: {latest_score.status}, as_of: {latest_score.as_of})")
                print(f"    - Resolution:     {latest_score.resolution_score}")
                print(f"    - Frequency:      {latest_score.frequency_score}")
                print(f"    - Security:       {latest_score.security_score}")
                print(f"    - Satisfaction:   {latest_score.satisfaction_score}")
                print(f"    - Infrastructure: {latest_score.infrastructure_score}")
                print(f"    Total Snapshots in History: {scores}")

if __name__ == "__main__":
    asyncio.run(check())
