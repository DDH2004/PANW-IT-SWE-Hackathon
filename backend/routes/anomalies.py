from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import date, timedelta
from collections import defaultdict
from statistics import mean, stdev, StatisticsError
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
        except StatisticsError:  # occurs if variance undefined (all equal)
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
                'transactions': [
                    {
                        'id': g.id,
                        'description': g.description,
                        'amount': g.amount,
                        'category': g.category,
                        'merchant': g.merchant,
                        'date': g.date.isoformat()
                    } for g in group
                ]
            })

    return {'outliers': outliers, 'duplicates': duplicates}


class DedupeRequest(BaseModel):
    transaction_ids: list[int]
    validate_duplicates: bool = True  # ensure they are duplicates under current heuristic
    keep_one_per_group: bool = False  # if true and a full group provided, keep earliest


@router.post('/dedupe')
def remove_duplicates(payload: DedupeRequest, db: Session = Depends(get_db)):
    """Delete specific transaction IDs considered unwanted duplicates.

    Options:
    - validate_duplicates: confirm each id belongs to a duplicate group (same date, amount, merchant/category) size>1.
    - keep_one_per_group: when True and user passes an entire duplicate group, keep the earliest created (by id) automatically.
    """
    if not payload.transaction_ids:
        raise HTTPException(status_code=400, detail="No transaction_ids supplied")
    # Fetch all referenced transactions
    txns = db.query(Transaction).filter(Transaction.id.in_(payload.transaction_ids)).all()
    found_ids = {t.id for t in txns}
    missing = [i for i in payload.transaction_ids if i not in found_ids]
    if missing:
        raise HTTPException(status_code=404, detail=f"Transactions not found: {missing}")

    # Build grouping for validation
    if payload.validate_duplicates:
        groups = {}
        for t in txns:
            if t.amount >= 0:  # only consider expenses duplicates
                raise HTTPException(status_code=400, detail=f"Transaction {t.id} is not an expense; aborting")
            key = (t.date, round(abs(t.amount), 2), t.merchant or '', t.category or '')
            groups.setdefault(key, []).append(t)
        # Re-query full group membership to ensure >1
        for key in groups.keys():
            date_k, amt_k, merch_k, cat_k = key
            full_group = db.query(Transaction).filter(
                Transaction.date == date_k,
                Transaction.amount < 0,
                (Transaction.merchant == merch_k) if merch_k else (Transaction.merchant.is_(None) | (Transaction.merchant == '')),
                (Transaction.category == cat_k) if cat_k else (Transaction.category.is_(None) | (Transaction.category == '')),
            ).all()
            # Filter to same absolute amount
            full_group = [g for g in full_group if round(abs(g.amount), 2) == amt_k]
            if len(full_group) <= 1:
                raise HTTPException(
                    status_code=400,
                    detail=f"Group for amount {amt_k} on {date_k} merchant '{merch_k}' has size 1; not a duplicate group"
                )
            if payload.keep_one_per_group:
                # Retain earliest id in group if all provided
                full_ids = {g.id for g in full_group}
                if full_ids.issubset(found_ids):
                    earliest = min(full_ids)
                    # remove earliest from deletion set
                    found_ids.discard(earliest)

    # Perform deletions
    to_delete = db.query(Transaction).filter(Transaction.id.in_(found_ids)).all()
    deleted_ids = [t.id for t in to_delete]
    for t in to_delete:
        db.delete(t)
    db.commit()
    return {
        'status': 'deduped',
        'deleted_count': len(deleted_ids),
        'deleted_ids': deleted_ids,
        'skipped_ids': list(set(payload.transaction_ids) - set(deleted_ids))
    }


## Undo feature removed per request.
