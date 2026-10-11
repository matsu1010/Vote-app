# Vote App — Local-first voting with selected admin result delivery

This project is built for a privacy-first voting flow:

- customer vote data stays local on the customer device
- only the selected admin receives the result summary
- each question can have one or more designated admin recipients
- raw vote data is not stored centrally by default

## Stack

- Backend: FastAPI
- Database: PostgreSQL
- Frontend: plain HTML + JavaScript
- Result delivery: webhook summary forwarding

## Run locally

### 1) Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2) Database

Start PostgreSQL locally, then create the DB:

```bash
createdb vote_app_db
```

### 3) Start backend

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4) Start mock admin webhook

```bash
uvicorn backend.app.mock_admin_webhook:app --host 0.0.0.0 --port 9000
```

### 5) Open frontend pages

Use a local static server:

```bash
python -m http.server 8080
```

Then open:
- http://localhost:8080/frontend/index.html
- http://localhost:8080/frontend/login.html
- http://localhost:8080/frontend/admin.html
- http://localhost:8080/frontend/voter.html

## Admin flow

1. Log in as admin
2. Create a question
3. Assign a recipient admin
4. Enter question ID in voter page
5. Save a vote locally
6. Submit the summary to admin
7. Admin receives a summary payload at the configured webhook URL

## Example admin assignment

```bash
curl -X POST http://localhost:8000/api/admin/questions/QUESTION_ID/recipients \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "admin_id": "ADMIN_USER_UUID",
    "delivery_mode": "summary",
    "destination_url": "http://localhost:9000/webhook"
  }'
```

## Example result forwarding

```bash
curl -X POST http://localhost:8000/api/results/question/QUESTION_ID/forward \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

## Privacy model

This app is intentionally local-first:
- raw vote data stays on the voter’s device
- backend receives only aggregate summary data
- admin recipient configuration is stored in the server
- raw vote archive is optional, not default
