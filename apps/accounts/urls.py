from django.urls import path

from .views import CurrentUserView, PasswordResetConfirmView, PasswordResetRequestView

urlpatterns = [
    path('me/', CurrentUserView.as_view(), name='current-user'),
]

# Password-reset endpoints live under /api/auth/ (not /api/accounts/)
# so they're exported separately and included by the root urls.py.
password_reset_urlpatterns = [
    path('password/reset/',         PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]