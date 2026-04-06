from django.urls import path

from .views import ResumeDetailView, ResumeListView

urlpatterns = [
    path("", ResumeListView.as_view(), name="resume-list"),
    path("<uuid:pk>/", ResumeDetailView.as_view(), name="resume-detail"),
]
