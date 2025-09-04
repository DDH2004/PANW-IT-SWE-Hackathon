import re

KEYWORD_CATEGORIES = [
    (re.compile(r'coffee|cafe|starbucks', re.I), 'Food & Drink'),
    (re.compile(r'grocery|wholefoods|market', re.I), 'Groceries'),
    (re.compile(r'spotify|music|netflix|subscription', re.I), 'Subscriptions'),
    (re.compile(r'uber|lyft|ride', re.I), 'Transport'),
    (re.compile(r'salary|payroll|employer', re.I), 'Income'),
]

def simple_category(description: str, merchant: str | None = None) -> str | None:
    text = f"{description} {merchant or ''}"
    for pattern, label in KEYWORD_CATEGORIES:
        if pattern.search(text):
            return label
    return None
