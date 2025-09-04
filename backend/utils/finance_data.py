"""Utilities for curated financial instrument + yield data.

First pass: static seed data; external API hooks can be layered later.
"""
from sqlalchemy.orm import Session
from datetime import date
from backend.models.instrument import Instrument
from backend.models.yield_curve import YieldCurvePoint

DEFAULT_INSTRUMENTS = [
    {"ticker": None, "name": "High-Yield Savings (avg)", "type": "cash", "risk_band": "capital_preservation", "sec_yield_pct": 4.2},
    {"ticker": "UST3M", "name": "3M Treasury Bill", "type": "treasury", "risk_band": "capital_preservation", "sec_yield_pct": 5.1, "duration_years": 0.25},
    {"ticker": "BND", "name": "Total Bond Market ETF", "type": "bond_etf", "risk_band": "conservative_income", "sec_yield_pct": 4.4, "expense_ratio": 0.03, "duration_years": 6.5},
    {"ticker": "AGG", "name": "US Aggregate Bond ETF", "type": "bond_etf", "risk_band": "conservative_income", "sec_yield_pct": 4.2, "expense_ratio": 0.03, "duration_years": 6.0},
    {"ticker": "VTI", "name": "Total US Stock Market ETF", "type": "equity_etf", "risk_band": "growth_equity", "expense_ratio": 0.03, "dividend_yield_pct": 1.4, "volatility_5y": 18.0},
    {"ticker": "VXUS", "name": "Total Intl ex-US ETF", "type": "equity_etf", "risk_band": "growth_equity", "expense_ratio": 0.07, "dividend_yield_pct": 3.0, "volatility_5y": 19.5},
]

def ensure_seed_data(db: Session):
    if db.query(Instrument).count() == 0:
        for rec in DEFAULT_INSTRUMENTS:
            db.add(Instrument(**rec))
        if db.query(YieldCurvePoint).count() == 0:
            today = date.today()
            for m,y in [(3,5.1),(12,4.6),(24,4.2),(60,4.0),(120,4.1)]:
                db.add(YieldCurvePoint(maturity_months=m, yield_pct=y, as_of=today))
        db.commit()

def summarize_yield_curve(db: Session):
    pts = db.query(YieldCurvePoint).all()
    if not pts:
        return "No yield data"
    pts_sorted = sorted(pts, key=lambda p: p.maturity_months)
    parts = [f"{p.maturity_months}m:{p.yield_pct:.2f}%" for p in pts_sorted]
    return "YieldCurve " + ", ".join(parts)

def fetch_recommendation_context(db: Session):
    instruments = db.query(Instrument).all()
    curve_summary = summarize_yield_curve(db)
    by_band = {}
    for inst in instruments:
        by_band.setdefault(inst.risk_band, []).append(inst)
    slim = {}
    for band, lst in by_band.items():
        def score(i):
            y = i.sec_yield_pct or i.dividend_yield_pct or 0
            er = i.expense_ratio or 0.0
            return (y, -er)
        top = sorted(lst, key=score, reverse=True)[:2]
        slim[band] = [
            {
                "ticker": i.ticker,
                "name": i.name,
                "type": i.type,
                "yield_pct": i.sec_yield_pct or i.dividend_yield_pct,
                "expense_ratio": i.expense_ratio,
                "duration_years": i.duration_years,
            } for i in top
        ]
    return curve_summary, slim
