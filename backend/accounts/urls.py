"""Account URL configuration."""
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', views.me, name='me'),
    path('profile/', views.update_profile, name='update_profile'),
    path('users/search/', views.search_users, name='search_users'),
]
