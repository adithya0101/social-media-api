# Social Media API

FastAPI-based social media platform with user auth and posts with images.


```bash
docker-compose up --build
```

API runs on `http://localhost:8000`

## Endpoints

### Auth
- `POST /auth/register` - Create account
- `POST /auth/login` - Get JWT token

### Users
- `GET /users/me` - Get current user (protected)
- `PUT /users/me` - Update current user (protected)
- `GET /users/{user_id}` - Get user by ID

### Posts
- `POST /posts` - Create post with optional image (protected)
- `GET /posts` - List posts (query params: `skip`, `limit`, `user_id`)
- `GET /posts/{post_id}` - Get post by ID
- `PUT /posts/{post_id}` - Update post (protected, owner only)
- `DELETE /posts/{post_id}` - Delete post (protected, owner only)
- `GET /posts/users/{user_id}/posts` - Get user's posts

## Usage Example

```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"john","email":"john@example.com","password":"pass123"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"john","password":"pass123"}'

# Create post (use token from login)
curl -X POST http://localhost:8000/posts \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "title=My Post" \
  -F "content=Hello world" \
  -F "image=@image.jpg"

# Get posts
curl http://localhost:8000/posts?skip=0&limit=10
```

## GCP Deployment (Cloud Run)

1. Build and push:
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/social-api
```

2. Deploy:
```bash
gcloud run deploy social-api \
  --image gcr.io/PROJECT_ID/social-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL=YOUR_CLOUD_SQL_URL,SECRET_KEY=YOUR_SECRET
```

3. Set up Cloud SQL (PostgreSQL) and connect via Cloud SQL Proxy or private IP.

## Structure

```
app/
├── auth/           # JWT auth logic
├── users/          # User CRUD
├── posts/          # Post CRUD + image handling
├── config.py       # Settings
├── database.py     # DB connection
├── models.py       # SQLAlchemy models
└── main.py         # FastAPI app
```
