from django.urls import path

from .views import OnetSearchView

urlpatterns = [
    path("search/", OnetSearchView.as_view(), name="onet-search"),
]
