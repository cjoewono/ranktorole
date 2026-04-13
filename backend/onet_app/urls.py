from django.urls import path
from .views import OnetCareerDetailView, OnetMilitarySearchView, OnetSearchView

urlpatterns = [
    path("search/", OnetSearchView.as_view(), name="onet-search"),
    path("military/", OnetMilitarySearchView.as_view(), name="onet-military-search"),
    path("career/<str:onet_code>/", OnetCareerDetailView.as_view(), name="onet-career-detail"),
]
