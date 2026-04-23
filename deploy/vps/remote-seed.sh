#!/usr/bin/env bash
# One-shot seed: copies the dataset JSON into the running container and loads it.
# Run this only on first deploy or when a full data reset is needed.
# WARNING: this truncates interventions, areas, and reference_places before inserting.
set -euo pipefail

APP_ROOT="/srv/apps/toroto-challenge/repo"

echo "Copying dataset into container..."
docker cp "$APP_ROOT/data/geospatial_interventions_dataset.json" \
  toroto-test-api:/app/data/geospatial_interventions_dataset.json

echo "Seeding database..."
docker exec toroto-test-api python -m scripts.load_dataset

echo "Seed complete."
