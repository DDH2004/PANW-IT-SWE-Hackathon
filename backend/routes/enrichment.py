from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models.transaction import Transaction
from backend.models.transaction_category import TransactionCategory
from backend.utils.enrich import categorize_with_model
from sqlalchemy import or_
from backend.utils.logging import logger
from collections import Counter  # used for cluster token frequency
import re
from pydantic import BaseModel

router = APIRouter(prefix="/enrich", tags=["enrichment"])

class SimpleModelClient:
    async def categorize(self, prompt: str, model: str = 'phi3:mini'):
        """Richer keyword heuristic to give better coverage for demo purposes."""
        text = prompt.lower()
        def any_kw(words):
            return any(w in text for w in words)
        if any_kw(['grocery','groceries','wholefoods','trader joe','kroger','safeway']):
            return {'category': 'Groceries', 'confidence': 0.92, 'model': model}
        if any_kw(['coffee','starbucks','cafe','drink','restaurant','dining','pizza','chipotle','mcdonald','burger']):
            return {'category': 'Food & Drink', 'confidence': 0.87, 'model': model}
        if any_kw(['uber','lyft','gas','shell','exxon','transport','bus','train','metro','taxi']):
            return {'category': 'Transport', 'confidence': 0.88, 'model': model}
        if any_kw(['netflix','spotify','hulu','disney','prime video','subscription','subscrip','monthly plan']):
            return {'category': 'Subscriptions', 'confidence': 0.9, 'model': model}
        if any_kw(['rent','mortgage','landlord','apartment']):
            return {'category': 'Housing', 'confidence': 0.9, 'model': model}
        if any_kw(['pharmacy','doctor','hospital','clinic','health','dental']):
            return {'category': 'Health', 'confidence': 0.88, 'model': model}
        if any_kw(['amazon','walmart','target','store','mall','shopping']):
            return {'category': 'Shopping', 'confidence': 0.86, 'model': model}
        if any_kw(['cinema','movie','theater','entertainment','concert','ticket']):
            return {'category': 'Entertainment', 'confidence': 0.85, 'model': model}
        if any_kw(['salary','payroll','bonus','dividend','interest','refund','rebate']):
            return {'category': 'Income', 'confidence': 0.95, 'model': model}
        # fallback 'Other' with moderate confidence slightly above default threshold suggestion if user lowers it
        return {'category': 'Other', 'confidence': 0.75, 'model': model}

@router.post('/')
async def trigger_enrichment(
    limit: int = 50,
    model: str = 'phi3:mini',
    promote: bool = True,
    promotion_min_confidence: float = 0.8,
    overwrite_existing: bool = False,
    only_uncategorized: bool = True,
    include_already_enriched: bool = False,
    cluster_mode: bool = False,
    cluster_threshold: float = 0.5,
    cluster_min_size: int = 2,
    cluster_max_tokens: int = 2,
    db: Session = Depends(get_db)
):
    # Base query
    q = db.query(Transaction)
    if only_uncategorized:
        q = q.filter(
            or_(
                Transaction.category == None,  # noqa: E711
                Transaction.category == '',
                Transaction.category.ilike('%uncategorized%')
            )
        )
    if not include_already_enriched and not cluster_mode:
        # Exclude transactions that already have any model-derived category row (only for model mode)
        q = q.filter(
            ~db.query(TransactionCategory.id).filter(TransactionCategory.transaction_id == Transaction.id).exists()
        )
    txns = (
        q.order_by(Transaction.id.desc())
        .limit(limit)
        .all()
    )
    if not txns:
        return {"enriched": 0, "processed_ids": [], "reason": "no candidates", "cluster_mode": cluster_mode}

    if cluster_mode:
        # Lightweight greedy Jaccard clustering on token sets
        stop = set(['the','and','for','to','a','of','in','at','on','store','inc','llc','co','payment','purchase'])
        token_cache = {}
        def tokenize(t: Transaction):
            key = t.id
            if key in token_cache:
                return token_cache[key]
            base = f"{t.description or ''} {t.merchant or ''}".lower()
            toks = [w for w in re.split(r"[^a-z0-9]+", base) if w and len(w) > 2 and w not in stop]
            token_cache[key] = set(toks)
            return token_cache[key]
        unassigned = set(t.id for t in txns)
        clusters = []  # list of (member_ids, label, avg_sim)
        id_to_tx = {t.id: t for t in txns}
        while unassigned:
            seed_id = unassigned.pop()
            seed_tokens = tokenize(id_to_tx[seed_id])
            members = [seed_id]
            sims = []
            # iterate snapshot list for deterministic behavior
            for other_id in list(unassigned):
                other_tokens = tokenize(id_to_tx[other_id])
                if not seed_tokens or not other_tokens:
                    continue
                inter = len(seed_tokens & other_tokens)
                union = len(seed_tokens | other_tokens)
                j = inter/union if union else 0.0
                if j >= cluster_threshold:
                    unassigned.remove(other_id)
                    members.append(other_id)
                    sims.append(j)
            if len(members) >= cluster_min_size:
                # derive label: top tokens by frequency across members
                freq = Counter()
                for mid in members:
                    freq.update(tokenize(id_to_tx[mid]))
                top_tokens = [tok for tok,_ in freq.most_common(cluster_max_tokens)] or ['misc']
                label = 'Cluster: ' + '_'.join(top_tokens)
                avg_sim = sum(sims)/len(sims) if sims else 1.0
                clusters.append((members, label, avg_sim))
        processed_ids = []
        promoted_ids = []
        cluster_detail = []  # list of dict: label, members:[{id, prev_category, description, merchant}], avg_similarity
        for members, label, avg_sim in clusters:
            confidence = min(0.99, max(0.3, avg_sim))  # bound
            member_infos = []
            # capture prior state before mutation
            for tid in members:
                t = id_to_tx[tid]
                member_infos.append({
                    'transaction_id': tid,
                    'previous_category': getattr(t, 'category', None),
                    'description': t.description,
                    'merchant': t.merchant,
                })
            for info in member_infos:
                tid = info['transaction_id']
                t = id_to_tx[tid]
                current = info['previous_category']
                promoted_flag = False
                if promote and (overwrite_existing or not current):
                    t.category = label
                    promoted_flag = True
                db.add(TransactionCategory(
                    transaction_id=tid,
                    source='cluster',
                    category=label,
                    confidence=confidence,
                    model='cluster',
                    promoted=promoted_flag,
                    original_category=current if promoted_flag else None,
                ))
                processed_ids.append(tid)
                if promoted_flag:
                    promoted_ids.append(tid)
            cluster_detail.append({
                'label': label,
                'size': len(members),
                'avg_similarity': avg_sim,
                'members': member_infos,
            })
        db.commit()
        logger.info("cluster_enrichment_complete", clusters=len(clusters), processed=len(processed_ids))
        return {
            "cluster_mode": True,
            "candidates": len(txns),
            "clusters": cluster_detail,
            "enriched": len(processed_ids),
            "processed_ids": processed_ids,
            "promoted_count": len(promoted_ids),
            "promoted_ids": promoted_ids,
            "threshold": promotion_min_confidence,
            "cluster_threshold": cluster_threshold,
            "cluster_min_size": cluster_min_size,
        }
    else:
        client = SimpleModelClient()
        result = await categorize_with_model(
            db,
            client,
            txns,
            model_name=model,
            promote=promote,
            promotion_min_confidence=promotion_min_confidence,
            overwrite_existing=overwrite_existing,
        )
        return {
            "cluster_mode": False,
            "candidates": len(txns),
            "enriched": len(result["processed_ids"]),
            "processed_ids": result["processed_ids"],
            "promoted_count": len(result["promoted_ids"]),
            "promoted_ids": result["promoted_ids"],
            "promotion_enabled": promote,
            "threshold": promotion_min_confidence,
            "only_uncategorized": only_uncategorized,
            "include_already_enriched": include_already_enriched,
        }

@router.get('/latest')
def latest_enriched(db: Session = Depends(get_db), limit: int = 20):
    rows = db.query(TransactionCategory).order_by(TransactionCategory.id.desc()).limit(limit).all()
    return [
        {
            'transaction_id': r.transaction_id,
            'category': r.category,
            'confidence': r.confidence,
            'model': r.model,
            'source': r.source,
            'created_at': r.created_at.isoformat() if r.created_at else None,
            'promoted': r.promoted,
        }
        for r in rows
    ]


class RenameClusterIn(BaseModel):
    old_label: str
    new_label: str
    update_transactions: bool = True
    update_history: bool = True  # rename in transaction_categories rows


@router.post('/rename_cluster')
def rename_cluster(payload: RenameClusterIn, db: Session = Depends(get_db)):
    old_label = payload.old_label.strip()
    new_label = payload.new_label.strip()
    if not old_label or not new_label:
        raise HTTPException(status_code=400, detail="Labels must be non-empty")
    if old_label == new_label:
        return {"status": "noop", "label": new_label}
    # ensure old exists
    exists_q = db.query(TransactionCategory.id).filter(TransactionCategory.category == old_label, TransactionCategory.source=='cluster').first()
    if not exists_q:
        raise HTTPException(status_code=404, detail="Old cluster label not found")
    updated_tx = 0
    updated_hist = 0
    if payload.update_transactions:
        updated_tx = db.query(Transaction).filter(Transaction.category == old_label).update({Transaction.category: new_label}, synchronize_session=False)
    if payload.update_history:
        updated_hist = db.query(TransactionCategory).filter(TransactionCategory.category == old_label, TransactionCategory.source=='cluster').update({TransactionCategory.category: new_label}, synchronize_session=False)
    db.commit()
    logger.info("cluster_renamed", old=old_label, new=new_label, tx_updated=updated_tx, history_updated=updated_hist)
    return {
        "status": "renamed",
        "old_label": old_label,
        "new_label": new_label,
        "updated_transactions": updated_tx,
        "updated_history_rows": updated_hist,
    }