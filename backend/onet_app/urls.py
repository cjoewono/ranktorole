# Intentionally empty — onet_app no longer exposes any endpoints.
# Kept as a Django app for the shared utility modules in views.py and
# recon_enrich_service.py. Remove the app entirely only after confirming
# no migrations reference it.

from django.urls import path  # noqa: F401  (stub to keep the module importable)

urlpatterns = []
