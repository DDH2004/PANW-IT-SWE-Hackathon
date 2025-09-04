from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models.transaction import Transaction

router = APIRouter()

@router.get('/insights')
async def insights(db: Session = Depends(get_db)):
    txns = db.query(Transaction).all()
    spending = {}
    income_total = 0.0
    for t in txns:
        if t.amount < 0:  # expense
            key = t.category or 'Uncategorized'
            spending[key] = spending.get(key, 0.0) + (-t.amount)  # store as positive outflow
        elif t.amount > 0:  # income
            income_total += t.amount
    spending_list = [
        { 'category': c, 'total': round(v, 2)} for c, v in sorted(spending.items(), key=lambda x: x[1], reverse=True)
    ]
    total_spend = round(sum(spending.values()), 2)
    net = round(income_total - total_spend, 2)
    return {
        'spending_by_category': spending_list,
        'total_spend': total_spend,
        'total_income': round(income_total, 2),
        'net': net,
    }
