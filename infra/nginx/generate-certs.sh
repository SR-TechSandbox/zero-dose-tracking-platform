#!/bin/sh
set -e

CERT_DIR="$(dirname "$0")/certs"
mkdir -p "$CERT_DIR"

if [ -f "$CERT_DIR/localhost.crt" ] && [ -f "$CERT_DIR/localhost.key" ]; then
  echo "TLS certificates already exist in $CERT_DIR"
  exit 0
fi

echo "Generating self-signed TLS certificate for localhost..."
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "$CERT_DIR/localhost.key" \
  -out "$CERT_DIR/localhost.crt" \
  -subj "/C=IN/ST=Karnataka/L=Bengaluru/O=ZeroDosePlatform/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

echo "Done: $CERT_DIR/localhost.crt & localhost.key"