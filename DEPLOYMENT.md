# GCP Deployment Guide

## Prerequisites
- GCP account with free tier credits
- gcloud CLI installed
- Project created in GCP Console

## Step 1: Setup GCP Project

```bash
# Set project
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable sqladmin.googleapis.com
```

## Step 2: Create Cloud SQL Instance (PostgreSQL)

```bash
# Create instance (db-f1-micro is free tier eligible)
gcloud sql instances create social-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

# Set postgres password
gcloud sql users set-password postgres \
  --instance=social-db \
  --password=YOUR_DB_PASSWORD

# Create database
gcloud sql databases create socialdb --instance=social-db

# Get connection name
gcloud sql instances describe social-db --format='value(connectionName)'
```

## Step 3: Build and Deploy to Cloud Run

```bash
# Build image
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/social-api

# Deploy to Cloud Run
gcloud run deploy social-api \
  --image gcr.io/YOUR_PROJECT_ID/social-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --add-cloudsql-instances YOUR_CONNECTION_NAME \
  --set-env-vars DATABASE_URL="postgresql://postgres:YOUR_DB_PASSWORD@/socialdb?host=/cloudsql/YOUR_CONNECTION_NAME" \
  --set-env-vars SECRET_KEY="$(openssl rand -hex 32)" \
  --set-env-vars ALGORITHM=HS256 \
  --set-env-vars ACCESS_TOKEN_EXPIRE_MINUTES=30 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 1
```

## Step 4: Test Deployment

```bash
# Get service URL
gcloud run services describe social-api --region us-central1 --format='value(status.url)'

# Test health endpoint
curl https://YOUR_SERVICE_URL/health
```

## Alternative: Using Docker Compose on Compute Engine

For more control and persistent storage:

```bash
# Create VM (f1-micro is free tier)
gcloud compute instances create social-api-vm \
  --machine-type=f1-micro \
  --zone=us-central1-a \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=30GB

# SSH into VM
gcloud compute ssh social-api-vm --zone=us-central1-a

# Install Docker and Docker Compose
sudo apt update
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER

# Clone your repo or upload files
# Then run:
docker-compose up -d
```

## Cost Optimization Tips

1. Cloud Run scales to zero when not used (free tier: 2M requests/month)
2. Cloud SQL: Use `db-f1-micro` (shared core, free tier eligible)
3. Set `--min-instances=0` to avoid idle charges
4. Use Cloud Build free tier: 120 build-minutes/day
5. Container Registry storage: First 0.5GB free

## Monitoring

```bash
# View logs
gcloud run services logs read social-api --region us-central1

# Check metrics
gcloud run services describe social-api --region us-central1
```
