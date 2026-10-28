# ImmuniCare — Milestone 1

Multi-clinic infant immunisation SaaS foundation. **Synthetic data only. Not for clinical use.**

## Requirements
Docker Desktop with Compose; Node.js 22 for generating/verifying the lockfile.

## First setup (PowerShell)
```powershell
cd C:\Projects\immunicare
Copy-Item .env.example .env
cd frontend
npm install
cd ..
docker compose up --build -d
```

Open http://localhost:5174 and verify `API connected`.

## Checks
```powershell
docker compose ps
Invoke-RestMethod http://localhost:8001/health
Invoke-RestMethod http://localhost:8001/ready
docker compose exec api pytest -q tests
docker compose exec db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
cd frontend
npm run build
cd ..
```

## Security notes
Local development only. Change demo passwords before sharing. The database port is bound to loopback. No authentication, patient records, or tenant isolation exist in Milestone 1; these are Milestone 2+ tasks. Never use real patient data.
