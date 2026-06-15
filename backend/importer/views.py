"""Import views: upload CSV, review issues, resolve, confirm import."""
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from groups.models import Group, GroupMembership
from expenses.models import Expense, ExpenseSplit, Settlement
from .models import ImportSession, ImportIssue
from .serializers import ImportSessionSerializer, ImportIssueSerializer
from .csv_parser import parse_csv
from .anomaly_detector import detect_anomalies


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_csv(request, group_id):
    """Upload and analyze a CSV file for import."""
    group = get_object_or_404(Group, id=group_id, memberships__user=request.user)

    csv_file = request.FILES.get('file')
    if not csv_file:
        return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

    if not csv_file.name.endswith('.csv'):
        return Response({'error': 'File must be a CSV'}, status=status.HTTP_400_BAD_REQUEST)

    # Read file content
    content = csv_file.read().decode('utf-8-sig')  # handle BOM

    # Parse CSV
    rows, parse_errors = parse_csv(content)
    if parse_errors:
        return Response({
            'error': 'Failed to parse CSV',
            'details': parse_errors
        }, status=status.HTTP_400_BAD_REQUEST)

    # Create import session
    session = ImportSession.objects.create(
        group=group,
        uploaded_by=request.user,
        file_name=csv_file.name,
        status='analyzing',
        total_rows=len(rows),
        raw_data=rows,
    )

    # Detect anomalies
    anomalies = detect_anomalies(rows)

    # Store issues
    error_count = 0
    warning_count = 0
    for anomaly in anomalies:
        severity = anomaly['severity']
        if severity == 'error':
            error_count += 1
        elif severity == 'warning':
            warning_count += 1

        ImportIssue.objects.create(
            session=session,
            row_number=anomaly['row_number'],
            column=anomaly.get('column', ''),
            issue_type=anomaly['issue_type'],
            severity=severity,
            description=anomaly['description'],
            original_value=anomaly.get('original_value', ''),
            suggested_value=anomaly.get('suggested_value', ''),
            original_row_data=anomaly.get('original_row_data', {}),
            resolution='accepted' if severity in ('auto_fixed', 'info') else 'pending',
        )

    session.status = 'reviewing'
    session.error_count = error_count
    session.warning_count = warning_count
    session.valid_rows = len(rows) - error_count
    session.save()

    return Response(
        ImportSessionSerializer(session).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_import_session(request, session_id):
    """Get import session with all issues."""
    session = get_object_or_404(ImportSession, id=session_id, uploaded_by=request.user)
    return Response(ImportSessionSerializer(session).data)


@api_view(['PATCH'])
@permission_classes([permissions.IsAuthenticated])
def resolve_issue(request, session_id, issue_id):
    """Resolve a single import issue."""
    session = get_object_or_404(ImportSession, id=session_id, uploaded_by=request.user)
    issue = get_object_or_404(ImportIssue, id=issue_id, session=session)

    resolution = request.data.get('resolution', 'accepted')
    user_value = request.data.get('user_value', '')

    issue.resolution = resolution
    issue.user_value = user_value
    issue.save()

    return Response(ImportIssueSerializer(issue).data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def resolve_all_auto(request, session_id):
    """Accept all auto-fixed and info issues at once."""
    session = get_object_or_404(ImportSession, id=session_id, uploaded_by=request.user)
    updated = ImportIssue.objects.filter(
        session=session,
        severity__in=['auto_fixed', 'info'],
        resolution='pending'
    ).update(resolution='accepted')
    return Response({'updated': updated})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def confirm_import(request, session_id):
    """Finalize import: create expenses/settlements from resolved data."""
    session = get_object_or_404(ImportSession, id=session_id, uploaded_by=request.user)

    # Check all errors are resolved
    pending_errors = session.issues.filter(severity='error', resolution='pending').count()
    if pending_errors > 0:
        return Response({
            'error': f'{pending_errors} error(s) still need resolution before import.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Check pending warnings
    pending_warnings = session.issues.filter(severity='warning', resolution='pending').count()
    if pending_warnings > 0:
        return Response({
            'error': f'{pending_warnings} warning(s) still need review before import.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Build resolved data: apply fixes
    issues_by_row = {}
    for issue in session.issues.all():
        if issue.row_number not in issues_by_row:
            issues_by_row[issue.row_number] = []
        issues_by_row[issue.row_number].append(issue)

    group = session.group
    created_expenses = 0
    created_settlements = 0
    skipped_rows = 0
    errors = []

    # Get or create user map
    user_map = _get_or_create_users(session.raw_data, issues_by_row, group)

    for row in session.raw_data:
        rn = row['row_number']
        row_issues = issues_by_row.get(rn, [])

        # Check if row should be skipped
        skip = False
        for issue in row_issues:
            if issue.resolution == 'rejected':
                if issue.issue_type in ('exact_duplicate', 'conflicting_duplicate',
                                        'zero_amount', 'settlement_as_expense',
                                        'settlement_detected'):
                    skip = True
                    break

        # Also skip if it's a duplicate marked for removal
        for issue in row_issues:
            if issue.issue_type == 'exact_duplicate' and issue.resolution == 'accepted':
                skip = True
                break

        if skip:
            skipped_rows += 1
            continue

        try:
            result = _process_row(row, row_issues, group, user_map, session)
            if result == 'expense':
                created_expenses += 1
            elif result == 'settlement':
                created_settlements += 1
            elif result == 'skipped':
                skipped_rows += 1
        except Exception as e:
            errors.append(f'Row {rn}: {str(e)}')

    session.status = 'completed'
    session.save()

    return Response({
        'status': 'completed',
        'created_expenses': created_expenses,
        'created_settlements': created_settlements,
        'skipped_rows': skipped_rows,
        'errors': errors,
    })


def _get_or_create_users(rows, issues_by_row, group):
    """Build a mapping from CSV names to User objects. Create users if needed."""
    all_names = set()
    for row in rows:
        if row['paid_by']:
            all_names.add(row['paid_by'].strip())
        if row['split_with']:
            for name in row['split_with'].split(';'):
                name = name.strip()
                if name:
                    all_names.add(name)

    # Normalize names using issue resolutions
    name_map = {}  # raw_name -> canonical_name
    for rn, issues in issues_by_row.items():
        for issue in issues:
            if issue.issue_type in ('name_variant', 'lowercase_name', 'whitespace_in_name',
                                    'informal_name') and issue.resolution == 'accepted':
                original = issue.original_value.strip()
                suggested = issue.suggested_value.strip() or issue.user_value.strip()
                if original and suggested:
                    name_map[original.lower()] = suggested

    # Build user map
    user_map = {}
    for raw_name in all_names:
        canonical = name_map.get(raw_name.lower().strip(), raw_name.strip().title())
        if not canonical:
            continue

        # Try to find existing user
        user = User.objects.filter(username__iexact=canonical).first()
        if not user:
            user = User.objects.filter(first_name__iexact=canonical).first()
        if not user:
            # Create user with canonical name as username
            user = User.objects.create_user(
                username=canonical.lower(),
                first_name=canonical,
                password='changeme123',
                email=f'{canonical.lower()}@fairshare.local'
            )
            # Add to group
            from django.utils import timezone
            GroupMembership.objects.get_or_create(
                group=group,
                user=user,
                defaults={'joined_at': timezone.now().date(), 'is_active': True}
            )

        user_map[raw_name.lower().strip()] = user
        user_map[canonical.lower()] = user

    return user_map


def _resolve_name(name, issues, user_map):
    """Resolve a name using issue fixes and user map."""
    name_lower = name.lower().strip()
    if name_lower in user_map:
        return user_map[name_lower]
    # Try title case
    if name.strip().title().lower() in user_map:
        return user_map[name.strip().title().lower()]
    return None


def _process_row(row, row_issues, group, user_map, session):
    """Process a single CSV row into an expense or settlement."""
    # Apply fixes from issues
    date_str = row['date']
    description = row['description']
    paid_by_name = row['paid_by']
    amount_str = row['amount']
    currency = row['currency']
    split_type = row['split_type']
    split_with = row['split_with']
    split_details = row['split_details']
    notes = row['notes']

    for issue in row_issues:
        if issue.resolution not in ('accepted', 'modified'):
            continue
        val = issue.user_value or issue.suggested_value

        if issue.column == 'date' and val:
            date_str = val
        elif issue.column == 'paid_by' and val:
            paid_by_name = val
        elif issue.column == 'amount' and val:
            amount_str = val
        elif issue.column == 'currency' and val:
            currency = val
        elif issue.column == 'split_type' and val:
            split_type = val

    # Parse date
    parsed_date = _parse_date(date_str)
    if not parsed_date:
        return 'skipped'

    # Parse amount
    clean_amount = amount_str.replace(',', '').replace('"', '').strip()
    try:
        amount = Decimal(clean_amount)
    except (InvalidOperation, ValueError):
        return 'skipped'

    # Skip zero amounts
    if amount == 0:
        return 'skipped'

    # Default currency
    if not currency:
        currency = 'INR'
    currency = currency.upper().strip()

    # Resolve payer
    payer = _resolve_name(paid_by_name, row_issues, user_map)
    if not payer:
        return 'skipped'

    # Check if settlement
    is_settlement = False
    for issue in row_issues:
        if issue.issue_type in ('settlement_detected', 'settlement_as_expense',
                                'missing_split_type_settlement'):
            if issue.resolution == 'accepted':
                is_settlement = True
                break

    desc_lower = description.lower()
    if any(kw in desc_lower for kw in ['paid back', 'deposit', 'settlement']):
        is_settlement = True

    if is_settlement:
        # Create settlement
        participants = [n.strip() for n in split_with.split(';') if n.strip()]
        payee_name = None
        for p in participants:
            if p.lower().strip() != paid_by_name.lower().strip():
                payee_name = p
                break
        if payee_name:
            payee = _resolve_name(payee_name, row_issues, user_map)
            if payee:
                Settlement.objects.create(
                    group=group,
                    paid_by=payer,
                    paid_to=payee,
                    amount=abs(amount),
                    currency=currency,
                    date=parsed_date,
                    notes=notes,
                )
                return 'settlement'
        return 'skipped'

    # Create expense
    is_refund = amount < 0
    expense = Expense.objects.create(
        group=group,
        description=description,
        paid_by=payer,
        amount=abs(amount),
        currency=currency,
        split_type=split_type if split_type else 'equal',
        date=parsed_date,
        notes=notes,
        is_settlement=False,
        imported_from=session.file_name,
        import_row=row['row_number'],
    )

    # Create splits
    participants = [n.strip() for n in split_with.split(';') if n.strip()]
    participant_users = []
    for p in participants:
        # Skip informal names that were rejected
        skip_name = False
        for issue in row_issues:
            if issue.issue_type == 'informal_name' and issue.original_value == p:
                if issue.resolution == 'accepted':
                    p = issue.suggested_value or issue.user_value or p
                elif issue.resolution == 'rejected':
                    skip_name = True
                break
            if issue.issue_type == 'departed_member' and issue.original_value == p:
                if issue.resolution == 'accepted':
                    skip_name = True
                break

        if skip_name:
            continue

        user = _resolve_name(p, row_issues, user_map)
        if user:
            participant_users.append(user)

    if not participant_users:
        expense.delete()
        return 'skipped'

    _create_splits(expense, participant_users, split_type, split_details, amount, is_refund)
    return 'expense'


def _create_splits(expense, participants, split_type, split_details, total_amount, is_refund):
    """Create ExpenseSplit records based on split type."""
    amount = abs(total_amount)
    n = len(participants)

    if split_type == 'percentage' and split_details:
        parts = [p.strip() for p in split_details.split(';')]
        total_pct = Decimal('0')
        pct_map = {}
        for part in parts:
            m = re.match(r'(.+?)\s+(\d+(?:\.\d+)?)\s*%', part.strip())
            if m:
                name = m.group(1).strip().lower()
                pct = Decimal(m.group(2))
                pct_map[name] = pct
                total_pct += pct

        for user in participants:
            name_key = user.first_name.lower()
            pct = pct_map.get(name_key, Decimal('0'))
            if total_pct > 0 and total_pct != 100:
                # Normalize percentages to 100%
                pct = (pct / total_pct) * 100
            share = (amount * pct / Decimal('100')).quantize(Decimal('0.01'))
            if is_refund:
                share = -share
            ExpenseSplit.objects.create(expense=expense, user=user, amount=share)

    elif split_type == 'unequal' and split_details:
        parts = [p.strip() for p in split_details.split(';')]
        for part in parts:
            m = re.match(r'(.+?)\s+(\d+(?:\.\d+)?)\s*$', part.strip())
            if m:
                name = m.group(1).strip().lower()
                share = Decimal(m.group(2))
                user = None
                for u in participants:
                    if u.first_name.lower() == name or u.username.lower() == name:
                        user = u
                        break
                if user:
                    if is_refund:
                        share = -share
                    ExpenseSplit.objects.create(expense=expense, user=user, amount=share)

    elif split_type == 'share' and split_details:
        parts = [p.strip() for p in split_details.split(';')]
        total_shares = Decimal('0')
        share_map = {}
        for part in parts:
            m = re.match(r'(.+?)\s+(\d+(?:\.\d+)?)\s*$', part.strip())
            if m:
                name = m.group(1).strip().lower()
                shares = Decimal(m.group(2))
                share_map[name] = shares
                total_shares += shares

        for user in participants:
            name_key = user.first_name.lower()
            shares = share_map.get(name_key, Decimal('1'))
            share_amount = (amount * shares / total_shares).quantize(Decimal('0.01'))
            if is_refund:
                share_amount = -share_amount
            ExpenseSplit.objects.create(expense=expense, user=user, amount=share_amount)

    else:
        # Equal split (default)
        share = (amount / n).quantize(Decimal('0.01'))
        for user in participants:
            s = share
            if is_refund:
                s = -s
            ExpenseSplit.objects.create(expense=expense, user=user, amount=s)


def _parse_date(date_str):
    """Parse date string to date object."""
    date_str = date_str.strip()
    for fmt in ['%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d']:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    # Try Mon-DD
    m = re.match(r'^([A-Za-z]{3})-(\d{1,2})$', date_str)
    if m:
        try:
            return datetime.strptime(f'{m.group(2)}-{m.group(1)}-2026', '%d-%b-%Y').date()
        except ValueError:
            pass
    return None
