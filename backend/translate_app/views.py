import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Resume
from .serializers import ResumeSerializer, TranslationInputSerializer
from .services import compress_session_anchor

logger = logging.getLogger(__name__)


class TranslationView(APIView):
    """
    GET  /api/v1/translations/ — list resumes for authenticated user.
    POST /api/v1/translations/ — translate military text into a civilian resume.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        resumes = Resume.objects.filter(user=request.user)
        return Response(ResumeSerializer(resumes, many=True).data)

    def post(self, request):
        input_ser = TranslationInputSerializer(data=request.data)
        if not input_ser.is_valid():
            return Response(input_ser.errors, status=status.HTTP_400_BAD_REQUEST)

        military_text = input_ser.validated_data["military_text"]
        job_description = input_ser.validated_data["job_description"]

        try:
            anchor = compress_session_anchor(military_text, job_description)
        except ValueError:
            return Response(
                {"error": "Translation failed: invalid response from AI service."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except Exception:
            logger.error("Unexpected error during translation")
            return Response(
                {"error": "Translation service unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        resume = Resume.objects.create(
            user=request.user,
            military_text=military_text,
            job_description=job_description,
            session_anchor=anchor,
            civilian_title=anchor["civilian_title"],
            summary=anchor["summary"],
            bullets=anchor["bullets"],
        )

        return Response(ResumeSerializer(resume).data, status=status.HTTP_201_CREATED)


class ResumeListView(APIView):
    """GET /api/v1/resumes/ — list all resumes for authenticated user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        resumes = Resume.objects.filter(user=request.user)
        return Response(ResumeSerializer(resumes, many=True).data)


class ResumeDetailView(APIView):
    """GET /api/v1/resumes/<pk>/ — retrieve a single resume scoped to request.user."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            resume = Resume.objects.get(pk=pk, user=request.user)
        except Resume.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ResumeSerializer(resume).data)
