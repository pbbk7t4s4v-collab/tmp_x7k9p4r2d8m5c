# TeachMaster

TeachMaster is a platform for generating machine-learning education content and managing courses. It includes a React-based frontend and a FastAPI backend with an ARQ worker.

## Table of Contents
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Start Infrastructure](#start-infrastructure)
  - [Run Backend](#run-backend)
  - [Run Frontend](#run-frontend)
- [Services and Ports](#services-and-ports)
- [Backend Routes](#backend-routes)
- [Deployment Notes](#deployment-notes)
- [Troubleshooting](#troubleshooting)

## Features
- ML education content generation
- Course management and sharing
- Token and wallet management
- Admin tools and feedback collection

## Tech Stack
- Frontend: React 18, Ant Design, React Router, React Query, Zustand, i18next
- Backend: FastAPI, Uvicorn, ARQ, Redis, MySQL

## Project Structure
```
.
├─ backend/              # FastAPI backend and ARQ worker
├─ frontend/             # React frontend
├─ docker-compose.yml    # MySQL and Redis
├─ start.sh              # Starts ARQ worker + backend
└─ README.md
```

## Getting Started

### Prerequisites
- Docker (for MySQL/Redis)
- Node.js and npm (for frontend)
- Python 3.8+ (for backend)

### Start Infrastructure
```bash
docker compose up -d
```

### Run Backend
Backend entry: `backend/main.py`.

There are two scripts:
- `start.sh`: runs from repo root; starts ARQ worker then FastAPI
- `backend/start.sh`: starts backend inside `backend/`

Use the one that matches your environment. Adjust conda/venv logic if needed.

### Run Frontend
```bash
cd frontend
npm install
npm start
```
Default dev URL: `http://localhost:3000` (adjust via `.env` if needed).

## Services and Ports
- Backend API: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`
- MySQL: `localhost:3306`
- Redis: `localhost:6379`

> Ports and hosts may vary with your `.env` or deployment configuration.

## Backend Routes
Routes are defined under `backend/app/api/`:
- `auth`, `content`, `course-management`
- `course-sharing`, `course-user-sharing`
- `tokens`, `tcoin`
- `admin`, `feedback`
- `health`

## Deployment Notes
- Use `docker-compose.yml` for local MySQL/Redis.
- Frontend includes `frontend/Dockerfile` and `frontend/nginx.conf`.
- Backend includes `backend/Dockerfile` for containerization.

## Troubleshooting
- Backend fails to start: verify Python deps, database connection, and Redis settings.
- ARQ worker can't connect to Redis: confirm Redis host/port alignment.
