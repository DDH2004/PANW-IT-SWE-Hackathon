from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date, timedelta
from collections import defaultdict
from statistics import mean, stdev
from backend.db import get_db
from backend.models.transaction import Transaction

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


@router.get('/')
def anomalies(db: Session = Depends(get_db)):
    """Return potential spending anomalies and possible duplicate charges.

    Heuristics:
    - Outliers: amounts whose absolute value exceeds mean+2*std for last 60d expenses.
    - Duplicates: same absolute amount, same day, same merchant/category appearing >1.
    """
    cutoff = date.today() - timedelta(days=60)
    txns = db.query(Transaction).filter(Transaction.date >= cutoff).all()
    expenses = [t for t in txns if t.amount < 0]
    abs_amounts = [abs(t.amount) for t in expenses]
    outliers = []
    if len(abs_amounts) >= 5:
        m = mean(abs_amounts)
        try:
            s = stdev(abs_amounts)
        except Exception:
            s = 0
        threshold = m + 2 * s
        for t in expenses:
            if abs(t.amount) >= threshold and abs(t.amount) > 0:
                outliers.append({
                    'date': t.date.isoformat(),
                    'description': t.description,
                    'amount': float(t.amount),
                    'category': t.category,
                    'merchant': t.merchant,
                    'threshold': round(threshold, 2)
                })

    dup_map = defaultdict(list)
    for t in expenses:
        key = (t.date, round(abs(t.amount), 2), t.merchant or '', t.category or '')
        dup_map[key].append(t)
    duplicates = []
    for key, group in dup_map.items():
        if len(group) > 1:
            duplicates.append({
                'date': key[0].isoformat(),
                'amount': -key[1],
                'merchant': key[2],
                'category': key[3],
                'count': len(group),
                'descriptions': [g.description for g in group]
            })

    return {'outliers': outliers, 'duplicates': duplicates}
