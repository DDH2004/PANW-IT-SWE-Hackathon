from sqlalchemy.orm import Session
from datetime import date, timedelta
from statistics import mean
from backend.models.transaction import Transaction

def build_financial_snapshot(db: Session, days: int = 30, max_lines: int = 12) -> str:
    cutoff = date.today() - timedelta(days=days)
    txns = (
        db.query(Transaction)
        .filter(Transaction.date >= cutoff)
        .order_by(Transaction.date.desc())
        .all()
    )
    if not txns:
        return "No recent transactions in last 30 days."

    income = sum(t.amount for t in txns if t.amount > 0)
    spend = sum(-t.amount for t in txns if t.amount < 0)
    net = income - spend

    # Category aggregation
    from collections import defaultdict
    cat_totals = defaultdict(float)
    for t in txns:
        if t.amount < 0:
            cat_totals[t.category or 'Uncategorized'] += -t.amount
    top_categories = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)[:5]

    # Merchant frequency (spend side only)
    merchant_totals = defaultdict(float)
    for t in txns:
        if t.amount < 0 and t.merchant:
            merchant_totals[t.merchant] += -t.amount
    top_merchants = sorted(merchant_totals.items(), key=lambda x: x[1], reverse=True)[:5]

    # Average daily spend
    days_span = max(1, (date.today() - cutoff).days)
    avg_daily = spend / days_span

    lines = [
        f"Window: last {days} days",
        f"Income: {income:.2f}",
        f"Spend: {spend:.2f}",
        f"Net: {net:.2f}",
        f"AvgDailySpend: {avg_daily:.2f}",
    ]
    if top_categories:
        lines.append(
            "TopCategories: "
            + ", ".join(f"{c}:{amt:.0f}" for c, amt in top_categories)
        )
    if top_merchants:
        lines.append(
            "TopMerchants: "
            + ", ".join(f"{m}:{amt:.0f}" for m, amt in top_merchants)
        )
    # Trim
    return "\n".join(lines[:max_lines])
