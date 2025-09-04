from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models.transaction import Transaction
from backend.models.transaction_category import TransactionCategory

router = APIRouter()

@router.get("/transactions")
def list_transactions(db: Session = Depends(get_db)):
    txns = db.query(Transaction).order_by(Transaction.date.desc()).limit(500).all()
    return [
        {
            "id": t.id,
            "date": t.date.isoformat(),
            "description": t.description,
            "amount": t.amount,
            "category": t.category,
            "merchant": t.merchant,
        }
        for t in txns
    ]

class CategoryUpdate(BaseModel):
    category: str | None = None

@router.patch("/transactions/{txn_id}/category")
def update_transaction_category(txn_id: int, payload: CategoryUpdate, db: Session = Depends(get_db)):
    txn = db.get(Transaction, txn_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    txn.category = payload.category
    db.commit()
    return {"id": txn.id, "category": txn.category}

@router.get("/transactions/{txn_id}/category/history")
def transaction_category_history(txn_id: int, db: Session = Depends(get_db)):
    txn = db.get(Transaction, txn_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    rows = (
        db.query(TransactionCategory)
        .filter(TransactionCategory.transaction_id == txn_id)
        .order_by(TransactionCategory.id.asc())
        .all()
    )
    return [
        {
            "id": r.id,
            "category": r.category,
            "original_category": r.original_category,
            "confidence": r.confidence,
            "model": r.model,
            "promoted": r.promoted,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "source": r.source,
        }
        for r in rows
    ]

@router.post("/admin/wipe")
def wipe_all_data(db: Session = Depends(get_db)):
    """Destructive: remove all transactional data and related categories, goals, settings.
    Leaves schema & migrations intact. Intended for development resets.
    """
    # Import locally to avoid circular imports
    from backend.models.goal import Goal
    from backend.models.setting import Setting
    deleted = {
        "transaction_categories": db.query(TransactionCategory).delete(),
        "transactions": db.query(Transaction).delete(),
        "goals": db.query(Goal).delete(),
        "settings": db.query(Setting).delete(),
    }
    db.commit()
    return {"status": "wiped", "deleted": deleted}
