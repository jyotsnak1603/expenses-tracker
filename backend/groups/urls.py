"""Group URL configuration."""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.GroupListCreateView.as_view(), name='group-list-create'),
    path('<int:pk>/', views.GroupDetailView.as_view(), name='group-detail'),
    path('<int:group_id>/members/', views.group_members, name='group-members'),
    path('<int:group_id>/members/add/', views.add_member, name='add-member'),
    path('<int:group_id>/members/<int:user_id>/', views.update_member, name='update-member'),
]
