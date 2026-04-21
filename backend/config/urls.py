"""
URL configuration for RankToRole project.

All application routes are prefixed with /api/v1/.
"""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.urls import include, path


def health_check(request):
    """Probe DB and cache. Returns 503 if either fails.

    Cache probe uses set/get round-trip so a broken Redis connection
    surfaces immediately rather than being silently absorbed.
    """
    checks = {"database": False, "cache": False}

    try:
        get_user_model().objects.exists()
        checks["database"] = True
    except Exception:
        pass

    try:
        from django.core.cache import cache
        cache.set("health_probe", "ok", 10)
        checks["cache"] = cache.get("health_probe") == "ok"
    except Exception:
        pass

    if all(checks.values()):
        return JsonResponse({"status": "ok", "checks": checks}, status=200)
    return JsonResponse({"status": "error", "checks": checks}, status=503)


urlpatterns = [
    path('health/', health_check, name='health-check'),
    path('admin/', admin.site.urls),
    path('api/v1/translations/', include('translate_app.urls')),
    path('api/v1/resumes/', include('translate_app.resume_urls')),
    path('api/v1/auth/', include('user_app.urls')),
    path('api/v1/contacts/', include('contact_app.urls')),
    path('api/v1/onet/', include('onet_app.urls')),
    path('api/v1/recon/', include('recon_app.urls')),
    path('api/v1/billing/', include('user_app.billing_urls')),
    # Social auth
    path('', include('social_django.urls', namespace='social')),
]
