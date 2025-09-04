from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import timedelta
from statistics import mean, pstdev
from backend.db import get_db
from backend.models.transaction import Transaction

router = APIRouter()


def _analyze_merchant(txns):
    """Given list of negative transactions for a single merchant sorted by date."""
    if len(txns) < 2:
        return None
    dates = [t.date for t in txns]
    amounts = [abs(t.amount) for t in txns]
    intervals = [ (dates[i] - dates[i-1]).days for i in range(1, len(dates)) ]
    if not intervals:
        return None
    avg_interval = mean(intervals)
    jitter = pstdev(intervals) if len(intervals) > 1 else 0
    first_amount = amounts[0]
    avg_amount = mean(amounts)
    min_amount, max_amount = min(amounts), max(amounts)
    # Flags
    flags = []
    # Recurring if average interval roughly monthly (25-35 days) OR >=3 charges spanning >=2 months
    distinct_months = { (d.year, d.month) for d in dates }
    if (25 <= avg_interval <= 35 and len(txns) >= 2) or len(distinct_months) >= 2 and len(txns) >= 3:
        flags.append('recurring')
    # Trial conversion: very low / zero first amount then higher subsequent average > first * 2 and first <=1
    if first_amount <= 1 and avg_amount > max(2, first_amount * 2):
        flags.append('trial_converted')
    # Gray charge: small recurring (avg under 15) and recurring flag
    if 'recurring' in flags and avg_amount < 15:
        flags.append('small_recurring')
    # Variable pricing: range > 30% of avg for small recurring
    if avg_amount > 0 and (max_amount - min_amount) / avg_amount > 0.3:
        flags.append('variable_amount')
    # Estimate next charge only if recurring
    next_charge_est = None
    if 'recurring' in flags:
        next_charge_est = dates[-1] + timedelta(days=round(avg_interval))
    return {
        'merchant': txns[0].merchant,
        'occurrences': len(txns),
        'first_date': dates[0].isoformat(),
        'last_date': dates[-1].isoformat(),
        'avg_interval_days': round(avg_interval, 1),
        'interval_jitter_days': round(jitter, 1),
        'avg_amount': round(avg_amount, 2),
        'amount_range': [round(min_amount, 2), round(max_amount, 2)],
        'estimated_next_charge': next_charge_est.isoformat() if next_charge_est else None,
        'flags': flags,
    }


@router.get('/subscriptions')
async def subscriptions(db: Session = Depends(get_db)):
    # Pull negative (expense) transactions with merchant
    rows = db.query(Transaction).filter(Transaction.amount < 0, Transaction.merchant.isnot(None)).all()
    by_merchant = {}
    for t in rows:
        by_merchant.setdefault(t.merchant, []).append(t)
    analyzed = []
    for merchant, txns in by_merchant.items():
        txns.sort(key=lambda t: t.date)
        info = _analyze_merchant(txns)
        if info and ('recurring' in info['flags'] or 'trial_converted' in info['flags']):
            analyzed.append(info)
    # Sort: trial conversions first, then soonest next charge
    analyzed.sort(key=lambda x: (
        0 if 'trial_converted' in x['flags'] else 1,
        x['estimated_next_charge'] or '9999-12-31'
    ))
    return { 'subscriptions': analyzed }
