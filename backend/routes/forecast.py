from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models.transaction import Transaction
from datetime import datetime
import pandas as pd

router = APIRouter()

@router.get('/forecast')
async def forecast(db: Session = Depends(get_db)):
    # Simplified placeholder: total spend last 30 days * 12 as annual projection
    txns = db.query(Transaction).all()
    if not txns:
        return {"projection": 0}
    df = pd.DataFrame([
        {"date": t.date, "amount": t.amount} for t in txns
    ])
    last_30 = df[df['date'] > (datetime.utcnow().date() - pd.Timedelta(days=30))]
    monthly = last_30['amount'].sum()
    projection = monthly * 12
    return {"annual_spend_projection": projection}
