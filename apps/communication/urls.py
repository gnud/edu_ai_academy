from django.urls import path

from .views import MessageListCreateView, ParticipantStateView, ThreadDetailView, ThreadListCreateView

urlpatterns = [
    path('threads/',                         ThreadListCreateView.as_view(),  name='thread-list'),
    path('threads/<int:pk>/',                ThreadDetailView.as_view(),      name='thread-detail'),
    path('threads/<int:pk>/messages/',       MessageListCreateView.as_view(), name='thread-messages'),
    path('threads/<int:pk>/me/',             ParticipantStateView.as_view(),  name='thread-me'),
]