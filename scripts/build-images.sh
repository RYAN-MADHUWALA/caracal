#!/bin/bash
# Build Docker images with version from VERSION file

set -e

# Get the root directory of the project
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION_FILE="$ROOT_DIR/VERSION"

# Check if VERSION file exists
if [ ! -f "$VERSION_FILE" ]; then
    echo "ERROR: VERSION file not found at $VERSION_FILE"
    exit 1
fi

# Read version from VERSION file
VERSION=$(cat "$VERSION_FILE" | tr -d '[:space:]')

echo "Building Docker images for version: $VERSION"

DOCKER_DIR="$ROOT_DIR/deploy/docker"

echo "Building caracal-mcp-adapter:v$VERSION..."
docker build -t caracal-mcp-adapter:v$VERSION -f "$DOCKER_DIR/Dockerfile.mcp" "$ROOT_DIR"

echo "Building caracal-cli:v$VERSION..."
docker build -t caracal-cli:v$VERSION -f "$DOCKER_DIR/Dockerfile.cli" "$ROOT_DIR"

echo "Building caracal-flow:v$VERSION..."
docker build -t caracal-flow:v$VERSION -f "$DOCKER_DIR/Dockerfile.flow" "$ROOT_DIR"

echo ""
echo "Docker images built successfully!"
echo "Images:"
echo "  - caracal-mcp-adapter:v$VERSION"
echo "  - caracal-cli:v$VERSION"
echo "  - caracal-flow:v$VERSION"
