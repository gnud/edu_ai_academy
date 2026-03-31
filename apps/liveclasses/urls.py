from django.urls import path

from .views import (
    ClassSessionDetailView,
    ClassSessionListView,
    JoinSessionView,
    LeaveSessionView,
    SessionParticipantListView,
)

urlpatterns = [
    path('',                              ClassSessionListView.as_view(),       name='class-session-list'),
    path('<int:pk>/',                     ClassSessionDetailView.as_view(),     name='class-session-detail'),
    path('<int:pk>/participants/',        SessionParticipantListView.as_view(), name='class-session-participants'),
    path('<int:pk>/join/',               JoinSessionView.as_view(),            name='class-session-join'),
    path('<int:pk>/leave/',              LeaveSessionView.as_view(),           name='class-session-leave'),
]
