from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── REST API ─────────────────────────────────────────────────────────────
    path('api/', include([
        # Auth — JWT token endpoints (no authentication required)
        path('auth/token/',          TokenObtainPairView.as_view(),  name='token-obtain'),
        path('auth/token/refresh/',  TokenRefreshView.as_view(),     name='token-refresh'),
        path('auth/token/verify/',   TokenVerifyView.as_view(),      name='token-verify'),

        # Resources
        path('courses/',  include('apps.academy.urls')),
        path('classes/',  include('apps.liveclasses.urls')),
        path('',          include('apps.core.urls')),
    ])),
]