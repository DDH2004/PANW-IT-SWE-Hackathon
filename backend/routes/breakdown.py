from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from backend.db import get_db
from backend.models.transaction import Transaction

router = APIRouter(prefix="/breakdown", tags=["breakdown"])

@router.get("/categories")
def category_breakdown(months: int = 3, db: Session = Depends(get_db)):
    """Return per-category totals for last N months plus overall share and income/spend separation."""
    from datetime import date, timedelta
    today = date.today()
    start = (today.replace(day=1))
    # approximate months window by subtracting 31*months days then clamp to first of that month
    window_start = (start - timedelta(days=31*months)).replace(day=1)

    rows = (
        db.query(
            Transaction.category,
            func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)).label('income'),
            func.sum(case((Transaction.amount < 0, Transaction.amount), else_=0)).label('spend')
        )
        .filter(Transaction.date >= window_start)
        .group_by(Transaction.category)
        .all()
    )
    income_total = sum(r.income or 0 for r in rows)
    spend_total = abs(sum(r.spend or 0 for r in rows))
    categories = []
    for r in rows:
        inc = float(r.income or 0)
        sp = abs(float(r.spend or 0))
        categories.append({
            'category': r.category or 'Uncategorized',
            'income': round(inc,2),
            'spend': round(sp,2),
            'net': round(inc - sp,2),
            'share_of_spend': (round((sp / spend_total)*100,2) if spend_total and sp else 0),
        })
    # sort by spend desc
    categories.sort(key=lambda x: x['spend'], reverse=True)
    return {
        'window_start': window_start.isoformat(),
        'months': months,
        'income_total': round(income_total,2),
        'spend_total': round(spend_total,2),
        'net_total': round(income_total - spend_total,2),
        'categories': categories,
    }

@router.get("/merchants")
def merchant_breakdown(limit: int = 15, db: Session = Depends(get_db)):
    rows = (
        db.query(
            Transaction.merchant,
            func.count('*').label('count'),
            func.sum(Transaction.amount).label('net'),
            func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)).label('income'),
            func.sum(case((Transaction.amount < 0, Transaction.amount), else_=0)).label('spend')
        )
        .group_by(Transaction.merchant)
        .order_by(func.sum(case((Transaction.amount < 0, Transaction.amount), else_=0)).asc())  # largest absolute spend first
        .limit(limit)
        .all()
    )
    data = []
    for r in rows:
        income = float(r.income or 0)
        spend = abs(float(r.spend or 0))
        data.append({
            'merchant': r.merchant or 'Unknown',
            'transactions': r.count,
            'income': round(income,2),
            'spend': round(spend,2),
            'net': round(income - spend,2)
        })
    return {'merchants': data}

@router.get("/timeline")
def monthly_timeline(months: int = 6, db: Session = Depends(get_db)):
    from datetime import date, timedelta
    today = date.today().replace(day=1)
    window_start = (today - timedelta(days=31*months)).replace(day=1)
    rows = (
        db.query(
            func.strftime('%Y-%m', Transaction.date).label('month'),
            func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)).label('income'),
            func.sum(case((Transaction.amount < 0, Transaction.amount), else_=0)).label('spend')
        )
        .filter(Transaction.date >= window_start)
        .group_by('month')
        .order_by('month')
        .all()
    )
    points = []
    for r in rows:
        inc = float(r.income or 0)
        sp = abs(float(r.spend or 0))
        points.append({'month': r.month, 'income': round(inc,2), 'spend': round(sp,2), 'net': round(inc - sp,2)})
    return {'months': months, 'window_start': window_start.isoformat(), 'timeline': points}
