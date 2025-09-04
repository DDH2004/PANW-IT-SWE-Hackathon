from fastapi import APIRouter, HTTPException, Query
import os
from backend.utils.logging import logger
from backend.models.schemas import CoachRequest, CoachResponse
from backend.db import get_db
from sqlalchemy.orm import Session
from fastapi import Depends
from backend.utils.summary import build_financial_snapshot
from backend.models.coach_message import CoachMessage
from backend.providers import get_coach_provider, ModelProviderError

router = APIRouter()

MODEL = os.getenv('OLLAMA_MODEL', 'phi3:mini')  # default internal model name

SAFETY_PREFIX = "You are a helpful financial wellness coach. Provide empathetic, responsible, non-judgmental guidance. Avoid giving legal or investment guarantees."

@router.get('/coach/debug')
async def coach_debug():
    # Minimal debug (provider-specific deeper diagnostics can be added later)
    provider = get_coach_provider()
    return {'provider': provider.name, 'model_requested': MODEL}

def _approx_tokens(text: str) -> int:
    # Very rough tokenizer heuristic (~4 chars per token average)
    return max(1, int(len(text)/4))

def _fetch_recent_history(db: Session, user_id: int, limit: int = 10):
    rows = db.query(CoachMessage).filter(CoachMessage.user_id == user_id).order_by(CoachMessage.id.desc()).limit(limit).all()
    # Return chronological
    return list(reversed(rows))

@router.get('/coach/history')
async def coach_history(limit: int = 25, db: Session = Depends(get_db), user_id: int = Query(1)):
    rows = _fetch_recent_history(db, user_id, min(limit, 100))
    return [
        {
            'id': r.id,
            'role': r.role,
            'content': r.content,
            'created_at': r.created_at.isoformat() if r.created_at else None,
            'model': r.model,
        } for r in rows
    ]

@router.post('/coach', response_model=CoachResponse)
async def coach(query: CoachRequest, db: Session = Depends(get_db), user_id: int = Query(1), include_history: bool = Query(True, description="Include prior conversation for personalization")):
    chosen_model = (query.model or MODEL).strip()
    full_snapshot = build_financial_snapshot(db) if query.include_data else "(User opted out of data context)"
    if query.fast:
        # Fast mode
        snapshot = full_snapshot[:400]
        style_hint = "Keep answer under 6 short bullet points."
        max_chars = 900
    # fast mode uses lower sampling params inside provider; variables retained for future use
    else:
        snapshot = full_snapshot
        style_hint = "Provide concise, structured guidance."
        max_chars = 1600
    # Build conversation memory (exclude if disabled or none)
    history_block = ""
    if include_history and not query.fast:  # omit in fast for latency
        recent = _fetch_recent_history(db, user_id, limit=8)
        if recent:
            lines = []
            for m in recent:
                role = 'User' if m.role == 'user' else 'Coach'
                # Trim overly long past messages
                content = m.content.strip()
                if len(content) > 300:
                    content = content[:300] + '…'
                lines.append(f"{role}: {content}")
            history_block = "PRIOR CHAT (most recent first shown last):\n" + "\n".join(lines) + "\n"
    prompt_core = f"{SAFETY_PREFIX}\nFINANCIAL SNAPSHOT:\n{snapshot}\n{history_block}User Question: {query.message}\n{style_hint}\nAnswer:"  # simplified tail
    prompt = prompt_core[:max_chars]
    provider = get_coach_provider()
    try:
        response_text = await provider.generate(prompt=prompt, model=chosen_model, fast=query.fast)
        # Persist both sides
        try:
            db.add(CoachMessage(user_id=user_id, role='user', content=query.message, model=chosen_model, tokens_in=_approx_tokens(query.message)))
            db.add(CoachMessage(user_id=user_id, role='assistant', content=response_text, model=chosen_model, tokens_out=_approx_tokens(response_text)))
            db.commit()
        except Exception as persist_err:  # noqa: BLE001
            logger.warning("coach_message_persist_failed", error=str(persist_err))
        return CoachResponse(response=response_text)
    except ModelProviderError as e:
        logger.error("coach_provider_failed", provider=provider.name, model=chosen_model, error=str(e))
        raise HTTPException(status_code=502, detail=f"Model provider '{provider.name}' failed: {e}") from e
