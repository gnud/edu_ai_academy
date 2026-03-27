import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import CurrentUserSerializer

User = get_user_model()
logger = logging.getLogger(__name__)


class CurrentUserView(APIView):
    """GET /api/accounts/me/ — return the authenticated user's profile."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = CurrentUserSerializer(request.user)
        return Response(serializer.data)


class PasswordResetRequestView(APIView):
    """
    POST /api/auth/password/reset/
    Body: { username }

    Generates a reset token and (in production) emails a link.
    Always returns 200 to avoid leaking whether the username exists.
    In development the token is logged to the console.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username', '').strip()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Return 200 regardless — don't reveal whether username exists.
            return Response({'detail': 'If the username exists, a reset link has been sent.'})

        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        reset_link = f"{settings.FRONTEND_URL}/?token={token}&uid={uid}"

        if not user.email:
            logger.warning("User %s has no email address — reset link: %s", user.username, reset_link)
            return Response({'detail': 'If the username exists, a reset link has been sent.'})

        try:
            send_mail(
                subject="AI Academy — password reset",
                message=(
                    f"Hi {user.username},\n\n"
                    f"Click the link below to reset your password:\n\n"
                    f"{reset_link}\n\n"
                    f"If you didn't request this, ignore this email.\n"
                ),
                from_email="noreply@ai-academy.local",
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as e:
            logger.exception("Failed to send password reset email to user %s: %s", user.username, e)

        return Response({'detail': 'If the username exists, a reset link has been sent.'})


class PasswordResetConfirmView(APIView):
    """
    POST /api/auth/password/reset/confirm/
    Body: { uid, token, new_password1, new_password2 }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        uid          = request.data.get('uid', '')
        token        = request.data.get('token', '')
        new_password1 = request.data.get('new_password1', '')
        new_password2 = request.data.get('new_password2', '')

        if new_password1 != new_password2:
            return Response(
                {'detail': 'Passwords do not match.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            pk   = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=pk)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            return Response(
                {'detail': 'Invalid reset link.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {'detail': 'Reset link is invalid or has expired.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password1)
        user.save()
        return Response({'detail': 'Password reset successful.'})
