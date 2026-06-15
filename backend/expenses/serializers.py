"""Expense and settlement serializers."""
from django.contrib.auth.models import User
from rest_framework import serializers
from accounts.serializers import UserMinimalSerializer
from .models import Expense, ExpenseSplit, Settlement


class ExpenseSplitSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='user', write_only=True
    )

    class Meta:
        model = ExpenseSplit
        fields = ('id', 'user', 'user_id', 'amount')


class ExpenseSerializer(serializers.ModelSerializer):
    paid_by_detail = UserMinimalSerializer(source='paid_by', read_only=True)
    splits = ExpenseSplitSerializer(many=True, read_only=True)

    class Meta:
        model = Expense
        fields = ('id', 'group', 'description', 'paid_by', 'paid_by_detail',
                  'amount', 'currency', 'split_type', 'date', 'notes',
                  'is_settlement', 'splits', 'created_at')
        read_only_fields = ('id', 'created_at')


class ExpenseCreateSerializer(serializers.ModelSerializer):
    splits = serializers.ListField(child=serializers.DictField(), write_only=True)

    class Meta:
        model = Expense
        fields = ('group', 'description', 'paid_by', 'amount', 'currency',
                  'split_type', 'date', 'notes', 'is_settlement', 'splits')

    def create(self, validated_data):
        splits_data = validated_data.pop('splits')
        expense = Expense.objects.create(**validated_data)
        for split in splits_data:
            ExpenseSplit.objects.create(
                expense=expense,
                user_id=split['user_id'],
                amount=split['amount']
            )
        return expense


class SettlementSerializer(serializers.ModelSerializer):
    paid_by_detail = UserMinimalSerializer(source='paid_by', read_only=True)
    paid_to_detail = UserMinimalSerializer(source='paid_to', read_only=True)

    class Meta:
        model = Settlement
        fields = ('id', 'group', 'paid_by', 'paid_by_detail',
                  'paid_to', 'paid_to_detail', 'amount', 'currency',
                  'date', 'notes', 'created_at')
        read_only_fields = ('id', 'created_at')
