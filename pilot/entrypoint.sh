#!/bin/sh
set -e

# Strip embedded credentials from git remote URLs in the workspace.
# The GIT_CONFIG_KEY_0 env var sets up URL rewriting for https://github.com/
# to inject GITHUB_TOKEN, but only if the remote URL doesn't already have
# credentials embedded (e.g. https://user:pass@github.com/...).
# This script normalizes remote URLs so GIT_CONFIG auth always applies.
if [ -d /workspace/.git ]; then
    current_url=$(git -C /workspace remote get-url origin 2>/dev/null || true)
    if [ -n "$current_url" ]; then
        clean_url=$(echo "$current_url" | sed 's|https://[^@]*@|https://|')
        if [ "$clean_url" != "$current_url" ]; then
            echo "[entrypoint] Removing embedded credentials from git remote URL"
            git -C /workspace remote set-url origin "$clean_url"
        fi
    fi
fi

exec pilot start
