from django.urls import path

from .views import CourseListView, CourseDetailView, MyCourseListView

urlpatterns = [
    path('',         CourseListView.as_view(),   name='course-list'),
    path('me/',      MyCourseListView.as_view(),  name='course-me'),
    path('<slug:slug>/', CourseDetailView.as_view(), name='course-detail'),
]