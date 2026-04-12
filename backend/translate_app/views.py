import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView


class UploadThrottle(UserRateThrottle):
    scope = "user_upload"


class DraftThrottle(UserRateThrottle):
    scope = "user_draft"


class ChatThrottle(UserRateThrottle):
    scope = "user_chat"


class FinalizeThrottle(UserRateThrottle):
    scope = "user_draft"  # reuse the draft rate bucket — 20/day is reasonable


from .models import Resume
from .serializers import DraftInputSerializer, FinalizeInputSerializer, ResumeSerializer
from .services import (
    call_claude_chat,
    call_claude_draft,
    compress_session_anchor,
    extract_pdf_text,
)

logger = logging.getLogger(__name__)


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

    def delete(self, request, pk):
        try:
            resume = Resume.objects.get(pk=pk, user=request.user)
        except Resume.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        resume.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ResumeUploadView(APIView):
    """POST /api/v1/resumes/upload/ — extract PDF text and create a Resume record."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [UploadThrottle]

    def post(self, request):
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response(
                {"error": "No file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if uploaded_file.size > 10 * 1024 * 1024:
            return Response(
                {"error": "File too large. Maximum size is 10MB."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if uploaded_file.content_type != "application/pdf":
            return Response(
                {"error": "Only PDF files are accepted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        magic_bytes = uploaded_file.read(5)
        if not magic_bytes.startswith(b"%PDF-"):
            return Response(
                {"error": "Invalid file signature. File is not a true PDF."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        uploaded_file.seek(0)

        file_bytes = uploaded_file.read()

        try:
            military_text = extract_pdf_text(file_bytes)
        except Exception:
            logger.error("PDF extraction failed")
            return Response(
                {"error": "Failed to extract text from PDF."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not military_text.strip():
            return Response(
                {"error": "PDF yielded no extractable text."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        resume = Resume.objects.create(
            user=request.user,
            military_text=military_text,
            job_description="",
            civilian_title="",
            summary="",
            is_finalized=False,
        )

        return Response(
            {"id": str(resume.id), "created_at": resume.created_at},
            status=status.HTTP_201_CREATED,
        )


class ResumeDraftView(APIView):
    """POST /api/v1/resumes/{id}/draft/ — generate draft + clarifying questions via Claude."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [DraftThrottle]

    def post(self, request, pk):
        try:
            resume = Resume.objects.get(pk=pk, user=request.user)
        except Resume.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        input_ser = DraftInputSerializer(data=request.data)
        if not input_ser.is_valid():
            return Response(input_ser.errors, status=status.HTTP_400_BAD_REQUEST)
        job_description = input_ser.validated_data.get("job_description", "")

        try:
            translation = call_claude_draft(
                resume.military_text,
                job_description,
                request.user.profile_context,
            )
        except ValueError:
            return Response(
                {"error": "Invalid response from AI service."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except Exception:
            logger.error("Claude API failure during draft generation")
            return Response(
                {"error": "Translation service unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        roles_data = [r.model_dump() for r in translation.roles]

        anchor = {
            "civilian_title": translation.civilian_title,
            "summary": translation.summary,
            "roles": roles_data,
            "job_description_snippet": job_description[:300],
            "profile_context": request.user.profile_context,
        }

        resume.job_description = job_description
        resume.civilian_title = translation.civilian_title
        resume.summary = translation.summary
        resume.roles = roles_data
        resume.ai_initial_draft = roles_data
        resume.session_anchor = anchor
        resume.chat_history = []
        resume.save()

        return Response(
            {
                "civilian_title": translation.civilian_title,
                "summary": translation.summary,
                "roles": roles_data,
                "clarifying_question": translation.clarifying_question,
                "assistant_reply": translation.assistant_reply,
            },
            status=status.HTTP_200_OK,
        )


class ResumeChatView(APIView):
    """POST /api/v1/resumes/{id}/chat/ — stateful refinement turn via Claude (history from DB)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ChatThrottle]

    def post(self, request, pk):
        try:
            resume = Resume.objects.get(pk=pk, user=request.user)
        except Resume.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        message = request.data.get("message", "").strip()
        if not message:
            return Response(
                {"error": "message is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        anchor = resume.session_anchor
        if not anchor:
            return Response(
                {"error": "Draft not yet generated. Call /draft/ first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        chat_history: list[dict] = list(resume.chat_history or [])

        try:
            result = call_claude_chat(anchor, chat_history, message)
        except ValueError:
            return Response(
                {"error": "Invalid response from AI service."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except Exception:
            logger.error("Claude API failure during chat refinement")
            return Response(
                {"error": "Translation service unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        roles_data = [r.model_dump() for r in result.translation.roles]

        resume.chat_history = result.updated_history
        resume.roles = roles_data
        resume.civilian_title = result.translation.civilian_title
        resume.summary = result.translation.summary
        resume.save()

        return Response(
            {
                "roles": roles_data,
                "assistant_reply": result.translation.assistant_reply,
                "civilian_title": result.translation.civilian_title,
                "summary": result.translation.summary,
            },
            status=status.HTTP_200_OK,
        )


class ResumeFinalizeView(APIView):
    """PATCH /api/v1/resumes/{id}/finalize/ — save final edits and set is_finalized=True."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [FinalizeThrottle]

    def patch(self, request, pk):
        try:
            resume = Resume.objects.get(pk=pk, user=request.user)
        except Resume.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        ser = FinalizeInputSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        validated = ser.validated_data

        for field in ("civilian_title", "summary"):
            if field in validated:
                setattr(resume, field, validated[field])

        if "roles" in validated:
            resume.roles = validated["roles"]

        resume.is_finalized = True
        resume.save()

        return Response(ResumeSerializer(resume).data, status=status.HTTP_200_OK)
