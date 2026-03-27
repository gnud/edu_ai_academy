from django.urls import path

from .views import (
    ChangeEmailView,
    ChangePasswordView,
    CurrentUserView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
)

urlpatterns = [
    path('me/',          CurrentUserView.as_view(),  name='current-user'),
    path('me/password/', ChangePasswordView.as_view(), name='change-password'),
    path('me/email/',    ChangeEmailView.as_view(),    name='change-email'),
]

# Exported and included under /api/auth/ by the root urls.py
password_reset_urlpatterns = [
    path('password/reset/',         PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]