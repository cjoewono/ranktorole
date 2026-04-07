from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Contact
from .serializers import ContactSerializer


class ContactListView(APIView):
    """
    GET  /api/v1/contacts/ — list contacts for authenticated user.
    POST /api/v1/contacts/ — create a contact for authenticated user.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        contacts = Contact.objects.filter(user=request.user)
        return Response(ContactSerializer(contacts, many=True).data)

    def post(self, request):
        serializer = ContactSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ContactDetailView(APIView):
    """
    GET    /api/v1/contacts/<pk>/ — retrieve a contact.
    PATCH  /api/v1/contacts/<pk>/ — partial update a contact.
    DELETE /api/v1/contacts/<pk>/ — delete a contact.
    """

    permission_classes = [IsAuthenticated]

    def _get_contact(self, pk, user):
        try:
            return Contact.objects.get(pk=pk, user=user)
        except Contact.DoesNotExist:
            return None

    def get(self, request, pk):
        contact = self._get_contact(pk, request.user)
        if contact is None:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ContactSerializer(contact).data)

    def patch(self, request, pk):
        contact = self._get_contact(pk, request.user)
        if contact is None:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ContactSerializer(contact, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        contact = self._get_contact(pk, request.user)
        if contact is None:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        contact.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
