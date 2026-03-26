from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── REST API ─────────────────────────────────────────────────────────────
    path('api/', include([
        path('courses/',  include('apps.academy.urls')),
        path('classes/',  include('apps.liveclasses.urls')),
        path('',          include('apps.core.urls')),
    ])),
]