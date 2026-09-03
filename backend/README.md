# Backend Development Guide

## Setup Instructions

### 1. Create Python Virtual Environment
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup Environment Variables
```bash
cp .env.example .env
# Edit .env with your database connection and settings
```

### 4. Setup Database

First, create PostgreSQL database:
```bash
createdb vote_app_db
```

Then run migrations with Alembic (optional - tables created on first run):
```bash
alembic upgrade head
```

### 5. Run Development Server
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API documentation will be available at: http://localhost:8000/docs

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info

### Questions
- `GET /api/questions` - List all open questions
- `GET /api/questions/{id}` - Get specific question
- `POST /api/questions` - Create question (admin only)
- `PUT /api/questions/{id}` - Update question (admin only)
- `DELETE /api/questions/{id}` - Delete question (admin only)

### Votes
- `POST /api/votes/{question_id}` - Submit/update vote
- `GET /api/votes/{question_id}/my-vote` - Get user's vote
- `DELETE /api/votes/{vote_id}` - Delete vote

### Results
- `GET /api/results/{question_id}` - Get results for question
- `GET /api/results` - Get all results

### Admin
- `POST /api/admin/users/{user_id}/make-admin` - Promote user to admin (super admin only)
- `POST /api/admin/questions/{question_id}/close` - Close question (admin only)
- `GET /api/admin/logs` - Get admin action logs (admin only)

## Database Schema

### Users
- id (UUID, primary key)
- username (unique)
- email_hash (optional)
- password_hash
- is_admin
- is_super_admin
- created_at, updated_at

### Questions
- id (UUID, primary key)
- title
- description
- status (open/closed)
- require_email_verification
- allow_anonymous
- enable_data_retention
- created_at, closed_at, updated_at

### Votes
- id (UUID, primary key)
- user_id (foreign key)
- question_id (foreign key)
- answer
- created_at, updated_at
- Unique constraint: (user_id, question_id)

### Admin Action Log
- id (UUID, primary key)
- admin_id (foreign key)
- action_type
- action_details (JSON)
- target_resource_id
- created_at

## Features

✅ JWT Authentication with bcrypt password hashing
✅ Admin role management
✅ Question lifecycle management
✅ Vote submission and updates
✅ Real-time voting results
✅ Admin action audit logging
✅ CORS support
✅ Production-ready configuration

## Testing

Test authentication:
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password123"}'
```

Create question:
```bash
curl -X POST http://localhost:8000/api/questions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Do you like voting?","description":"A simple question"}'
```

Submit vote:
```bash
curl -X POST http://localhost:8000/api/votes/QUESTION_ID \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"answer":"Yes"}'
```

Get results:
```bash
curl http://localhost:8000/api/results/QUESTION_ID
```

## Deployment

### Using Docker
```bash
docker build -t vote-app-backend .
docker run -p 8000:8000 --env-file .env vote-app-backend
```

### Using Gunicorn (Production)
```bash
gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
```

### Environment Variables for Production
- Set `SECRET_KEY` to a strong random string
- Configure `DATABASE_URL` for your PostgreSQL instance
- Set `CORS_ORIGINS` to your frontend domain
- Use `https://` for production URLs
