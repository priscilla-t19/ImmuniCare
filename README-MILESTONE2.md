# ImmuniCare — Milestone 2: Identity and Multi-Tenancy

Based on the CSI481 Database Systems group assignment at the University of Botswana. This repository is an independently developed redesign and extension.

## What's new
- Clinic registration with unique slug and administrator account
- Argon2 password hashing and 8-hour revocable opaque bearer sessions (SHA-256 digests stored in DB)
- Clinic membership RBAC: admin, clinician, receptionist
- Clinic-scoped access controls; cross-clinic access returns 404
- Staff provisioning by clinic administrators (demo-only: administrator sets initial password)
- Alembic initial migration for identity tables
- React sign-in, registration, staff management dashboard
- Automated auth, role and cross-tenant tests (SQLite test database)

## Important security and product limitations
This is a **local development prototype**, not a production healthcare system. Do not use real medical data or deploy publicly. Login tokens live in React memory (refresh signs out). Staff onboarding uses admin-chosen passwords; replace with expiring invitation links and forced password setup before production. No password reset, email verification, login throttling, audit logging, CSRF-protected cookie auth, TLS termination, HIPAA/GDPR/Botswana Data Protection Act assessment, or PostgreSQL RLS yet. Future patient tables must include clinic scoping and security tests.

## Windows PowerShell installation
1. Save/commit Milestone 1. Back up your existing .env and database before migrations.
2. Extract the archive to a separate folder and copy its files into your existing `C:\Projects\immunicare`, **without deleting** `.env` or the PostgreSQL volume.
3. In project root:

```powershell
docker compose up -d --build
docker compose exec api alembic upgrade head
docker compose exec api alembic current
docker compose exec api python -m pytest -q tests
Invoke-RestMethod http://localhost:8001/ready
docker compose ps
```

4. Open http://localhost:5174 and select **Register a new clinic**.
5. Use fictional clinic and staff details only. Create a second clinic and confirm staff from the first cannot see its resources.

## Key API routes
- `POST /auth/register-clinic` (public; development-only open registration)
- `POST /auth/login` (public)
- `GET /auth/me` (bearer token)
- `POST /auth/logout` (bearer token)
- `GET /clinics/{clinic_id}` (clinic member)
- `GET /clinics/{clinic_id}/staff` (clinic admin)
- `POST /clinics/{clinic_id}/staff` (clinic admin)

## Validation
- `docker compose exec api python -m pytest -q tests`
- `docker compose exec api alembic current`
- `docker compose build --no-cache web` (production build uses Node stage, Nginx runtime has no npm)

## Git workflow
```powershell
git status
git add .
git commit -m "milestone 2: add clinic authentication and tenant isolation"
git push
```

Do not commit `.env` or real health data.
