from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.models import AIAnalytic

router = APIRouter()

class AIAnalyticCreate(BaseModel):
    property_id: int
    predicted_market_value: Optional[float] = None
    rental_yield_pct: Optional[float] = None
    growth_score: Optional[float] = None
    ten_year_roi: Optional[float] = None
    model_version: Optional[str] = "v1.0"
    confidence_score: Optional[float] = None
    actual_market_value: Optional[float] = None
    inference_time_ms: Optional[int] = None
    input_features_used: Optional[str] = None
    is_validated: Optional[bool] = False

# Update schema
class AIAnalyticUpdate(BaseModel):
    predicted_market_value: Optional[float] = None
    rental_yield_pct: Optional[float] = None
    growth_score: Optional[float] = None
    ten_year_roi: Optional[float] = None
    confidence_score: Optional[float] = None
    actual_market_value: Optional[float] = None
    is_validated: Optional[bool] = None

@router.get("/api/ai_analytics")
def get_all_ai_analytics(db: Session = Depends(get_db)):
    analytics = db.query(AIAnalytic).all()
    return {"count": len(analytics), "analytics": analytics}

@router.get("/api/ai_analytics/{analytics_id}")
def get_ai_analytic(analytics_id: int, db: Session = Depends(get_db)):
    analytic = db.query(AIAnalytic).filter(AIAnalytic.analytics_id == analytics_id).first()
    if not analytic:
        raise HTTPException(status_code=404, detail="AI Analytics record not found")
    return analytic

@router.get("/api/ai_analytics/property/{property_id}")
def get_ai_analytics_by_property(property_id: int, db: Session = Depends(get_db)):
    analytics = db.query(AIAnalytic).filter(AIAnalytic.property_id == property_id).all()
    return {"count": len(analytics), "analytics": analytics}

@router.post("/api/ai_analytics")
def create_ai_analytic(analytic: AIAnalyticCreate, db: Session = Depends(get_db)):
    new_analytic = AIAnalytic(
        property_id = analytic.property_id,
        predicted_market_value = analytic.predicted_market_value,
        rental_yield_pct = analytic.predicted_market_value,
        growth_score = analytic.growth_score,
        ten_year_roi = analytic.ten_year_roi,
        model_version = analytic.model_version,
        confidence_score = analytic.confidence_score,
        actual_market_value = analytic.actual_market_value,
        inference_time_ms = analytic.inference_time_ms,
        input_features_used = analytic.input_features_used,
        is_validated = analytic.is_validated
    )
    db.add(new_analytic)
    db.commit()
    db.refresh(new_analytic)
    return {"message": "AI Analytics record created successfully", "analytics": new_analytic}

@router.put("/api/ai_analytics/{analytics_id}")
def updated_ai_analytic(analytics_id: int, analytic_update: AIAnalyticUpdate, db: Session = Depends(get_db)):
    analytic = db.query(AIAnalytic).filter(AIAnalytic.analytics_id == analytics_id).first()
    if not analytic:
        raise HTTPException(status_code=404, detail="AI Analytics record not found")

    # update only provided fields
    if analytic_update.predicted_market_value is not None:
        analytic.predicted_market_value = analytic_update.predicted_market_value
    if analytic_update.rental_yield_pct is not None:
        analytic.rental_yield_pct = analytic_update.rental_yield_pct
    if analytic_update.growth_score is not None:
        analytic.growth_score = analytic_update.growth_score
    if analytic_update.ten_year_roi is not None:
        analytic.ten_year_roi = analytic_update.ten_year_roi
    if analytic_update.confidence_score is not None:
        analytic.confidence_score = analytic_update.confidence_score
    if analytic_update.actual_market_value is not None:
        analytic.actual_market_value = analytic_update.actual_market_value
    if analytic_update.is_validated is not None:
        analytic.is_validated = analytic_update.is_validated

    db.commit()
    db.refresh(analytic)
    return {"message": "AI Analytics record updated successfully", "analytic": analytic}

@router.delete("/api/ai_analytics/{analytics_id}")
def delete_ai_analytic(analytics_id: int, db: Session = Depends(get_db)):
    analytic = db.query(AIAnalytic).filter(AIAnalytic.analytics_id == analytics_id).first()
    if not analytic:
        raise HTTPException(status_code=404, detail="AI Analytics record not found")

    db.delete(analytic)
    db.commit()
    return {"message": "AI Analytics record deleted successfully"}

