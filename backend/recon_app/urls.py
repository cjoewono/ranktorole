from django.urls import path

from .views import BrainstormView

urlpatterns = [
    path("brainstorm/", BrainstormView.as_view(), name="recon-brainstorm"),
]
