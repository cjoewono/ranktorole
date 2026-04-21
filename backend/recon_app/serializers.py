"""
Input validation for POST /api/v1/recon/brainstorm/.

The Recon form is the sole source of signal for a brainstorm — profile_context
is never read. This serializer enforces the shape and limits so the view logic
and Haiku prompt can trust their inputs.
"""

from rest_framework import serializers


VALID_BRANCHES = {
    "Army", "Navy", "Air Force", "Marine Corps",
    "Coast Guard", "Space Force",
}


class ServiceEntrySerializer(serializers.Serializer):
    branch = serializers.CharField(max_length=50)
    mos_code = serializers.CharField(max_length=20)

    def validate_branch(self, value: str) -> str:
        value = value.strip()
        if value not in VALID_BRANCHES:
            raise serializers.ValidationError(
                f"branch must be one of: {sorted(VALID_BRANCHES)}"
            )
        return value

    def validate_mos_code(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("mos_code cannot be blank.")
        return value


class BrainstormInputSerializer(serializers.Serializer):
    services = ServiceEntrySerializer(many=True, min_length=1, max_length=5)
    grade = serializers.CharField(max_length=10, required=False, allow_blank=True, default="")
    position = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    target_career_field = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )
    education = serializers.ListField(
        child=serializers.CharField(max_length=200),
        required=False,
        default=list,
        max_length=10,
    )
    certifications = serializers.ListField(
        child=serializers.CharField(max_length=200),
        required=False,
        default=list,
        max_length=20,
    )
    licenses = serializers.ListField(
        child=serializers.CharField(max_length=200),
        required=False,
        default=list,
        max_length=20,
    )
    state = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
