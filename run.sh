#!/bin/bash

NAME=MarketMonitoring
WORKERS=1
WORKER_CLASS=uvicorn.workers.UvicornWorker
LOG_LEVEL=info
BIND=0.0.0.0:1844
ERROR_LOG=.gunicorn.log
ACCESS_LOG=.gunicorn-access.log
export $(grep -v '^#' .env | xargs)

mkdir .tmp || true
touch $ERROR_LOG
touch $ACCESS_LOG

echo "running server"
echo $NAME
echo $WORKERS
echo $WORKER_CLASS
echo $ERROR_LOG
echo $ACCESS_LOG
echo $BIND
exec gunicorn main:app \
  --keep-alive 30 \
  --name $NAME \
  --workers $WORKERS \
  --worker-class $WORKER_CLASS \
  --bind $BIND \
  --log-level=$LOG_LEVEL \
  --error-logfile=$ERROR_LOG \
  --access-logfile=$ACCESS_LOG
