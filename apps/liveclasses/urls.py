from django.urls import path

from .views import (
    BlackboardFileDeleteView,
    BlackboardFileListCreateView,
    BlackboardStateView,
    ClassSessionDetailView,
    ClassSessionListView,
    ClassroomGroupDetailView,
    ClassroomGroupListCreateView,
    ClassroomGroupMemberKickView,
    JoinSessionView,
    LeaveSessionView,
    SessionGroupingView,
    SessionParticipantListView,
)

urlpatterns = [
    path('',                                   ClassSessionListView.as_view(),          name='class-session-list'),
    path('<int:pk>/',                          ClassSessionDetailView.as_view(),        name='class-session-detail'),
    path('<int:pk>/participants/',             SessionParticipantListView.as_view(),    name='class-session-participants'),
    path('<int:pk>/join/',                     JoinSessionView.as_view(),               name='class-session-join'),
    path('<int:pk>/leave/',                    LeaveSessionView.as_view(),              name='class-session-leave'),
    path('<int:pk>/groups/',                   ClassroomGroupListCreateView.as_view(),  name='class-session-groups'),
    path('<int:pk>/groups/<int:gid>/',         ClassroomGroupDetailView.as_view(),      name='class-session-group-detail'),
    path('<int:pk>/groups/<int:gid>/members/<int:mid>/', ClassroomGroupMemberKickView.as_view(), name='class-session-group-member-kick'),
    path('<int:pk>/grouping/',                 SessionGroupingView.as_view(),           name='class-session-grouping'),
    path('<int:pk>/blackboard/',               BlackboardStateView.as_view(),           name='class-session-blackboard'),
    path('<int:pk>/blackboard/files/',         BlackboardFileListCreateView.as_view(),  name='class-session-blackboard-files'),
    path('<int:pk>/blackboard/files/<int:fid>/', BlackboardFileDeleteView.as_view(),   name='class-session-blackboard-file-delete'),
]
