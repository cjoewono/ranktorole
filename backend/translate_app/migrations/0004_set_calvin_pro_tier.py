from django.db import migrations


def set_calvin_pro(apps, schema_editor):
    User = apps.get_model("user_app", "User")
    User.objects.filter(email="calvinjoewono@gmail.com").update(tier="pro")


def reverse_calvin_pro(apps, schema_editor):
    User = apps.get_model("user_app", "User")
    User.objects.filter(email="calvinjoewono@gmail.com").update(tier="free")


class Migration(migrations.Migration):

    dependencies = [
        ("translate_app", "0003_resume_ai_initial_draft_resume_chat_history_and_more"),
        ("user_app", "0004_user_tier"),
    ]

    operations = [
        migrations.RunPython(set_calvin_pro, reverse_calvin_pro),
    ]
