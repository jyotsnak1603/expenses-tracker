"""Expense views."""
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from groups.models import Group
from .models import Expense, ExpenseSplit, Settlement
from .serializers import (
    ExpenseSerializer, ExpenseCreateSerializer, SettlementSerializer
)
from .balance_engine import compute_group_balances


class ExpenseListCreateView(generics.ListCreateAPIView):
    """List or create expenses for a group."""

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ExpenseCreateSerializer
        return ExpenseSerializer

    def get_queryset(self):
        group_id = self.kwargs['group_id']
        return Expense.objects.filter(
            group_id=group_id,
            group__memberships__user=self.request.user
        ).prefetch_related('splits__user', 'paid_by').distinct()

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['group'] = self.kwargs['group_id']
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        expense = serializer.save()
        return Response(
            ExpenseSerializer(expense).data,
            status=status.HTTP_201_CREATED
        )


class ExpenseDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ExpenseSerializer

    def get_queryset(self):
        return Expense.objects.filter(
            group__memberships__user=self.request.user
        ).prefetch_related('splits__user', 'paid_by').distinct()


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def group_balances(request, group_id):
    """Get computed balances for a group (Aisha's one-number view)."""
    group = get_object_or_404(Group, id=group_id, memberships__user=request.user)
    currency = request.query_params.get('currency', group.default_currency)
    result = compute_group_balances(group, target_currency=currency)

    # Enrich with user details
    user_ids = set()
    for uid in result['balances']:
        user_ids.add(int(uid))
    for s in result['settlements_needed']:
        user_ids.add(int(s['from_user_id']))
        user_ids.add(int(s['to_user_id']))

    users = {u.id: {'id': u.id, 'username': u.username, 'first_name': u.first_name}
             for u in User.objects.filter(id__in=user_ids)}

    # Replace IDs with user info in settlements
    for s in result['settlements_needed']:
        s['from_user'] = users.get(int(s['from_user_id']), {})
        s['to_user'] = users.get(int(s['to_user_id']), {})

    result['users'] = users
    return Response(result)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_balance_breakdown(request, group_id, user_id):
    """Get detailed expense breakdown for a specific user (Rohan's requirement)."""
    group = get_object_or_404(Group, id=group_id, memberships__user=request.user)
    result = compute_group_balances(group, target_currency=group.default_currency)
    breakdown = result['per_user_breakdown'].get(user_id, {
        'total_paid': '0', 'total_owed': '0', 'net': '0', 'expenses': []
    })
    user = get_object_or_404(User, id=user_id)
    breakdown['user'] = {
        'id': user.id, 'username': user.username, 'first_name': user.first_name
    }
    return Response(breakdown)


class SettlementListCreateView(generics.ListCreateAPIView):
    serializer_class = SettlementSerializer

    def get_queryset(self):
        group_id = self.kwargs['group_id']
        return Settlement.objects.filter(
            group_id=group_id,
            group__memberships__user=self.request.user
        ).distinct()

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['group'] = self.kwargs['group_id']
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
