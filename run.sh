#!/bin/bash

NAME=MarketMonitoring
LOG_LEVEL=info
export $(grep -v '^#' .env | xargs)

mkdir .tmp || true
mkdir logs || true

echo "running market monitoring...."
echo $NAME
exec python main.py
