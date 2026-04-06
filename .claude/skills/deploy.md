# Skill: Deployment

Load this file when working on: EC2, production Docker,
Nginx, environment variables, or AWS configuration.

## Production Checklist
Before any deployment:
- DEBUG=False in production .env
- ALLOWED_HOSTS set to EC2 public IP or domain (no wildcard)
- SECRET_KEY is a new random value (not dev key)
- ANTHROPIC_API_KEY confirmed set
- GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET confirmed set
- DATABASE_URL points to production DB
- CORS_ALLOWED_ORIGINS set to frontend URL only

## EC2 Setup
- OS: Ubuntu 22.04 LTS
- Install: Docker, Docker Compose, git
- No credentials in any file — use IAM instance role
- Security group: ports 80 and 443 only
- Never open ports 8000, 5432, or 5173 externally

## Docker Production
- Use docker compose up --build -d for production start
- Never use docker compose down on production (use stop)
- Nginx handles SSL termination if cert is configured
- All services on internal Docker network only
- DB port never mapped to host in production

## Nginx
- /api/ → backend:8000 (proxy_pass)
- / → frontend:80 (built static files)
- Set proxy_set_header X-Real-IP, X-Forwarded-For
- Set client_max_body_size for resume text uploads

## Environment Variables
Production .env must include:
  DEBUG=False
  SECRET_KEY=
  ALLOWED_HOSTS=
  DATABASE_URL=
  ANTHROPIC_API_KEY=
  GOOGLE_CLIENT_ID=
  GOOGLE_CLIENT_SECRET=
  CORS_ALLOWED_ORIGINS=
  JWT_SECRET_KEY=

## IAM Role (no hardcoded credentials)
Attach role to EC2 with minimum permissions needed
Never run aws configure on the instance
Never store access keys in .env or any file

## Smoke Test After Deploy
1. GET / → frontend loads
2. POST /api/v1/auth/login/ → returns tokens
3. POST /api/v1/translations/ → returns translated resume
4. GET /api/v1/resumes/ → returns user resume list
5. Check docker compose logs -f for errors

## Rollback
git pull previous commit
docker compose up --build -d