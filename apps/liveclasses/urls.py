from django.urls import path

from .views import ClassSessionListView

urlpatterns = [
    path('', ClassSessionListView.as_view(), name='class-session-list'),
]