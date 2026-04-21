"""
POST /api/v1/recon/brainstorm/ — form-driven career brainstorm.

Profile-decoupled. The request body is the sole source of signal. User is
required only for auth + throttling.
"""

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from translate_app.throttles import ReconEnrichThrottle

from .serializers import BrainstormInputSerializer
from .services import run_brainstorm

logger = logging.getLogger(__name__)


class BrainstormView(APIView):
    """Form in, ranked career match out. No DB writes. Fully ephemeral."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ReconEnrichThrottle]

    def post(self, request):
        serializer = BrainstormInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Invalid form payload.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = run_brainstorm(serializer.validated_data)
        if result is None:
            return Response(
                {"error": "Could not reach O*NET for any service entry. Try again shortly."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(result, status=status.HTTP_200_OK)
