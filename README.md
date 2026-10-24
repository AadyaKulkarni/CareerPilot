# Placement Readiness & Career Intelligence Portal

A production-oriented starter for a student placement/career intelligence platform.

## Stack
- Frontend: React + TypeScript + Vite + Tailwind CSS + Recharts
- Backend: FastAPI + SQLAlchemy + JWT
- Database: PostgreSQL
- Cache/queue-ready: Redis
- ML: scikit-learn rule/feature-based career-fit engine (replaceable by trained models)
- LLM: provider abstraction with OpenAI-compatible HTTP support and secure server-side API keys

## Quick start with Docker
1. Install Docker Desktop.
2. Copy `.env.example` to `.env` and update secrets if needed.
3. Run `docker compose up --build`.
4. Open http://localhost:5173.
5. API docs: http://localhost:8000/docs

## Local development
### Backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## LLM keys
The app supports a user-level LLM configuration from Settings. Keys are accepted by the backend only and encrypted at rest using `SECRET_KEY`. Do not put user keys in frontend code.

The included `.env` intentionally contains empty LLM keys. Add your own key through the UI or environment variables for development.


## AI agents (matches the project brief)

| Agent | What it does | Code |
|---|---|---|
| **Resume Agent** | Upload PDF/DOCX/TXT, extract contact, education, skills, projects, experience; ATS-style score (100 pts) with concrete fixes; optionally merges findings into your profile without overwriting your entries | `backend/app/agents/resume_agent.py` |
| **Skill Gap Agent** | Compares skills evidence (profile + resume + projects + coding) with role requirements; prioritised gap report, effort estimates, closest alternative roles | `skill_gap_agent.py`, role data in `catalog.py` |
| **Coding Analytics Agent** | Fetches public stats from LeetCode, Codeforces and GitHub (or manual entry); coding score, difficulty mix, strengths/gaps, recommendations | `coding_agent.py` |
| **Job Matching Agent** | Ranks companies/roles using skill coverage, TF-IDF profile similarity, DSA fit and CGPA; matches pasted job descriptions | `job_agent.py`, data in `app/data/companies.json` |
| **Interview Agent** | Mock interview (HR, technical, project, behavioural) from your role/skills/projects; LLM evaluation if a key is configured, otherwise keyword + STAR-structure scoring | `interview_agent.py` |

### Expected outputs
- **Placement readiness score** (`GET /api/readiness`): transparent weighted blend (profile 8, academics 10, skills 24, portfolio 10, resume 13, coding 20, interview 15). Areas not yet assessed count as zero and are flagged, so the score cannot look better than the evidence.
- **Skill-gap report** (`GET /api/skills/gap?target_role=`)
- **Company / role matches** (`GET /api/companies/matches`, `POST /api/job/match`)
- **Learning roadmap** (`POST /api/roadmap/generate`): week-by-week plan from gaps in every agent, shown on the Learning Roadmap page.

### New API endpoints
`POST /resume/parse` (multipart) · `POST /resume/analyze-text` · `GET /resume/latest` · `GET /skills/gap` · `GET /roles` · `POST /coding/sync` · `POST /coding/manual` · `GET /coding/analytics` · `DELETE /coding/{platform}` · `GET /companies/matches` · `POST /job/match` · `POST /interview/start` · `POST /interview/{id}/answer` · `POST /interview/{id}/finish` · `GET /interview/sessions` · `GET /interview/{id}` · `GET /readiness` · `POST /roadmap/generate`

### Notes and limits
- **Embeddings:** similarity uses TF-IDF (offline, no key). `agents/similarity.py` is the single place to swap in neural embeddings.
- **Company catalog is illustrative.** Cut-offs and hiring processes are approximations; edit `app/data/companies.json` for your campus drives.
- **Coding platforms:** the backend calls LeetCode (unofficial GraphQL), Codeforces and GitHub public APIs. LeetCode's endpoint is unofficial and may change or rate-limit; manual entry is the fallback.
- **LLM providers:** OpenAI, Gemini and Anthropic (Settings page). Without a key the Interview Agent uses its offline question bank and heuristic scoring; heuristics reward keyword coverage and cannot verify correctness.
- **Database:** new tables (`resume_analyses`, `coding_stats`, `interview_sessions`, `readiness_snapshots`) are created automatically on startup. No existing table was changed, so no migration is needed.

### Tests
```bash
cd backend && python -m unittest discover -s tests -v
```

## Demo account
The backend exposes registration. Create your own account from the UI.
