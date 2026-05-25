#!/usr/bin/env bash
# Standard deploy: build and restart. Migrations run automatically inside the
# container before uvicorn starts (see Dockerfile CMD). Data persists in the
# DB volume across deploys. To reset and reseed, run remote-seed.sh separately.
set -euo pipefail

APP_ROOT="/srv/apps/geoapi/repo"
DEPLOY_DIR="$APP_ROOT/deploy/vps"

if [ ! -f "$DEPLOY_DIR/.env.production" ]; then
  echo "Missing $DEPLOY_DIR/.env.production" >&2
  exit 1
fi

cd "$DEPLOY_DIR"
docker compose --env-file .env.production up -d --build

echo "Deploy triggered. Migrations run on container startup."
echo "Monitor with: docker logs -f geoapi-test-api"
