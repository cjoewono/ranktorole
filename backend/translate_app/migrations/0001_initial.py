import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Resume',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('military_text', models.TextField()),
                ('job_description', models.TextField()),
                ('session_anchor', models.JSONField(blank=True, null=True)),
                ('approved_bullets', models.JSONField(default=list)),
                ('rejected_bullets', models.JSONField(default=list)),
                ('civilian_title', models.CharField(max_length=255)),
                ('summary', models.TextField()),
                ('bullets', models.JSONField(default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='resumes',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'resumes',
                'ordering': ['-created_at'],
            },
        ),
    ]
