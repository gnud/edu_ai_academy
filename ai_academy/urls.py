from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from apps.accounts.urls import password_reset_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── REST API ─────────────────────────────────────────────────────────────
    path('api/', include([
        # Auth — JWT token endpoints (no authentication required)
        path('auth/token/',          TokenObtainPairView.as_view(),  name='token-obtain'),
        path('auth/token/refresh/',  TokenRefreshView.as_view(),     name='token-refresh'),
        path('auth/token/verify/',   TokenVerifyView.as_view(),      name='token-verify'),
        path('auth/',                include(password_reset_urlpatterns)),

        # Resources
        path('accounts/', include('apps.accounts.urls')),
        path('courses/',  include('apps.academy.urls')),
        path('classes/',  include('apps.liveclasses.urls')),
        path('messages/', include('apps.communication.urls')),
        path('',          include('apps.core.urls')),
    ])),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)