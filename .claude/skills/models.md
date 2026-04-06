# Skill: Django Models

Load this file when working on: models, migrations,
serializers, admin, or database schema.

## Global Rules
- All models use UUIDv4 primary key:
  id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
- All models include: created_at, updated_at (auto_now_add / auto_now)
- All querysets scoped to request.user in views
- Never change a field name after migration has run
- Never delete a migration file
- Run makemigrations after every model change
- Run migrate after every makemigrations

## Models

### User (user_app/models.py)
Extends AbstractUser
Fields: id (UUID), email, created_at, updated_at
Note: use email as USERNAME_FIELD

### Resume (resume_app/models.py)
Fields:
  id: UUIDv4 PK
  user: FK → User (on_delete=CASCADE)
  military_text: TextField
  job_description: TextField
  civilian_title: CharField(max_length=255)
  summary: TextField
  bullets: JSONField (list of strings)
  created_at: auto
  updated_at: auto

CRUD: Create (translate), Read (list/detail), Update (edit output), Delete
This is CRUD model #1

### Contact (contact_app/models.py) — from BridgeBoard
Fields:
  id: UUIDv4 PK
  user: FK → User (on_delete=CASCADE)
  name: CharField
  email: EmailField
  company: CharField
  role: CharField
  notes: TextField (blank=True)
  created_at: auto
  updated_at: auto

CRUD: full Create, Read, Update, Delete
This is CRUD model #2

## Serializers
- Use DRF serializers for all data transformations
- Never return password or raw API keys in any serializer
- Read-only fields: id, created_at, updated_at, user
- Validate max lengths server-side in serializer

## Migration Workflow
1. Edit model
2. docker compose exec backend python manage.py makemigrations
3. docker compose exec backend python manage.py migrate
4. If full restart needed: docker compose down && docker compose up --build
   (new env vars require full restart, not just restart)

## Admin
Register all models in admin.py
Use list_display for key fields
Filter by user where applicable