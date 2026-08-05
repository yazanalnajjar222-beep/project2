#!/bin/bash
# Variables
VAULT_ADDR='http://127.0.0.1:8200'  # Update with your Vault address
VAULT_TOKEN='hvs.MJoesifpnU5fAtosedMmhcIC'       # Update with your Vault token
SECRET_PATH='kv/project2'      # Update with your secret path
ENV_FILE='/home/aau/Desktop/project2/Expense_Tracker/.env'               # Name of the .env file
# Export Vault address and token
export VAULT_ADDR
export VAULT_TOKEN

# Retrieve secrets from Vault
echo "Retrieving secrets from Vault..."
SECRETS=$(vault kv get -format=json $SECRET_PATH)
# Check if retrieval was successful
if [ $? -ne 0 ]; then
  echo "Failed to retrieve secrets from Vault."
  exit 1
fi

# Extract data and save to .env file
echo "Saving secrets to $ENV_FILE..."
echo "$SECRETS" | jq -r '.data.data | to_entries[] | .key + "=" + .value' > $ENV_FILE

# Check if .env file was created successfully
if [ $? -ne 0 ]; then
  echo "Failed to save secrets to $ENV_FILE."
  exit 1
fi
# Run Docker with .env file
echo "Running Docker container..."
