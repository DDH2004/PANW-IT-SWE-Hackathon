from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models.transaction import Transaction
from datetime import datetime, timedelta
import pandas as pd

try:
    from prophet import Prophet  # type: ignore
    _PROPHET_AVAILABLE = True
except Exception:  # pragma: no cover
    _PROPHET_AVAILABLE = False

router = APIRouter()

@router.get('/forecast')
async def forecast(
    db: Session = Depends(get_db),
    method: str = Query("auto", description="auto|prophet|simple"),
    horizon_days: int = Query(90, ge=14, le=365)
):
    """Return spend forecast using Prophet (if available & sufficient data) or a simple heuristic.

    - prophet: Daily spend (expenses only) aggregated & forecasted forward horizon_days.
    - simple: Uses average daily spend last 30 days * horizon.
    Response always includes legacy annual projection key for backward compatibility.
    """
    txns = db.query(Transaction).all()
    if not txns:
        return {"annual_spend_projection": 0, "forecast_method": None, "daily_forecast": []}

    # Build DataFrame
    rows = []
    for t in txns:
        # Consider only expenses (amount < 0) as spend; income excluded
        if t.amount < 0:
            rows.append({"ds": pd.to_datetime(t.date), "y": float(-t.amount)})  # positive spend value
    if not rows:
        return {"annual_spend_projection": 0, "forecast_method": None, "daily_forecast": []}
    df = pd.DataFrame(rows)
    # Aggregate duplicates per day
    df = df.groupby('ds', as_index=False)['y'].sum().sort_values('ds')

    # Compute simple metrics for fallback & annual projection
    today = datetime.utcnow().date()
    last_30_cutoff = today - timedelta(days=30)
    last_30 = df[df['ds'].dt.date > last_30_cutoff]
    avg_daily_last_30 = last_30['y'].mean() if not last_30.empty else df['y'].mean()
    simple_annual_projection = (avg_daily_last_30 or 0) * 365

    use_prophet = False
    reason = ""
    if method in ("auto", "prophet"):
        if not _PROPHET_AVAILABLE:
            reason = "prophet_not_installed"
        elif len(df) < 25:  # need a minimum number of daily points
            reason = "insufficient_history"
        else:
            use_prophet = True

    if use_prophet:
        try:
            m = Prophet(daily_seasonality=True, weekly_seasonality=True, yearly_seasonality=False)
            m.fit(df)
            future = m.make_future_dataframe(periods=horizon_days)
            fc = m.predict(future)
            # Keep only future (and maybe recent past for context)
            fc_future = fc[fc['ds'] > df['ds'].max()].copy()
            # Summaries
            next_30_end = df['ds'].max() + pd.Timedelta(days=30)
            next_60_end = df['ds'].max() + pd.Timedelta(days=60)
            next_90_end = df['ds'].max() + pd.Timedelta(days=90)
            def window_sum(end):
                return float(fc_future[fc_future['ds'] <= end]['yhat'].sum())
            result = {
                "forecast_method": "prophet",
                "reason": reason or None,
                "horizon_days": horizon_days,
                "annual_spend_projection": simple_annual_projection,  # keep legacy style (heuristic)
                "next_30d_spend": round(window_sum(next_30_end),2),
                "next_60d_spend": round(window_sum(next_60_end),2),
                "next_90d_spend": round(window_sum(next_90_end),2),
                "daily_forecast": [
                    {
                        "date": r.ds.date().isoformat(),
                        "predicted_spend": round(float(r.yhat), 2),
                        "lower": round(float(r.yhat_lower), 2),
                        "upper": round(float(r.yhat_upper), 2)
                    }
                    for _, r in fc_future.head(horizon_days).iterrows()
                ]
            }
            return result
        except Exception as e:  # fallback silently
            reason = f"prophet_error:{type(e).__name__}"  # pragma: no cover

    # Simple fallback method
    next_30 = avg_daily_last_30 * 30
    next_60 = avg_daily_last_30 * 60
    next_90 = avg_daily_last_30 * 90
    simple_daily = []
    base_date = df['ds'].max()
    for i in range(1, horizon_days+1):
        d = (base_date + pd.Timedelta(days=i)).date().isoformat()
        simple_daily.append({"date": d, "predicted_spend": round(float(avg_daily_last_30),2)})
    return {
        "forecast_method": "simple" if method != "prophet" else "prophet_fallback",
        "reason": reason or None,
        "horizon_days": horizon_days,
        "annual_spend_projection": simple_annual_projection,
        "next_30d_spend": round(float(next_30),2),
        "next_60d_spend": round(float(next_60),2),
        "next_90d_spend": round(float(next_90),2),
        "daily_forecast": simple_daily
    }
