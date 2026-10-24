# CareerPilot: Intelligent Career Development Platform

CareerPilot is an AI-powered student career development and placement-readiness platform. It helps students analyze their profiles, identify skill gaps, explore suitable career opportunities, track coding progress, practice interviews, and generate personalized learning roadmaps.

## Tech Stack

- **Frontend:** React, TypeScript, Vite
- **Backend:** Python, FastAPI
- **Database:** PostgreSQL, SQLAlchemy
- **Authentication:** JWT
- **Machine Learning:** scikit-learn and TF-IDF-based similarity
- **AI Integration:** Optional LLM APIs
- **Deployment:** Docker and Docker Compose

## Key Features

- **Resume Analysis:** Extracts resume information, calculates an ATS-style score, and suggests improvements.
- **Skill-Gap Analysis:** Compares student skills with target-role requirements and identifies areas for improvement.
- **Coding Analytics:** Supports coding-profile statistics from supported platforms and manual entries.
- **Job Matching:** Ranks suitable roles using profile similarity, skill coverage, coding performance, and academic information.
- **Mock Interviews:** Supports HR, technical, project, and behavioural interview practice.
- **Career Readiness:** Combines assessment information to estimate placement readiness.
- **Learning Roadmap:** Generates prioritized learning tasks based on identified skill gaps.
- **LLM Support:** Optional language-model integration for supported features.

## Run with Docker

1. Install Docker Desktop.
2. Open a terminal in the project root.
3. Copy `.env.example` to `.env` and configure the required environment variables.
4. Start the application:

   ```bash
   docker compose up --build
   ```

5. Open the frontend at `http://localhost:5173`.
6. Open the backend API documentation at `http://localhost:8000/docs`.

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment, then run:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

Open another terminal and run:

```bash
cd frontend
npm install
npm run dev
```

## Security Notes

- Keep API keys, passwords, and other secrets in environment variables or the application's secure configuration.
- Never commit your actual `.env` file or expose API keys in frontend code.
- Use `.env.example` to document required configuration variables without including real secrets.

## Project Structure

- `frontend/` — React and TypeScript user interface
- `backend/app/agents/` — career analysis and recommendation modules
- `backend/app/api/` — API routes and agent endpoints
- `backend/app/models/` — database models
- `backend/app/services/` — shared services, including LLM integration
- `backend/app/ml/` — machine-learning components
- `infra/` — deployment and scaling configuration

## Testing

Backend tests are located in `backend/tests/`. To run them:

```bash
cd backend
python -m unittest discover -s tests -v
```

## Future Enhancements

Potential enhancements include improved recommendation models, additional career data sources, expanded evaluation metrics, and MCP-based integration for exposing selected CareerPilot capabilities to compatible AI clients.