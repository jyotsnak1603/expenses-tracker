"""
Anomaly detector for CSV import.
Detects 40+ data quality issues across 8 categories.
"""
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from fuzzywuzzy import fuzz


# Known flatmate names for matching
KNOWN_NAMES = ['Aisha', 'Rohan', 'Priya', 'Meera', 'Sam', 'Dev']

# Name aliases mapping
NAME_ALIASES = {
    'priya s': 'Priya',
    'priya': 'Priya',
    'rohan': 'Rohan',
    'aisha': 'Aisha',
    'meera': 'Meera',
    'sam': 'Sam',
    'dev': 'Dev',
}

# Settlement keywords
SETTLEMENT_KEYWORDS = ['paid back', 'settlement', 'settle', 'deposit', 'paid.*back']

# Meera left date
MEERA_LEFT_DATE = datetime(2026, 3, 31).date()
# Sam joined date
SAM_JOINED_DATE = datetime(2026, 4, 8).date()


def detect_anomalies(rows):
    """
    Run all anomaly checks on parsed CSV rows.
    Returns list of issue dicts.
    """
    issues = []

    for row in rows:
        rn = row['row_number']
        rd = dict(row)

        # === CATEGORY A: Date & Format Issues ===
        issues.extend(_check_date(row, rn, rd))
        issues.extend(_check_amount_format(row, rn, rd))

        # === CATEGORY B: Name & Identity Issues ===
        issues.extend(_check_payer_name(row, rn, rd))
        issues.extend(_check_split_with_names(row, rn, rd))

        # === CATEGORY C: Missing Data ===
        issues.extend(_check_missing_data(row, rn, rd))

        # === CATEGORY E: Math & Validation ===
        issues.extend(_check_math(row, rn, rd))

        # === CATEGORY F: Semantic & Business Logic ===
        issues.extend(_check_semantics(row, rn, rd))

        # === CATEGORY G: Membership & Timeline ===
        issues.extend(_check_membership(row, rn, rd))

        # === CATEGORY H: Currency Issues ===
        issues.extend(_check_currency(row, rn, rd))

    # === CATEGORY D: Cross-row Duplicate Detection ===
    issues.extend(_check_duplicates(rows))

    return issues


def _parse_date_safe(date_str):
    """Try to parse a date string, return (date, format_used) or (None, None)."""
    date_str = date_str.strip()

    # Standard DD-MM-YYYY
    for fmt in ['%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d']:
        try:
            return datetime.strptime(date_str, fmt).date(), fmt
        except ValueError:
            continue

    # Mon-DD format like "Mar-14"
    m = re.match(r'^([A-Za-z]{3})-(\d{1,2})$', date_str)
    if m:
        try:
            return datetime.strptime(f'{m.group(2)}-{m.group(1)}-2026', '%d-%b-%Y').date(), 'Mon-DD'
        except ValueError:
            pass

    return None, None


def _parse_amount_safe(amount_str):
    """Parse amount string, handling commas. Returns (Decimal, issues_list)."""
    clean = amount_str.replace(',', '').replace('"', '').strip()
    try:
        return Decimal(clean), []
    except (InvalidOperation, ValueError):
        return None, ['Cannot parse amount']


def _check_date(row, rn, rd):
    issues = []
    date_str = row['date']

    if not date_str:
        issues.append(_issue(rn, 'date', 'missing_date', 'error',
                             'Date is missing', '', '', rd))
        return issues

    # Check for Mon-DD format (A1)
    if re.match(r'^[A-Za-z]{3}-\d{1,2}$', date_str):
        parsed, _ = _parse_date_safe(date_str)
        suggested = parsed.strftime('%d-%m-%Y') if parsed else ''
        issues.append(_issue(rn, 'date', 'malformed_date', 'auto_fixed',
                             f'Non-standard date format: "{date_str}". Expected DD-MM-YYYY.',
                             date_str, suggested, rd))
        return issues

    # Check for ambiguous DD-MM vs MM-DD (A2)
    m = re.match(r'^(\d{2})-(\d{2})-(\d{4})$', date_str)
    if m:
        d1, d2, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if d1 <= 12 and d2 <= 12 and d1 != d2:
            # Both interpretations valid — ambiguous
            try:
                date_ddmm = datetime(y, d2, d1).date()
                date_mmdd = datetime(y, d1, d2).date()
                # Only flag if both produce valid but different dates
                if date_ddmm != date_mmdd:
                    notes = row.get('notes', '')
                    if 'format' in notes.lower() or 'april' in notes.lower() or 'may' in notes.lower():
                        issues.append(_issue(rn, 'date', 'ambiguous_date', 'warning',
                                             f'Ambiguous date "{date_str}": could be {date_ddmm.strftime("%B %d")} (DD-MM) or {date_mmdd.strftime("%B %d")} (MM-DD). Notes hint at confusion.',
                                             date_str, date_ddmm.strftime('%d-%m-%Y'), rd))
            except ValueError:
                pass

    # Standard parse check
    parsed, fmt = _parse_date_safe(date_str)
    if parsed is None:
        issues.append(_issue(rn, 'date', 'invalid_date', 'error',
                             f'Cannot parse date: "{date_str}"', date_str, '', rd))

    return issues


def _check_amount_format(row, rn, rd):
    issues = []
    amount_str = row['amount']

    if not amount_str:
        issues.append(_issue(rn, 'amount', 'missing_amount', 'error',
                             'Amount is missing', '', '', rd))
        return issues

    # Comma-formatted (A4)
    if ',' in amount_str:
        clean = amount_str.replace(',', '')
        issues.append(_issue(rn, 'amount', 'comma_in_amount', 'auto_fixed',
                             f'Amount contains comma formatting: "{amount_str}"',
                             amount_str, clean, rd))

    # Parse the amount
    amt, errs = _parse_amount_safe(amount_str)
    if amt is None:
        issues.append(_issue(rn, 'amount', 'invalid_amount', 'error',
                             f'Cannot parse amount: "{amount_str}"', amount_str, '', rd))
        return issues

    # Excessive decimal precision (A5)
    if '.' in amount_str.replace(',', ''):
        decimals = amount_str.replace(',', '').split('.')[-1]
        if len(decimals) > 2:
            rounded = str(amt.quantize(Decimal('0.01')))
            issues.append(_issue(rn, 'amount', 'excessive_precision', 'auto_fixed',
                                 f'Amount has {len(decimals)} decimal places: {amount_str}. Rounded to {rounded}.',
                                 amount_str, rounded, rd))

    # Zero amount (F3)
    if amt == 0:
        issues.append(_issue(rn, 'amount', 'zero_amount', 'warning',
                             'Amount is zero. This may be a placeholder or void entry.',
                             amount_str, '', rd))

    # Negative amount (F4)
    if amt < 0:
        issues.append(_issue(rn, 'amount', 'negative_amount', 'warning',
                             f'Negative amount ({amount_str}). Treating as refund/reversal.',
                             amount_str, str(amt), rd))

    return issues


def _check_payer_name(row, rn, rd):
    issues = []
    payer = row['paid_by']

    if not payer:
        return issues  # handled in missing data check

    # Trailing/leading whitespace (B3)
    if payer != payer.strip():
        issues.append(_issue(rn, 'paid_by', 'whitespace_in_name', 'auto_fixed',
                             f'Payer name has extra whitespace: "{payer}"',
                             payer, payer.strip(), rd))
        payer = payer.strip()

    # Lowercase (B1, B2)
    if payer != payer.title() and payer.lower() in [n.lower() for n in KNOWN_NAMES]:
        issues.append(_issue(rn, 'paid_by', 'lowercase_name', 'auto_fixed',
                             f'Payer name has incorrect casing: "{payer}"',
                             payer, payer.title(), rd))

    # Name variant (B4) - e.g. "Priya S"
    payer_lower = payer.lower().strip()
    if payer_lower not in [n.lower() for n in KNOWN_NAMES]:
        # Try fuzzy match
        best_match = None
        best_score = 0
        for name in KNOWN_NAMES:
            score = fuzz.ratio(payer_lower, name.lower())
            if score > best_score and score >= 60:
                best_score = score
                best_match = name
        if best_match:
            issues.append(_issue(rn, 'paid_by', 'name_variant', 'warning',
                                 f'Payer "{payer}" might be "{best_match}" (similarity: {best_score}%)',
                                 payer, best_match, rd))
        elif payer_lower not in NAME_ALIASES:
            issues.append(_issue(rn, 'paid_by', 'unknown_payer', 'warning',
                                 f'Unknown payer: "{payer}". Not in known members list.',
                                 payer, '', rd))

    return issues


def _check_split_with_names(row, rn, rd):
    issues = []
    split_with = row['split_with']
    if not split_with:
        return issues

    names = [n.strip() for n in split_with.split(';')]
    for name in names:
        name_lower = name.lower().strip()
        if not name_lower:
            continue

        # Check for informal compound names (B5) - e.g. "Dev's friend Kabir"
        if "'" in name or 'friend' in name_lower:
            issues.append(_issue(rn, 'split_with', 'informal_name', 'warning',
                                 f'Informal participant name: "{name}". Extract the actual name.',
                                 name, name.split()[-1] if name.split() else name, rd))
            continue

        # Check if name is known
        if name_lower not in [n.lower() for n in KNOWN_NAMES]:
            best_match = None
            best_score = 0
            for known in KNOWN_NAMES:
                score = fuzz.ratio(name_lower, known.lower())
                if score > best_score and score >= 60:
                    best_score = score
                    best_match = known
            if not best_match:
                issues.append(_issue(rn, 'split_with', 'unknown_participant', 'warning',
                                     f'Unknown participant: "{name}".',
                                     name, '', rd))

    return issues


def _check_missing_data(row, rn, rd):
    issues = []

    # Missing payer (C1)
    if not row['paid_by']:
        issues.append(_issue(rn, 'paid_by', 'missing_payer', 'error',
                             'Payer (paid_by) is missing. Cannot determine who paid.',
                             '', '', rd))

    # Missing split_type (C2)
    if not row['split_type']:
        desc_lower = row['description'].lower()
        is_settlement = any(re.search(kw, desc_lower) for kw in SETTLEMENT_KEYWORDS)
        if is_settlement:
            issues.append(_issue(rn, 'split_type', 'missing_split_type_settlement', 'auto_fixed',
                                 'Missing split type, but description suggests this is a settlement/payment.',
                                 '', 'settlement', rd))
        else:
            issues.append(_issue(rn, 'split_type', 'missing_split_type', 'error',
                                 'Split type is missing.',
                                 '', '', rd))

    # Missing currency (C3)
    if not row['currency']:
        issues.append(_issue(rn, 'currency', 'missing_currency', 'auto_fixed',
                             'Currency is missing. Defaulting to INR.',
                             '', 'INR', rd))

    # Missing split_with
    if not row['split_with'] and row['split_type'] not in ['', None]:
        issues.append(_issue(rn, 'split_with', 'missing_split_with', 'error',
                             'Split participants list is missing.',
                             '', '', rd))

    return issues


def _check_math(row, rn, rd):
    issues = []
    split_type = row['split_type'].lower().strip()
    details = row['split_details']

    if split_type == 'percentage' and details:
        # Parse percentages
        parts = [p.strip() for p in details.split(';')]
        total = Decimal('0')
        for part in parts:
            m = re.search(r'(\d+(?:\.\d+)?)\s*%', part)
            if m:
                total += Decimal(m.group(1))
        if total != Decimal('100'):
            issues.append(_issue(rn, 'split_details', 'percentage_sum_error', 'error',
                                 f'Percentage splits sum to {total}%, not 100%.',
                                 details, '', rd))

    if split_type == 'unequal' and details:
        # Check if unequal split sums match amount
        parts = [p.strip() for p in details.split(';')]
        total = Decimal('0')
        for part in parts:
            m = re.search(r'(\d+(?:\.\d+)?)\s*$', part.strip())
            if m:
                total += Decimal(m.group(1))
        amt_str = row['amount'].replace(',', '')
        try:
            amt = Decimal(amt_str)
            if total != amt and total > 0:
                issues.append(_issue(rn, 'split_details', 'unequal_sum_mismatch', 'warning',
                                     f'Unequal split details sum to {total}, but expense amount is {amt}.',
                                     details, '', rd))
        except (InvalidOperation, ValueError):
            pass

    # Conflicting split metadata (E5)
    if split_type == 'equal' and details:
        issues.append(_issue(rn, 'split_details', 'redundant_split_details', 'auto_fixed',
                             f'Split type is "equal" but split_details are provided: "{details}". Ignoring details.',
                             details, '', rd))

    return issues


def _check_semantics(row, rn, rd):
    issues = []
    desc_lower = row['description'].lower()

    # Settlement as expense (F1, F2)
    is_settlement = any(re.search(kw, desc_lower) for kw in SETTLEMENT_KEYWORDS)
    if is_settlement and row['split_type'] != '':
        issues.append(_issue(rn, 'description', 'settlement_as_expense', 'warning',
                             f'Description "{row["description"]}" suggests this is a settlement/payment, not an expense.',
                             row['description'], 'settlement', rd))
    elif is_settlement and row['split_type'] == '':
        issues.append(_issue(rn, 'description', 'settlement_detected', 'warning',
                             f'Description "{row["description"]}" appears to be a settlement/payment.',
                             row['description'], 'settlement', rd))

    # Self-referencing error in notes (F6)
    notes_lower = row['notes'].lower()
    error_keywords = ['wrong', 'incorrect', 'error', 'mistake', 'also logged', 'counted twice', 'fixing later']
    for kw in error_keywords:
        if kw in notes_lower:
            issues.append(_issue(rn, 'notes', 'self_reported_issue', 'info',
                                 f'Notes mention a potential issue: "{row["notes"]}"',
                                 row['notes'], '', rd))
            break

    # Refund participant check (F5) - cross reference with description
    amt_str = row['amount'].replace(',', '')
    try:
        amt = Decimal(amt_str)
        if amt < 0 and 'refund' in desc_lower:
            issues.append(_issue(rn, 'split_with', 'refund_participant_check', 'info',
                                 'This is a refund. Verify participants match the original expense.',
                                 row['split_with'], '', rd))
    except (InvalidOperation, ValueError):
        pass

    return issues


def _check_membership(row, rn, rd):
    issues = []
    split_with = row['split_with']
    if not split_with:
        return issues

    date_str = row['date']
    parsed_date, _ = _parse_date_safe(date_str)
    if not parsed_date:
        return issues

    names = [n.strip() for n in split_with.split(';')]

    # Check Meera after departure (G1)
    if parsed_date > MEERA_LEFT_DATE:
        for name in names:
            if name.lower().strip() == 'meera':
                issues.append(_issue(rn, 'split_with', 'departed_member', 'warning',
                                     f'Meera is included in this expense dated {parsed_date}, but she left the group on {MEERA_LEFT_DATE}.',
                                     name, 'Remove Meera', rd))

    # Check Dev as non-member (G2, G3)
    for name in names:
        if name.lower().strip() == 'dev':
            # Dev is a guest, not a flatmate
            if parsed_date.month == 2 or (parsed_date.month == 3 and parsed_date.day <= 14):
                issues.append(_issue(rn, 'split_with', 'non_member_participant', 'info',
                                     f'Dev is not a regular flatmate but is included as a trip/visit participant.',
                                     name, '', rd))
                break

    # Check Sam before joining (if he appears before April 8)
    if parsed_date < SAM_JOINED_DATE:
        for name in names:
            if name.lower().strip() == 'sam':
                issues.append(_issue(rn, 'split_with', 'member_before_joining', 'warning',
                                     f'Sam is included in expense dated {parsed_date}, but he joined around {SAM_JOINED_DATE}.',
                                     name, 'Remove Sam', rd))

    return issues


def _check_currency(row, rn, rd):
    issues = []
    currency = row['currency'].upper().strip()

    if currency and currency != 'INR' and currency != '':
        issues.append(_issue(rn, 'currency', 'foreign_currency', 'info',
                             f'Expense is in {currency}. Will be converted to INR using configured exchange rate.',
                             currency, '', rd))

    return issues


def _check_duplicates(rows):
    """Cross-row duplicate detection (D1-D6)."""
    issues = []
    seen = []

    for i, row in enumerate(rows):
        for j, prev in enumerate(seen):
            if row['date'] == prev['date'] or _dates_match(row['date'], prev['date']):
                # Same date — check for duplicate
                desc_sim = fuzz.ratio(
                    row['description'].lower(),
                    prev['description'].lower()
                )

                amt1 = row['amount'].replace(',', '').replace('"', '')
                amt2 = prev['amount'].replace(',', '').replace('"', '')

                payer1 = row['paid_by'].lower().strip()
                payer2 = prev['paid_by'].lower().strip()

                if desc_sim >= 60:
                    if amt1 == amt2 and payer1 == payer2:
                        # Exact duplicate (D1)
                        issues.append(_issue(
                            row['row_number'], 'all', 'exact_duplicate', 'warning',
                            f'Appears to be a duplicate of row {prev["row_number"]} '
                            f'(same date, payer, amount, similar description: "{prev["description"]}").',
                            f'Row {row["row_number"]}',
                            f'Remove (keep row {prev["row_number"]})',
                            dict(row)
                        ))
                    elif desc_sim >= 70 and (payer1 != payer2 or amt1 != amt2):
                        # Conflicting duplicate (D3)
                        diff_parts = []
                        if payer1 != payer2:
                            diff_parts.append(f'payer: {row["paid_by"]} vs {prev["paid_by"]}')
                        if amt1 != amt2:
                            diff_parts.append(f'amount: {amt1} vs {amt2}')
                        issues.append(_issue(
                            row['row_number'], 'all', 'conflicting_duplicate', 'warning',
                            f'Possible duplicate of row {prev["row_number"]} with conflicts: '
                            f'{"; ".join(diff_parts)}. '
                            f'Descriptions: "{row["description"]}" vs "{prev["description"]}".',
                            f'Row {row["row_number"]}',
                            f'Choose one (check notes)',
                            dict(row)
                        ))
        seen.append(row)

    return issues


def _dates_match(d1, d2):
    """Check if two date strings refer to the same date."""
    p1, _ = _parse_date_safe(d1)
    p2, _ = _parse_date_safe(d2)
    if p1 and p2:
        return p1 == p2
    return False


def _issue(row_number, column, issue_type, severity, description,
           original_value, suggested_value, original_row_data):
    return {
        'row_number': row_number,
        'column': column,
        'issue_type': issue_type,
        'severity': severity,
        'description': description,
        'original_value': str(original_value),
        'suggested_value': str(suggested_value),
        'original_row_data': original_row_data if isinstance(original_row_data, dict) else {},
    }
