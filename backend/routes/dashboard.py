from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date, timedelta
from collections import defaultdict
import os

from backend.db import get_db
from backend.models.transaction import Transaction
from backend.models.setting import Setting

router = APIRouter()


def _month_range(d: date):
    start = d.replace(day=1)
    if start.month == 12:
        next_month_start = start.replace(year=start.year + 1, month=1)
    else:
        next_month_start = start.replace(month=start.month + 1)
    return start, next_month_start - timedelta(days=1)


@router.get('/dashboard')
async def dashboard(db: Session = Depends(get_db)):
    today = date.today()
    start_this, end_this = _month_range(today)
    # Previous month
    prev_reference = (start_this - timedelta(days=1))
    start_prev, end_prev = _month_range(prev_reference)

    txns = db.query(Transaction).all()

    mtd_income = mtd_spend = 0.0
    prev_spend_by_cat = defaultdict(float)
    this_spend_by_cat = defaultdict(float)
    largest_expenses = []
    expenses = []
    subs_map = defaultdict(list)

    for t in txns:
        # Build subscription grouping baseline
        if t.merchant:
            subs_map[t.merchant].append(t)
        if start_prev <= t.date <= end_prev and t.amount < 0:
            prev_spend_by_cat[t.category or 'Uncategorized'] += -t.amount
        if start_this <= t.date <= end_this:
            if t.amount > 0:
                mtd_income += t.amount
            elif t.amount < 0:
                amt = -t.amount
                mtd_spend += amt
                this_spend_by_cat[t.category or 'Uncategorized'] += amt
                expenses.append(t)

    # Largest expenses this month
    expenses.sort(key=lambda t: t.amount)  # negative amounts ascending
    largest_expenses = [
        {
            'date': e.date.isoformat(),
            'description': e.description[:60],
            'amount': float(e.amount),
            'category': e.category,
        }
        for e in sorted(expenses, key=lambda t: t.amount)[:5]
    ]

    # Month-over-month category changes
    mom_changes = []
    for cat, val in this_spend_by_cat.items():
        prev = prev_spend_by_cat.get(cat, 0.0)
        delta = val - prev
        pct = (delta / prev * 100) if prev > 0 else None
        mom_changes.append({
            'category': cat,
            'this_month': round(val, 2),
            'prev_month': round(prev, 2),
            'delta': round(delta, 2),
            'delta_pct': round(pct, 1) if pct is not None else None,
        })
    mom_changes.sort(key=lambda x: abs(x['delta']), reverse=True)
    mom_changes = mom_changes[:5]

    savings_rate = (mtd_income - mtd_spend) / mtd_income * 100 if mtd_income > 0 else 0

    # Budget: DB setting overrides env variable
    monthly_budget = 0.0
    setting_budget = db.query(Setting).filter(Setting.key == 'MONTHLY_BUDGET').first()
    if setting_budget:
        try:
            monthly_budget = float(setting_budget.value)
        except ValueError:
            monthly_budget = 0.0
    if not setting_budget:  # fallback
        try:
            monthly_budget = float(os.getenv('MONTHLY_BUDGET', '0') or 0)
        except ValueError:
            monthly_budget = 0.0
    budget_used_pct = (mtd_spend / monthly_budget * 100) if monthly_budget > 0 else None

    # Upcoming subscriptions heuristic: merchants with >=3 occurrences; estimate next charge ~30 days after last negative
    upcoming = []
    for merchant, mtxns in subs_map.items():
        negs = [t for t in mtxns if t.amount < 0]
        if len(negs) >= 3:
            last = max(negs, key=lambda t: t.date)
            next_est = last.date + timedelta(days=30)
            if 0 <= (next_est - today).days <= 14:
                upcoming.append({
                    'merchant': merchant,
                    'last_amount': float(negs[-1].amount),
                    'next_estimate': next_est.isoformat(),
                })
    upcoming.sort(key=lambda x: x['next_estimate'])

    return {
        'mtd_income': round(mtd_income, 2),
        'mtd_spend': round(mtd_spend, 2),
        'net_cash_flow': round(mtd_income - mtd_spend, 2),
        'savings_rate_pct': round(savings_rate, 1),
        'monthly_budget': monthly_budget if monthly_budget else None,
        'budget_used_pct': round(budget_used_pct, 1) if budget_used_pct is not None else None,
        'largest_expenses': largest_expenses,
        'mom_category_changes': mom_changes,
        'upcoming_subscriptions': upcoming,
    }
