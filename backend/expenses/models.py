"""Expense, split, and settlement models."""
from django.db import models
from django.contrib.auth.models import User
from groups.models import Group


class Expense(models.Model):
    SPLIT_TYPE_CHOICES = [
        ('equal', 'Equal'),
        ('unequal', 'Unequal'),
        ('percentage', 'Percentage'),
        ('share', 'Share / Ratio'),
    ]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='expenses')
    description = models.CharField(max_length=500)
    paid_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses_paid')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    split_type = models.CharField(max_length=20, choices=SPLIT_TYPE_CHOICES)
    date = models.DateField()
    notes = models.TextField(blank=True, default='')
    is_settlement = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Track if imported from CSV
    imported_from = models.CharField(max_length=100, blank=True, default='')
    import_row = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.description} - {self.currency} {self.amount}'


class ExpenseSplit(models.Model):
    """Individual share of an expense for each participant."""
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='splits')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expense_splits')
    amount = models.DecimalField(max_digits=12, decimal_places=2,
                                 help_text='Amount owed by this user in original currency')

    class Meta:
        unique_together = ('expense', 'user')

    def __str__(self):
        return f'{self.user.username} owes {self.amount} for {self.expense.description}'


class Settlement(models.Model):
    """Record of a payment/settlement between two users."""
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='settlements')
    paid_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='settlements_paid')
    paid_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='settlements_received')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    date = models.DateField()
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.paid_by.username} → {self.paid_to.username}: {self.currency} {self.amount}'
