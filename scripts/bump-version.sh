#!/usr/bin/env bash
# Bump patch version in __init__.py and pyproject.toml, then commit.
# Usage: ./scripts/bump-version.sh
# Can be used as a pre-commit hook or called manually.
set -euo pipefail

INIT_FILE="src/brew_hop_search/__init__.py"
PYPROJECT="pyproject.toml"

# Extract current version
current=$(grep -oP '(?<=__version__ = ")[^"]+' "$INIT_FILE")
if [ -z "$current" ]; then
    echo "Could not find __version__ in $INIT_FILE" >&2
    exit 1
fi

# Bump patch
IFS='.' read -r major minor patch <<< "$current"
new_patch=$((patch + 1))
new_version="$major.$minor.$new_patch"

# Update files
sed -i '' "s/__version__ = \"$current\"/__version__ = \"$new_version\"/" "$INIT_FILE"
sed -i '' "s/^version = \"$current\"/version = \"$new_version\"/" "$PYPROJECT"

echo "$current → $new_version"
