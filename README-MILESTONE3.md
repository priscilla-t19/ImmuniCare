# ImmuniCare — Milestone 3: Patients and Guardians

This update was developed against the committed Milestone 2 source archive. It retains the existing authentication, clinic, staff, and session routes.

## Changes

- `0002_patients_guardians` Alembic migration creates `patients`, `guardians`, and `patient_guardians`.
- Clinic-scoped patient and guardian registration, lists, name search, details, and updates.
- Many-to-many patient–guardian linking and unlinking.
- Existing `clinic_access` dependency protects every new route; missing or foreign records return 404.
- API tests for CRUD, validation, duplicate constraints, clinician/receptionist access, and cross-clinic read/write isolation.
- React forms for patient and guardian registration, patient directory, and guardian linking.

## Installation (PowerShell)

1. Ensure Milestone 2 is committed: `git status`.
2. Extract this ZIP to a **separate temporary folder** and copy its contents into your existing `C:\Projects\immunicare` project, excluding any local `.env` (the ZIP has none). Do **not** delete your existing Docker volume.
3. In `C:\Projects\immunicare`:

```powershell
docker compose up -d --build
docker compose exec api alembic upgrade head
docker compose exec api alembic current
docker compose exec api python -m pytest -q tests
Invoke-RestMethod http://localhost:8001/ready
```

Expected Alembic revision: `0002_patients_guardians (head)`.
Expected test count: **7 passed** (4 existing + 3 new) in the provided test environment.
Open `http://localhost:5174` and log in to your existing clinic; register synthetic patient and guardian records and link them.

## Manual security checks

1. Sign into Clinic A; create a synthetic patient and guardian and link them.
2. Sign into Clinic B with a separate account; verify Clinic A's records are absent.
3. The automated tests also call the API directly using foreign clinic IDs and foreign patient/guardian IDs, asserting 404 for cross-clinic reads and writes.
4. Log in as a clinician or receptionist; verify registration works but staff-admin operations remain forbidden.

## Known limitations / future hardening

- This is a **development prototype**. Never use real children's or guardians' identity/health information.
- The patient birth certificate number is unique **within a clinic**, not across all clinics. It is displayed to authorised clinic staff; consider masking and access segmentation for a production system.
- Guardian identity numbers are optional and deliberately omitted from API responses; do not enter real IDs.
- All three existing clinic roles can create and update patient/guardian records. Production permissions must be refined based on clinic policies.
- Search is name-only, capped at 100 results, without pagination.
- The current bearer token is kept in React memory and will be lost on refresh; this avoids persistent browser storage but isn't a complete production authentication design.
- The application enforces clinic isolation in route dependencies and SQL filters; **PostgreSQL row-level security and database-level same-tenant link constraints are not yet implemented**.
- This milestone does not implement vaccination scheduling, clinical decision support, patient deletion, record audit logging, consent workflows, or production compliance.
- SQLite API tests passed in the build environment; Docker/PostgreSQL and frontend build must be verified on the user's machine.
