# GCP Deployment Guide (v2)

Deploys the API to **Cloud Run**, backed by **Cloud SQL (PostgreSQL)**, with images in
**Artifact Registry** and secrets in **Secret Manager**. Builds and deploys run from a
**Cloud Build trigger** on pushes to `main`.

> This guide replaces the v1 flow (`gcr.io`, secrets as plain env vars, manual deploys).
> The reasons for each change are in the "Design decisions" table in the [README](README.md).

## Prerequisites

- A GCP project with billing enabled, and the `gcloud` CLI installed and authenticated
- The repo connected to Cloud Build (one-time, done in the console in Step 6)

## Step 1: Set variables and enable APIs

```bash
export PROJECT_ID=your-project-id
export REGION=us-central1
gcloud config set project $PROJECT_ID

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  sqladmin.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com
```

## Step 2: Create the Artifact Registry repository

```bash
gcloud artifacts repositories create social-api \
  --repository-format=docker \
  --location=$REGION \
  --description="social-media-api container images"
```

Images live at `$REGION-docker.pkg.dev/$PROJECT_ID/social-api/api:<git-sha>`.
Tagging by commit SHA (not `latest`) means every deploy is traceable and rollbacks are exact.

## Step 3: Create the Cloud SQL instance (PostgreSQL)

```bash
# Read the password without echoing it or saving it in shell history
read -s -p "DB password: " DB_PASS; echo

gcloud sql instances create social-db \
  --database-version=POSTGRES_15 \
  --edition=ENTERPRISE \
  --tier=db-f1-micro \
  --region=$REGION

gcloud sql users set-password postgres --instance=social-db --password="$DB_PASS"
gcloud sql databases create socialdb --instance=social-db

CONN=$(gcloud sql instances describe social-db --format='value(connectionName)')
echo $CONN
```

> **Cost:** Cloud SQL is **not** part of the Always Free tier (see "Cost notes" below).
> The instance bills while it exists, even when idle.

> **Known limitation:** the app connects as the `postgres` superuser. A dedicated
> least-privilege user is on the v3 list. On PostgreSQL 15 that needs explicit schema
> grants, which is why it isn't in this pass.

## Step 4: Store secrets in Secret Manager

```bash
# Stable JWT signing key (tr strips the trailing newline)
openssl rand -hex 32 | tr -d '\n' | gcloud secrets create social-api-secret-key --data-file=-

# Full database URL. URL-encode any special characters in the password.
printf '%s' "postgresql://postgres:${DB_PASS}@/socialdb?host=/cloudsql/${CONN}" \
  | gcloud secrets create social-api-database-url --data-file=-

unset DB_PASS
```

Non-secret settings (`ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`) stay as plain env vars in
`cloudbuild.yaml`.

**Why a stable key matters:** in v1 the deploy command ran `SECRET_KEY="$(openssl rand -hex 32)"`,
so every manual deploy generated a new signing key and invalidated every issued JWT.

## Step 5: Create service accounts and grant least-privilege access

**Runtime identity** (what the running service uses):

```bash
gcloud iam service-accounts create social-api-runtime
RUNTIME_SA=social-api-runtime@$PROJECT_ID.iam.gserviceaccount.com

for s in social-api-secret-key social-api-database-url; do
  gcloud secrets add-iam-policy-binding $s \
    --member=serviceAccount:$RUNTIME_SA --role=roles/secretmanager.secretAccessor
done

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$RUNTIME_SA --role=roles/cloudsql.client
```

**Build identity** (what Cloud Build uses to build and deploy):

```bash
gcloud iam service-accounts create social-api-build
BUILD_SA=social-api-build@$PROJECT_ID.iam.gserviceaccount.com

for role in roles/artifactregistry.writer roles/run.admin roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member=serviceAccount:$BUILD_SA --role=$role
done

# Allow the build identity to deploy a service that runs as the runtime identity
gcloud iam service-accounts add-iam-policy-binding $RUNTIME_SA \
  --member=serviceAccount:$BUILD_SA --role=roles/iam.serviceAccountUser
```

> `roles/run.admin` is broader than ideal, but `--allow-unauthenticated` needs permission to
> set the service's IAM policy, which `roles/run.developer` doesn't include. If a build step
> fails with a permissions error, the error message names the missing permission.




## Step 6: Create the Cloud Build trigger (Option A, recommended)

In the console: **Cloud Build → Triggers**

1. Connect the GitHub repository (one-time OAuth step).
2. Create a trigger:
   - Event: push to branch `^main$`
   - Configuration: `cloudbuild.yaml` in the repository
   - Service account: `social-api-build@YOUR_PROJECT_ID.iam.gserviceaccount.com`
3. Push to `main` (or run the trigger manually) and watch **Cloud Build → History**.

> If this service already exists from v1 with plain `SECRET_KEY` / `DATABASE_URL` env vars and the
> deploy complains about a name conflict, remove them once, then re-run:
> `gcloud run services update social-api --region $REGION --remove-env-vars=SECRET_KEY,DATABASE_URL`

## Step 6 (Option B): Manual bootstrap deploy

Use this to deploy once without a trigger.

```bash
IMAGE=$REGION-docker.pkg.dev/$PROJECT_ID/social-api/api:manual-1
gcloud builds submit --tag $IMAGE

gcloud run deploy social-api \
  --image $IMAGE \
  --region $REGION \
  --allow-unauthenticated \
  --service-account=$RUNTIME_SA \
  --add-cloudsql-instances=$CONN \
  --set-secrets=SECRET_KEY=social-api-secret-key:latest,DATABASE_URL=social-api-database-url:latest \
  --set-env-vars=ALGORITHM=HS256,ACCESS_TOKEN_EXPIRE_MINUTES=30 \
  --memory=512Mi --cpu=1 --min-instances=0 --max-instances=1
```

## Step 7: Verify

```bash
URL=$(gcloud run services describe social-api --region $REGION --format='value(status.url)')
curl $URL/health
```

Then run the smoke test (`test_api.sh`) against `$URL`. Check the top of the script for how it
takes the base URL.

## Operations

**View logs**

```bash
gcloud run services logs read social-api --region $REGION
```

**Roll back** (images are tagged by commit SHA, so revisions are traceable):

```bash
gcloud run revisions list --service social-api --region $REGION
gcloud run services update-traffic social-api --region $REGION --to-revisions=REVISION_NAME=100
```

**Rotate a secret**

```bash
openssl rand -hex 32 | tr -d '\n' | gcloud secrets versions add social-api-secret-key --data-file=-
gcloud run services update social-api --region $REGION   # new revision picks up :latest
```

Rotating `SECRET_KEY` invalidates all issued tokens. That is expected behavior.

## Cost notes

Prices and free tiers change. Confirm on the official pricing pages before relying on any of this.

| Service | Free allowance (as last checked) | What to watch |
|---|---|---|
| Cloud Run | 2M requests/month, plus vCPU-second and GiB-second allowances (Always Free) | `--min-instances=0` means no idle charge |
| Cloud SQL | **None in Always Free.** New projects can get a short free trial instance (preset configuration); the instance this guide creates is paid | Starts at roughly $10/month for the smallest shared-core instance, depending on region and config. Bills while idle |
| Cloud Build | 2,500 free build-minutes per month per billing account (default `e2-standard-2` pool) | Builds for this repo are a few minutes each |
| Artifact Registry | Small free storage allotment | Old images accumulate; set a cleanup policy |
| Secret Manager | Small free tier | Negligible at this scale |

To stop paying for the database between demos:

```bash
gcloud sql instances patch social-db --activation-policy=NEVER   # stop (storage still billed)
gcloud sql instances patch social-db --activation-policy=ALWAYS  # start again
```

## Teardown

```bash
gcloud run services delete social-api --region $REGION
gcloud sql instances delete social-db
gcloud secrets delete social-api-secret-key
gcloud secrets delete social-api-database-url
gcloud artifacts repositories delete social-api --location=$REGION
```

## Alternative: Docker Compose on a Compute Engine VM

Worth considering if the app needs persistent local disk (for example, for uploaded images). The
trade-off is that you now own patching, TLS, restarts and backups.

```bash
# The Always Free VM is e2-micro, in us-west1, us-central1 or us-east1 only
gcloud compute instances create social-api-vm \
  --machine-type=e2-micro \
  --zone=us-central1-a \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=30GB \
  --boot-disk-type=pd-standard

gcloud compute ssh social-api-vm --zone=us-central1-a

sudo apt update && sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER
# clone the repo, then:
docker-compose up -d
```

An `e2-micro` has 1 GB of RAM, which is tight for the API and PostgreSQL together.
