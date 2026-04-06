import uuid
from django.conf import settings
from django.db import models


class Resume(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='resumes'
    )
    military_text = models.TextField()
    job_description = models.TextField()
    session_anchor = models.JSONField(null=True, blank=True)
    approved_bullets = models.JSONField(default=list)
    rejected_bullets = models.JSONField(default=list)
    civilian_title = models.CharField(max_length=255)
    summary = models.TextField()
    bullets = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'resumes'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} — {self.civilian_title}"
