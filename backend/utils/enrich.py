"""Model-based categorization enrichment scaffold.

This module provides a non-blocking style enrichment function that can be
triggered after upload to categorize transactions that lack a category or
were tagged as None by the heuristic.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.models.transaction import Transaction
from backend.models.transaction_category import TransactionCategory
from backend.utils.logging import logger

ALLOWED_CATEGORIES = [
    'Income','Groceries','Food & Drink','Transport','Subscriptions','Housing','Shopping','Entertainment','Health','Other'
]

def build_prompt(description: str, merchant: str|None) -> str:
    return (
        "You are a financial transaction categorizer. Given a description and merchant, "
        "choose ONE best-fit category from this list: " + ", ".join(ALLOWED_CATEGORIES) + ".\n"
        "Return ONLY raw JSON object with keys category, confidence (0-1).\n"
        f"Description: {description}\nMerchant: {merchant or ''}"
    )

def _ensure_category_table_columns(db: Session):
    """Ensure newly added columns exist for backward compatibility (online SQLite migrations)."""
    try:
        rows = db.execute(text("PRAGMA table_info(transaction_categories)")).fetchall()
        existing = {r[1] for r in rows}
        altered = False
        if 'promoted' not in existing:
            db.execute(text("ALTER TABLE transaction_categories ADD COLUMN promoted BOOLEAN DEFAULT 0"))
            altered = True
        if 'original_category' not in existing:
            db.execute(text("ALTER TABLE transaction_categories ADD COLUMN original_category VARCHAR NULL"))
            altered = True
        if altered:
            db.commit()
            logger.info("enrich_runtime_migration_applied", columns_added=[c for c in ['promoted','original_category'] if c not in existing])
    except Exception as e:
        logger.warning("enrich_runtime_migration_failed", error=str(e))
        try:
            db.rollback()
        except Exception:
            pass

async def categorize_with_model(
    db: Session,
    model_client,
    txns: List[Transaction],
    model_name: str = 'phi3:mini',
    promote: bool = True,
    promotion_min_confidence: float = 0.8,
    overwrite_existing: bool = False,
    allowed_categories: Optional[List[str]] = None,
):
    """Categorize a list of transactions using provided model_client.

    Parameters:
      db: SQLAlchemy session
      model_client: object with async categorize(prompt:str, model:str) -> {category:str, confidence:float}
      txns: list of Transaction objects to categorize
      model_name: identifier for the model stored in TransactionCategory.model
      promote: if True, optionally writes back to Transaction.category when criteria met
      promotion_min_confidence: minimum confidence required for promotion
      overwrite_existing: if True, will overwrite a non-empty Transaction.category (default False)
      allowed_categories: optional override list; falls back to ALLOWED_CATEGORIES

    Promotion Rules:
      - category in allowed list
      - confidence >= promotion_min_confidence
      - (overwrite_existing or transaction.category is None/empty)
    """
    # Ensure schema compatibility (promoted & original_category columns added after early deployments)
    _ensure_category_table_columns(db)
    processed_ids = []
    promoted_ids = []
    allowed = set(allowed_categories or ALLOWED_CATEGORIES)
    for t in txns:
        prompt = build_prompt(t.description, t.merchant)
        try:
            resp = await model_client.categorize(prompt, model=model_name)
            cat = resp.get('category')
            conf = resp.get('confidence')
            if not cat or cat not in allowed:
                continue
            promoted_flag = False
            if promote and conf is not None:
                current = getattr(t, 'category', None)
                if (overwrite_existing or not current) and conf >= promotion_min_confidence:
                    t.category = cat
                    promoted_flag = True
            else:
                current = getattr(t, 'category', None)
            db.add(TransactionCategory(
                transaction_id=t.id,
                source='model',
                category=cat,
                confidence=conf,
                model=model_name,
                promoted=promoted_flag,
                original_category=current if promoted_flag else None,
            ))
            processed_ids.append(t.id)
            if promoted_flag:
                promoted_ids.append(t.id)
        except (ValueError, KeyError, AttributeError, TypeError):
            # swallow individual transaction errors
            continue
    db.commit()
    return {"processed_ids": processed_ids, "promoted_ids": promoted_ids}