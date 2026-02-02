#!/usr/bin/env bash
# One-time setup: prompt for Gemini API key and write to .env (key is not echoed).
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"

echo "Gemini API key is used for AI summarization on the Code Analysis page."
echo "Get a key at: https://aistudio.google.com/apikey"
echo ""
read -rs -p "Enter Gemini API key (input hidden): " key
echo ""

if [ -z "$key" ]; then
  echo "No key entered. .env was not changed."
  exit 0
fi

# Write GEMINI_API_KEY only; do not overwrite other vars if .env exists
if [ -f "$ENV_FILE" ]; then
  if grep -q '^GEMINI_API_KEY=' "$ENV_FILE" 2>/dev/null; then
    sed -i.bak "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY=$key|" "$ENV_FILE" && rm -f "${ENV_FILE}.bak"
  else
    echo "GEMINI_API_KEY=$key" >> "$ENV_FILE"
  fi
else
  printf '%s\n' "# Gemini API key for AI summarization (Code Analysis)" "GEMINI_API_KEY=$key" > "$ENV_FILE"
fi

echo "Written to $ENV_FILE. Restart the backend (e.g. npm start) for changes to take effect."
