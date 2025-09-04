from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional, List
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models.goal import Goal
from sqlalchemy import func, case
from datetime import timedelta
import os
from backend.providers import get_coach_provider, ModelProviderError
from backend.utils.logging import logger
from backend.models.transaction import Transaction

router = APIRouter(prefix="/goals", tags=["goals"])


class GoalIn(BaseModel):
    name: str
    target_amount: float
    target_date: Optional[date] = None

    @field_validator("target_amount")
    @classmethod
    def positive(cls, v):
        if v <= 0:
            raise ValueError("target_amount must be positive")
        return v


class GoalOut(BaseModel):
    id: int
    name: str
    target_amount: float
    current_amount: float
    target_date: Optional[date]
    progress_percent: float

    class Config:
        from_attributes = True


def _progress(goal: Goal) -> float:
    if goal.target_amount <= 0:
        return 0.0
    return min(100.0, (goal.current_amount / goal.target_amount) * 100.0)


@router.post("/", response_model=GoalOut)
def create_goal(payload: GoalIn, db: Session = Depends(get_db)):
    goal = Goal(name=payload.name, target_amount=payload.target_amount, current_amount=0, target_date=payload.target_date)
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return GoalOut(
        id=goal.id,
        name=goal.name,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        target_date=goal.target_date,
        progress_percent=_progress(goal),
    )


@router.get("/", response_model=List[GoalOut])
def list_goals(db: Session = Depends(get_db)):
    goals = db.query(Goal).all()
    return [
        GoalOut(
            id=g.id,
            name=g.name,
            target_amount=g.target_amount,
            current_amount=g.current_amount,
            target_date=g.target_date,
            progress_percent=_progress(g),
        )
        for g in goals
    ]


@router.get("/{goal_id}", response_model=GoalOut)
def get_goal(goal_id: int, db: Session = Depends(get_db)):
    g = db.query(Goal).get(goal_id)
    if not g:
        raise HTTPException(status_code=404, detail="Goal not found")
    return GoalOut(
        id=g.id,
        name=g.name,
        target_amount=g.target_amount,
        current_amount=g.current_amount,
        target_date=g.target_date,
        progress_percent=_progress(g),
    )


class GoalUpdate(BaseModel):
    name: Optional[str] = None
    target_amount: Optional[float] = None
    target_date: Optional[date] = None
    current_amount: Optional[float] = None  # allow manual sync


@router.patch("/{goal_id}", response_model=GoalOut)
def update_goal(goal_id: int, payload: GoalUpdate, db: Session = Depends(get_db)):
    g = db.query(Goal).get(goal_id)
    if not g:
        raise HTTPException(status_code=404, detail="Goal not found")
    if payload.name is not None:
        g.name = payload.name
    if payload.target_amount is not None:
        if payload.target_amount <= 0:
            raise HTTPException(status_code=400, detail="target_amount must be positive")
        g.target_amount = payload.target_amount
    if payload.target_date is not None:
        g.target_date = payload.target_date
    if payload.current_amount is not None:
        if payload.current_amount < 0:
            raise HTTPException(status_code=400, detail="current_amount must be >= 0")
        g.current_amount = payload.current_amount
    db.commit()
    db.refresh(g)
    return GoalOut(
        id=g.id,
        name=g.name,
        target_amount=g.target_amount,
        current_amount=g.current_amount,
        target_date=g.target_date,
        progress_percent=_progress(g),
    )


@router.delete("/{goal_id}")
def delete_goal(goal_id: int, db: Session = Depends(get_db)):
    g = db.query(Goal).get(goal_id)
    if not g:
        raise HTTPException(status_code=404, detail="Goal not found")
    db.delete(g)
    db.commit()
    return {"status": "deleted"}


@router.post("/{goal_id}/sync", response_model=GoalOut)
def sync_goal_from_transactions(goal_id: int, db: Session = Depends(get_db)):
    """Heuristic sync: sum positive transaction amounts whose description references the goal name."""
    g = db.query(Goal).get(goal_id)
    if not g:
        raise HTTPException(status_code=404, detail="Goal not found")
    total = (
        db.query(func.sum(Transaction.amount))
        .filter(Transaction.amount > 0, Transaction.description.ilike(f"%{g.name}%"))
        .scalar()
        or 0
    )
    g.current_amount = float(total)
    db.commit()
    db.refresh(g)
    return GoalOut(
        id=g.id,
        name=g.name,
        target_amount=g.target_amount,
        current_amount=g.current_amount,
        target_date=g.target_date,
        progress_percent=_progress(g),
    )


class GoalForecastOut(BaseModel):
    goal_id: int
    name: str
    target_amount: float
    current_amount: float
    target_date: date | None
    months_remaining: float | None
    required_monthly: float | None
    projected_monthly_savings: float
    projected_amount_by_target: float | None
    on_track: bool | None
    shortfall: float | None
    advice: str


def _monthly_net_savings(db: Session, months: int = 3) -> float:
    """Compute average net savings (income - spend) per month over recent period."""
    start = date.today().replace(day=1)
    window_start = (start - timedelta(days=31*months)).replace(day=1)
    rows = (
        db.query(
            func.strftime('%Y-%m', Transaction.date).label('m'),
            func.sum(
                case((Transaction.amount > 0, Transaction.amount), else_=0.0)
            ).label('inc'),
            func.sum(
                case((Transaction.amount < 0, Transaction.amount), else_=0.0)
            ).label('spend'),
        )
        .filter(Transaction.date >= window_start)
        .group_by('m')
        .all()
    )
    nets = []
    for r in rows:
        inc = float(r.inc or 0)
        spend = abs(float(r.spend or 0))
        nets.append(inc - spend)
    if not nets:
        return 0.0
    return sum(nets)/len(nets)


@router.get("/{goal_id}/forecast", response_model=GoalForecastOut)
async def forecast_goal(
    goal_id: int,
    fast: bool = False,  # use slower (more reliable) generation by default
    db: Session = Depends(get_db),
):
    g = db.query(Goal).get(goal_id)
    if not g:
        raise HTTPException(status_code=404, detail="Goal not found")
    avg_net = _monthly_net_savings(db, months=3)
    months_remaining = None
    required_monthly = None
    projected_amount_by_target = None
    on_track = None
    shortfall = None
    if g.target_date:
        today = date.today()
        delta_days = (g.target_date - today).days
        months_remaining = max(0.0, delta_days/30.0)
        remaining = max(0.0, g.target_amount - g.current_amount)
        required_monthly = (remaining / months_remaining) if months_remaining > 0 else remaining
        # project future accumulation using avg_net (assumes all net saved) – conservative adjust (0.8) to account for variability
        projected_gain = avg_net * months_remaining * 0.8
        projected_amount_by_target = g.current_amount + projected_gain
        shortfall = max(0.0, g.target_amount - projected_amount_by_target)
        on_track = shortfall <= 0.01

    advice = ""
    provider = get_coach_provider()
    prompt = (
        "You are a non-judgmental financial coach. A user has a savings goal. "
        "Given the data, state if they are on track (brief), then give specific, kind suggestions with approximate monthly dollar impact. "
        "Avoid moralizing. 5 bullet points max.\n"\
        f"Goal: {g.name}\nTarget Amount: {g.target_amount:.2f}\nCurrent Amount: {g.current_amount:.2f}\n"\
        f"Target Date: {g.target_date or 'None'}\nAvg Monthly Net Savings (last 3 mo): {avg_net:.2f}\n"\
        f"Months Remaining: {months_remaining}\nRequired Monthly (to hit target): {required_monthly}\n"\
        f"Projected Amount by Target (80% adj): {projected_amount_by_target}\nShortfall: {shortfall}\n"\
        "Respond:".
        replace("None","N/A")
    )
    attempted = []
    primary_model = os.getenv('OLLAMA_MODEL','phi3:mini')
    fallback_models = [primary_model, 'mistral', 'llama3', 'phi3', 'llama2']
    # Preserve order but drop duplicates
    seen = set()
    candidate_models = []
    for m in fallback_models:
        if m and m not in seen:
            seen.add(m)
            candidate_models.append(m)
    success = False
    logger.info("goal_forecast_start", goal_id=g.id, fast_param=fast, models=candidate_models)
    for model_name in candidate_models:
        for attempt_fast in ([fast] + ([False] if fast else [])):
            try:
                tag = f"{model_name}:{'fast' if attempt_fast else 'slow'}"
                attempted.append(tag)
                advice = await provider.generate(prompt=prompt, model=model_name, fast=attempt_fast)
                logger.info("goal_forecast_advice_success", goal_id=g.id, attempt=tag, chars=len(advice))
                success = True
                break
            except ModelProviderError as e:
                logger.warning("goal_forecast_advice_attempt_failed", goal_id=g.id, attempt=tag, error=str(e))
                continue
        if success:
            break
    if not success:
        advice = "Unable to retrieve AI advice right now. (models tried: " + ", ".join(attempted or candidate_models) + ")"
        logger.error("goal_forecast_advice_failed", goal_id=g.id, attempts=attempted)
    else:
        if len(attempted) > 1:
            advice += f"\n\n(_advice attempts: {attempted}_)"

    return GoalForecastOut(
        goal_id=g.id,
        name=g.name,
        target_amount=g.target_amount,
        current_amount=g.current_amount,
        target_date=g.target_date,
        months_remaining=months_remaining,
        required_monthly=required_monthly,
        projected_monthly_savings=avg_net,
        projected_amount_by_target=projected_amount_by_target,
        on_track=on_track,
        shortfall=shortfall,
        advice=advice,
    )
