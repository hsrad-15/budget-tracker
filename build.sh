#!/usr/bin/env bash
# Render build script. Set as the Build Command in the Render dashboard,
# or referenced automatically via render.yaml.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
