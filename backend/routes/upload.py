from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from sqlalchemy.orm import Session
import pandas as pd
import io, csv
from datetime import datetime
from backend.db import get_db
from backend.models.transaction import Transaction
from backend.utils.logging import logger
from backend.utils.categorize import simple_category

router = APIRouter()

# Core fields required for minimal ingestion (merchant can be synthesized)
REQUIRED_MIN_COLUMNS = {"date", "amount"}
PRIMARY_TEXT_COLUMN = "description"  # logical field we want for narrative text

DATE_FORMATS = ["%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d-%m-%Y"]

def parse_date(val: str):
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Invalid date format: {val}")

HEADER_SYNONYMS = {
    'merchant_name': 'merchant',
    'vendor': 'merchant',
    'payee': 'merchant',
    'memo': 'description',
    'details': 'description',
    'notes': 'description',
    'note': 'description',
    'narrative': 'description',
    'category_description': 'description',
    'category title': 'description',
    'category_title': 'description',
    'category name': 'description',
    'category_name': 'description',
    'title': 'description',
    'narration': 'description',
    'amount_usd': 'amount',
    'value': 'amount',
    'transaction_date': 'date',
    'transaction type': 'txn_type',
    'transaction_type': 'txn_type',
    'type': 'txn_type',
    'dr_cr': 'txn_type',
    'credit/debit': 'txn_type',
}

def _remap_headers(columns):
    remapped = []
    for c in columns:
        base = c.strip().lower().lstrip('\ufeff')  # remove BOM if present
        remapped.append(HEADER_SYNONYMS.get(base, base))
    return remapped

def _score_description_candidates(df: pd.DataFrame):
    """Return list of candidate columns (name, score, metrics) that could serve as description.

    Score heuristic factors:
      - header keyword match (descript, memo, narr, note, detail, title, label, category)
      - proportion of non-empty rows
      - avg token length / richness (unique tokens / rows)
    """
    keyword_weights = {
        'descript': 2.5, 'memo': 2.2, 'narr': 2.2, 'note': 2.0, 'detail': 1.8,
        'title': 1.7, 'label': 1.6, 'category': 1.2, 'name': 1.1
    }
    candidates = []
    n_rows = len(df)
    text_cols = []
    for col in df.columns:
        if col in ('date','amount','txn_type'): continue
        # Exclude numeric-like columns
        sample_vals = df[col].head(20)
        # If majority of sample convertible to float -> skip
        numeric_like = 0
        for v in sample_vals:
            try:
                float(str(v).replace(',',''))
                numeric_like += 1
            except (ValueError, TypeError):
                pass
        if numeric_like > len(sample_vals)*0.7:
            continue
        text_cols.append(col)
    for col in text_cols:
        series = df[col].astype(str)
        non_empty = series[series.str.strip()!='']
        prop_non_empty = len(non_empty)/n_rows if n_rows else 0
        few_examples = [v for v in non_empty.head(3)]
        tokens = []
        for v in non_empty.head(200):
            tokens.extend(str(v).lower().split())
        unique_tokens = len(set(tokens))
        richness = unique_tokens / (len(non_empty.head(200)) or 1)
        header_lower = col.lower()
        header_score = 0
        for k, w in keyword_weights.items():
            if k in header_lower:
                header_score = max(header_score, w)
        score = header_score + prop_non_empty*1.5 + richness*0.5
        candidates.append({
            "column": col,
            "score": round(score, 4),
            "non_empty_ratio": round(prop_non_empty, 4),
            "richness": round(richness, 4),
            "examples": few_examples,
        })
    candidates.sort(key=lambda x: x['score'], reverse=True)
    return candidates

def _apply_description_replacement(df: pd.DataFrame, chosen: str):
    """Rename the chosen column to 'description', dropping any existing 'description' to avoid duplication.

    If chosen already is 'description', no-op. Mutates df in-place.
    """
    if chosen == 'description':
        return
    if 'description' in df.columns:
        # Drop existing description to avoid stale / conflicting text
        df.drop(columns=['description'], inplace=True)
    # If target chosen somehow missing (race), skip
    if chosen in df.columns:
        df.rename(columns={chosen: 'description'}, inplace=True)

@router.post("/upload")
async def upload_csv(
    file: UploadFile = File(...),
    dry_run: bool = False,
    chosen_description: str | None = Query(None, description="Explicit column name to use as description if not auto-detected"),
    auto_confirm_description: bool = Query(False, description="Proceed automatically with top candidate if confidence is high"),
    force_description_choice: bool = Query(False, description="Always prompt for description selection even if a description column already exists"),
    db: Session = Depends(get_db)
):
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files supported")
    content = await file.read()
    # Attempt delimiter sniffing
    text = content.decode(errors='replace')
    sample = text[:2048]
    dialect = None
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ','
    try:
        df = pd.read_csv(io.StringIO(text), delimiter=delimiter, comment='#')
    except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"CSV parse error: {e}") from e
    if df.empty:
        raise HTTPException(status_code=400, detail="CSV is empty after parsing (check content / delimiter)")
    df.columns = _remap_headers(df.columns)
    cols = set(df.columns)
    # If description missing, discover candidates and require confirmation unless confident & auto_confirm
    auto_confirmed = False
    candidate_meta = []
    # Track which original column was ultimately used for description so we can reason about category handling
    description_source = 'description' if 'description' in cols else None
    if 'description' not in cols or force_description_choice:
        candidate_meta = _score_description_candidates(df)
        # If user provided explicit choice
        if chosen_description:
            match = next((c for c in candidate_meta if c['column'] == chosen_description), None)
            if not match:
                raise HTTPException(status_code=400, detail=f"chosen_description '{chosen_description}' not found among candidate columns: {[c['column'] for c in candidate_meta]}")
            _apply_description_replacement(df, chosen_description)
            cols = set(df.columns)
            description_source = chosen_description
        elif candidate_meta and (('description' not in cols) or force_description_choice):
            top = candidate_meta[0]
            # Heuristic confidence: header keyword score portion > 2 or overall score > 2.8 considered confident
            confident = top['score'] >= 2.8
            if not force_description_choice and auto_confirm_description and confident and 'description' not in cols:
                _apply_description_replacement(df, top['column'])
                cols = set(df.columns)
                auto_confirmed = True
                description_source = top['column']
            else:
                # Return early requesting confirmation (even if description exists but force was requested)
                message = (
                    "Forced description selection: choose a column to use for description." if force_description_choice else (
                        "Ambiguous description column. Provide chosen_description param to confirm or set auto_confirm_description=true if acceptable." if not confident else
                        "High confidence candidate available; confirm to proceed or set auto_confirm_description=true."
                    )
                )
                # Put existing description column at front if present and force requested
                if force_description_choice and 'description' in cols and not any(c['column']=='description' for c in candidate_meta):
                    # evaluate description column similarly
                    existing_series = df['description'].astype(str)
                    non_empty = existing_series[existing_series.str.strip()!='']
                    prop_non_empty = len(non_empty)/len(df) if len(df) else 0
                    tokens = []
                    for v in non_empty.head(200):
                        tokens.extend(str(v).lower().split())
                    richness = len(set(tokens))/(len(non_empty.head(200)) or 1)
                    candidate_meta.insert(0, {
                        'column': 'description',
                        'score': round(3.0 + prop_non_empty*1.5 + richness*0.5,4),  # boost to reflect already-selected
                        'non_empty_ratio': round(prop_non_empty,4),
                        'richness': round(richness,4),
                        'examples': [v for v in non_empty.head(3)],
                    })
                return {
                    "status": "needs_confirmation",
                    "message": message,
                    "candidates": candidate_meta,
                    "suggested": top,
                    "normalized_columns": list(df.columns),
                    "dry_run": True,
                    "forced": force_description_choice,
                }
        else:
            # No candidates; synthesize fallback from first non-required textual
            for col in df.columns:
                if col not in ('date','amount'):
                    _apply_description_replacement(df, col)
                    cols = set(df.columns)
                    description_source = col
                    break
    # Create synthetic merchant if absent
    if 'merchant' not in cols:
        df['merchant'] = ''
        cols.add('merchant')
    # Validate minimal required fields
    if not REQUIRED_MIN_COLUMNS.issubset(cols) or 'description' not in cols:
        missing = (REQUIRED_MIN_COLUMNS | {'description'}) - cols
        raise HTTPException(status_code=400, detail=f"CSV missing required logical fields after normalization: {missing}")
    records = 0
    skipped = 0
    errors = []
    sign_inferred = 0

    income_keywords = {"income","salary","payroll","deposit","interest","refund","rebate","dividend","bonus"}
    expense_keywords = {"grocery","rent","subscription","payment","purchase","expense","withdrawal","debit","fee","coffee","restaurant","transfer out","transfer-out"}
    debit_tokens = {"debit","withdrawal","payment","purchase","fee","dr","out"}
    credit_tokens = {"credit","deposit","refund","income","cr","in"}
    for idx, row in df.iterrows():
        try:
            raw_date = str(row['date']).strip()
            if raw_date.startswith('#') or raw_date == '':  # comment / blank line
                skipped += 1
                continue
            date_obj = parse_date(raw_date)
            raw_desc = row['description']
            if raw_desc is None or (isinstance(raw_desc, float) and pd.isna(raw_desc)):
                raw_desc = ''
            desc = str(raw_desc).strip()
            if not desc:
                desc = 'UNKNOWN'  # ensure non-empty to avoid downstream clustering nulls
            merchant = str(row.get('merchant', '')).strip()
            amount_val = float(row['amount'])
            # Sign inference only if non-negative raw amount
            if amount_val >= 0:
                txntype = str(row.get('txn_type','')).strip().lower()
                if txntype in debit_tokens:
                    amount_val = -abs(amount_val)
                    sign_inferred += 1
                elif txntype in credit_tokens:
                    amount_val = abs(amount_val)  # explicit, still counts if changed from negative? skip
                else:
                    # Fallback to keyword heuristic on combined text
                    combined = ' '.join([
                        str(desc),
                        str(row.get('category','')),
                        str(row.get('labels','')),
                        str(row.get('notes','')),
                        str(row.get('txn_type','')),
                    ]).lower()
                    has_income = any(k in combined for k in income_keywords)
                    has_expense = any(k in combined for k in expense_keywords)
                    if has_expense and not has_income:
                        amount_val = -abs(amount_val)
                        sign_inferred += 1
                    # If neither detected, default assumption: treat as outflow unless obviously income keyword present
                    elif not has_income:
                        amount_val = -abs(amount_val)
                        sign_inferred += 1
            # Category resolution precedence:
            # 1. If original category column existed AND wasn't repurposed as description, prefer its value
            # 2. If the user explicitly selected the 'category' column as description (description_source == 'category'),
            #    we treat the description text itself as the category label (better than leaving empty)
            # 3. Fallback to heuristic simple_category
            raw_category_val = None
            if description_source != 'category' and 'category' in df.columns:
                try:
                    rc = row.get('category')
                    if rc is not None and not (isinstance(rc, float) and pd.isna(rc)):
                        txt = str(rc).strip()
                        if txt:
                            raw_category_val = txt
                except Exception:
                    pass
            elif description_source == 'category':
                # Original category column became description; reuse that text as category directly
                raw_category_val = desc if desc and desc != 'UNKNOWN' else None
            category = raw_category_val if raw_category_val else simple_category(desc, merchant)
            txn = Transaction(
                date=date_obj,
                description=desc,
                amount=amount_val,
                merchant=merchant,
                category=category,
            )
            if not dry_run:
                db.add(txn)
            records += 1
        except (ValueError, TypeError) as e:
            skipped += 1
            if len(errors) < 5:  # cap error detail
                errors.append({"row": int(idx), "error": str(e)})
            continue
    if not dry_run:
        db.commit()
    else:
        db.rollback()
    logger.info("csv_uploaded", file=file.filename, records=records, skipped=skipped, dry_run=dry_run, auto_confirmed=auto_confirmed)
    return {
        "status": "ok",
        "records": records,
        "skipped": skipped,
        "errors_sample": errors,
        "delimiter": delimiter,
        "normalized_columns": list(df.columns),
        "dry_run": dry_run,
        "sign_inferred": sign_inferred,
        "description_column_used": 'description' if 'description' in cols else None,
    "description_source": description_source,
        "auto_confirmed": auto_confirmed,
        "candidates_evaluated": candidate_meta if candidate_meta else None,
    }
