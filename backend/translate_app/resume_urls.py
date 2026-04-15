from django.urls import path

from .views import (
    ResumeChatView,
    ResumeDetailView,
    ResumeDraftView,
    ResumeFinalizeView,
    ResumeListView,
    ResumeReopenView,
    ResumeUploadView,
)

urlpatterns = [
    path("", ResumeListView.as_view(), name="resume-list"),
    path("upload/", ResumeUploadView.as_view(), name="resume-upload"),
    path("<uuid:pk>/", ResumeDetailView.as_view(), name="resume-detail"),
    path("<uuid:pk>/draft/", ResumeDraftView.as_view(), name="resume-draft"),
    path("<uuid:pk>/chat/", ResumeChatView.as_view(), name="resume-chat"),
    path("<uuid:pk>/finalize/", ResumeFinalizeView.as_view(), name="resume-finalize"),
    path("<uuid:pk>/reopen/", ResumeReopenView.as_view(), name="resume-reopen"),
]
