#!/usr/bin/env bash
set -euo pipefail

release=$1
root=$(dirname "$(dirname "$release")")
export DOCKER_HOST="unix:///run/user/$(id -u)/docker.sock"

compose() {
    local version_dir=$1
    shift
    APP_IMAGE_TAG="$(basename "$version_dir")" docker compose \
        --project-name yandex-travel --env-file "$root/.env.vps" \
        -f "$version_dir/docker-compose.yml" -f "$version_dir/deploy/compose.vps.yml" "$@"
}

previous=$(readlink -e "$root/current" || true)
compose "$release" config --quiet
compose "$release" pull --policy missing nginx
compose "$release" build app
ln -s "$release" "$release/next-current"

if compose "$release" up -d --no-build --wait --wait-timeout 150 &&
    health=$(curl --fail --silent --show-error --max-time 10 http://127.0.0.1/health) &&
    [[ "$health" == '{"status":"ok"}' ]] &&
    mv -Tf "$release/next-current" "$root/current"; then
    echo "Deployed $(basename "$release")"
    exit 0
fi

echo 'Deployment failed. Check service logs on the VPS.' >&2
compose "$release" ps --all || true
if [[ -n "$previous" ]]; then
    echo "Restoring $(basename "$previous")" >&2
    if ! compose "$previous" up -d --no-build --remove-orphans --wait --wait-timeout 150; then
        echo 'Previous release failed to become healthy.' >&2
    fi
else
    compose "$release" stop nginx app || true
fi
exit 1
