import asyncio
from app.db.session import AsyncSessionLocal
from app.analytics.services.estate_living_score_service import LivingScoreService

async def test_living_score_engine():
    async with AsyncSessionLocal() as session:
        service = LivingScoreService(session)
        print("Calculating live Living Score for Estate 4 (Silverleaf Reserve)...")
        snapshot = await service.calculate_and_snapshot(
            estate_id=4,
            actor=None
        )
        print("Living Score calculation success!")
        print(f"  Overall Score:      {snapshot.overall_score}")
        print(f"  Status:             {snapshot.status}")
        print(f"  Measured Weight:    {snapshot.measured_weight}")
        print(f"  Resolution Score:   {snapshot.resolution_score}")
        print(f"  Frequency Score:    {snapshot.frequency_score}")
        print(f"  Security Score:     {snapshot.security_score}")
        print(f"  Satisfaction Score: {snapshot.satisfaction_score}")
        print(f"  Infrastructure:     {snapshot.infrastructure_score}")
        print(f"  Snapshot ID:        {snapshot.snapshot_id}")

if __name__ == "__main__":
    asyncio.run(test_living_score_engine())
