#!/bin/bash

# Load environment variables
source .env

# Build and push Docker image
docker build -t localhost:5000/my-app:latest .
docker push localhost:5000/my-app:latest
