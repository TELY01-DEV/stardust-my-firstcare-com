#!/bin/bash

# Exit on error
set -e

# Variables
SSH_KEY="$HOME/.ssh/id_ed25519"
SSH_PORT=2222
SERVER_USER="root"
SERVER_IP="103.13.30.89"
SERVER_PATH="/www/dk_project/dk_app/stardust-my-firstcare-com"
LOCAL_FILE="app/routes/admin.py"
REMOTE_FILE="$SERVER_PATH/app/routes/admin.py"

# 1. Commit and push the change

echo "Committing and pushing changes..."
git add $LOCAL_FILE
git commit -m "fix: support page parameter for patient list pagination"
git push

echo "Copying updated file to production server..."
scp -i $SSH_KEY -P $SSH_PORT $LOCAL_FILE $SERVER_USER@$SERVER_IP:$REMOTE_FILE

echo "Rebuilding and restarting Docker on production server..."
ssh -i $SSH_KEY -p $SSH_PORT $SERVER_USER@$SERVER_IP << EOF
  cd $SERVER_PATH
  docker compose build
  docker compose up -d
EOF

echo "Deployment complete!" 