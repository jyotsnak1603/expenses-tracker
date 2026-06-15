"""Import URL configuration."""
from django.urls import path
from . import views

urlpatterns = [
    path('group/<int:group_id>/upload/', views.upload_csv, name='import-upload'),
    path('<int:session_id>/', views.get_import_session, name='import-session'),
    path('<int:session_id>/issues/<int:issue_id>/', views.resolve_issue, name='resolve-issue'),
    path('<int:session_id>/resolve-auto/', views.resolve_all_auto, name='resolve-all-auto'),
    path('<int:session_id>/confirm/', views.confirm_import, name='confirm-import'),
]
