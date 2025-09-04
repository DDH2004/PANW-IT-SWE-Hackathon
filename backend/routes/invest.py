from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models.instrument import Instrument
from backend.models.yield_curve import YieldCurvePoint
from backend.utils.finance_data import ensure_seed_data, fetch_recommendation_context
from backend.utils.summary import build_financial_snapshot
from backend.providers import get_coach_provider, ModelProviderError
from backend.utils.logging import logger

router = APIRouter()

@router.get('/instruments')
async def list_instruments(db: Session = Depends(get_db)):
    ensure_seed_data(db)
    rows = db.query(Instrument).all()
    return [
        {
            'ticker': r.ticker,
            'name': r.name,
            'type': r.type,
            'risk_band': r.risk_band,
            'expense_ratio': r.expense_ratio,
            'yield_pct': r.sec_yield_pct or r.dividend_yield_pct,
            'duration_years': r.duration_years,
            'volatility_5y': r.volatility_5y,
        } for r in rows
    ]

@router.get('/yield_curve')
async def yield_curve(db: Session = Depends(get_db)):
    ensure_seed_data(db)
    pts = db.query(YieldCurvePoint).all()
    return [
        { 'maturity_months': p.maturity_months, 'yield_pct': p.yield_pct, 'as_of': p.as_of.isoformat() } for p in pts
    ]

@router.get('/coach/recommendations')
async def coach_recommendations(db: Session = Depends(get_db)):
    ensure_seed_data(db)
    snapshot = build_financial_snapshot(db)[:800]
    curve_summary, band_map = fetch_recommendation_context(db)
    provider = get_coach_provider()
    prompt = (
        "You are a cautious financial education assistant. Use ONLY the provided instruments. "
        "Do not give personalized investment advice; provide educational options grouped by risk progression. "
        "Include disclaimers about risk and suitability.\n"
        f"USER SNAPSHOT:\n{snapshot}\n"
        f"YIELD SUMMARY: {curve_summary}\n"
        f"INSTRUMENTS JSON: {band_map}\n"
        "Return a concise markdown-style list grouped by risk_band with 1-2 sentences each."
    )
    try:
        resp = await provider.generate(prompt=prompt, model='phi3:mini', fast=True)
    except ModelProviderError as e:
        logger.error("coach_recommendations_failed", error=str(e))
        raise HTTPException(status_code=502, detail=str(e)) from e
    return {"recommendations": resp, "disclaimer": "Educational purposes only; not investment advice.", "bands": band_map, "yield_summary": curve_summary}
