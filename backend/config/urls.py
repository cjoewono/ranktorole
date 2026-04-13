"""
URL configuration for RankToRole project.

All application routes are prefixed with /api/v1/.
"""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.urls import include, path


def health_check(request):
    try:
        get_user_model().objects.exists()
        return JsonResponse({"status": "ok"}, status=200)
    except Exception:
        return JsonResponse({"status": "error"}, status=503)


urlpatterns = [
    path('health/', health_check, name='health-check'),
    path('admin/', admin.site.urls),
    path('api/v1/translations/', include('translate_app.urls')),
    path('api/v1/resumes/', include('translate_app.resume_urls')),
    path('api/v1/auth/', include('user_app.urls')),
    path('api/v1/contacts/', include('contact_app.urls')),
    path('api/v1/onet/', include('onet_app.urls')),
    # Social auth
    path('', include('social_django.urls', namespace='social')),
]
