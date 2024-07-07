#!/bin/bash

# Load environment variables
source .env

# Initialize and apply Terraform configuration
terraform init
terraform apply -auto-approve
