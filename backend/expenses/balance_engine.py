"""
Deterministic balance engine.

Computes who owes whom based on all expenses and settlements in a group.
Supports multi-currency conversion and provides per-expense breakdowns
(Rohan's requirement: "show me exactly which expenses make up my balance").
"""
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
from django.conf import settings
from .models import Expense, ExpenseSplit, Settlement


def get_exchange_rate(from_currency, to_currency):
    """Get exchange rate between currencies."""
    if from_currency == to_currency:
        return Decimal('1')
    key = f'{from_currency}_{to_currency}'
    rate = settings.EXCHANGE_RATES.get(key)
    if rate:
        return Decimal(str(rate))
    # Try reverse
    reverse_key = f'{to_currency}_{from_currency}'
    reverse_rate = settings.EXCHANGE_RATES.get(reverse_key)
    if reverse_rate:
        return Decimal('1') / Decimal(str(reverse_rate))
    return Decimal('1')  # fallback


def convert_amount(amount, from_currency, to_currency='INR'):
    """Convert an amount from one currency to another."""
    rate = get_exchange_rate(from_currency, to_currency)
    return (Decimal(str(amount)) * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def compute_group_balances(group, target_currency='INR'):
    """
    Compute net balances for all members in a group.

    Returns:
        {
            'balances': {user_id: net_balance},  # positive = owed money, negative = owes money
            'settlements_needed': [(payer_id, payee_id, amount)],  # optimized
            'per_user_breakdown': {user_id: {'total_paid': X, 'total_owed': Y, 'expenses': [...]}}
        }
    """
    # Net balance: positive = person is owed money, negative = person owes money
    net = defaultdict(lambda: Decimal('0'))
    user_breakdown = defaultdict(lambda: {
        'total_paid': Decimal('0'),
        'total_owed': Decimal('0'),
        'expenses': []
    })

    # Process expenses
    expenses = Expense.objects.filter(
        group=group, is_settlement=False
    ).prefetch_related('splits__user', 'paid_by').order_by('date')

    for expense in expenses:
        paid_by_id = expense.paid_by_id
        amount_in_target = convert_amount(expense.amount, expense.currency, target_currency)

        # Payer paid this amount
        net[paid_by_id] += amount_in_target
        user_breakdown[paid_by_id]['total_paid'] += amount_in_target

        # Each participant owes their share
        for split in expense.splits.all():
            share_in_target = convert_amount(split.amount, expense.currency, target_currency)
            net[split.user_id] -= share_in_target
            user_breakdown[split.user_id]['total_owed'] += share_in_target
            user_breakdown[split.user_id]['expenses'].append({
                'expense_id': expense.id,
                'description': expense.description,
                'date': str(expense.date),
                'amount': str(share_in_target),
                'currency': target_currency,
                'original_amount': str(split.amount),
                'original_currency': expense.currency,
                'paid_by': expense.paid_by.username,
            })

        # Also add to payer's breakdown
        user_breakdown[paid_by_id]['expenses'].append({
            'expense_id': expense.id,
            'description': expense.description,
            'date': str(expense.date),
            'amount': str(amount_in_target),
            'currency': target_currency,
            'role': 'payer',
            'original_amount': str(expense.amount),
            'original_currency': expense.currency,
        })

    # Process settlements
    settlements = Settlement.objects.filter(group=group)
    for s in settlements:
        amount_in_target = convert_amount(s.amount, s.currency, target_currency)
        net[s.paid_by_id] += amount_in_target  # payer gets credit
        net[s.paid_to_id] -= amount_in_target  # receiver loses credit

    # Compute optimized settlements
    settlements_needed = optimize_settlements(dict(net))

    # Build result
    balances = {uid: str(bal.quantize(Decimal('0.01'))) for uid, bal in net.items()}

    # Serialize breakdown
    breakdown = {}
    for uid, data in user_breakdown.items():
        breakdown[uid] = {
            'total_paid': str(data['total_paid'].quantize(Decimal('0.01'))),
            'total_owed': str(data['total_owed'].quantize(Decimal('0.01'))),
            'net': str(net.get(uid, Decimal('0')).quantize(Decimal('0.01'))),
            'expenses': data['expenses'],
        }

    return {
        'balances': balances,
        'settlements_needed': settlements_needed,
        'per_user_breakdown': breakdown,
        'currency': target_currency,
    }


def optimize_settlements(net_balances):
    """
    Minimize the number of transactions to settle all debts.
    Uses a greedy algorithm: match largest creditor with largest debtor.

    This is Aisha's request: "one number per person, who pays whom, done."
    """
    creditors = []  # people owed money (positive balance)
    debtors = []    # people who owe money (negative balance)

    for uid, balance in net_balances.items():
        bal = balance.quantize(Decimal('0.01'))
        if bal > Decimal('0.01'):
            creditors.append([uid, bal])
        elif bal < Decimal('-0.01'):
            debtors.append([uid, -bal])  # store as positive

    # Sort by amount descending
    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)

    settlements = []
    i, j = 0, 0

    while i < len(creditors) and j < len(debtors):
        creditor_id, credit = creditors[i]
        debtor_id, debt = debtors[j]

        amount = min(credit, debt)
        if amount > Decimal('0.01'):
            settlements.append({
                'from_user_id': debtor_id,
                'to_user_id': creditor_id,
                'amount': str(amount),
            })

        creditors[i][1] -= amount
        debtors[j][1] -= amount

        if creditors[i][1] <= Decimal('0.01'):
            i += 1
        if debtors[j][1] <= Decimal('0.01'):
            j += 1

    return settlements
