from django.urls import path

from .views import HubView

urlpatterns = [
    path('hub/', HubView.as_view(), name='hub'),
]