#!/bin/bash

# Script para build com timestamp único (quebra cache automaticamente)
BUILD_DATE=$(date -u +"%Y%m%d_%H%M%S")
echo "Building with timestamp: $BUILD_DATE"

docker build --build-arg BUILD_DATE=$BUILD_DATE -t video-transcription-api:$BUILD_DATE .
docker tag video-transcription-api:$BUILD_DATE video-transcription-api:latest

echo "Build completed with cache-busting timestamp: $BUILD_DATE" 