"""Expense URL configuration."""
from django.urls import path
from . import views

urlpatterns = [
    path('group/<int:group_id>/', views.ExpenseListCreateView.as_view(), name='expense-list-create'),
    path('<int:pk>/', views.ExpenseDetailView.as_view(), name='expense-detail'),
    path('group/<int:group_id>/balances/', views.group_balances, name='group-balances'),
    path('group/<int:group_id>/balances/<int:user_id>/', views.user_balance_breakdown, name='user-balance-breakdown'),
    path('group/<int:group_id>/settlements/', views.SettlementListCreateView.as_view(), name='settlement-list-create'),
]
