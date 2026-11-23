#!/usr/bin/env bash
set -euo pipefail

base_url=$1
health=$(curl --fail --silent --show-error --max-time 10 "$base_url/health")
if [[ "$health" != '{"status":"ok"}' ]]; then
    echo 'Unexpected response from the API health endpoint.' >&2
    exit 1
fi

homepage=$(curl --fail --silent --show-error --max-time 10 "$base_url/")
search_page=$(curl --fail --silent --show-error --max-time 10 "$base_url/search")
bundle_pattern='src="(/assets/[^"]+\.js)"'
if [[ "$homepage" != *'<div id="root"></div>'* || "$search_page" != "$homepage" ||
      ! "$homepage" =~ $bundle_pattern ]]; then
    echo 'The React homepage, search route, or JavaScript entry point is missing.' >&2
    exit 1
fi

curl --fail --silent --show-error --max-time 10 --output /dev/null "$base_url${BASH_REMATCH[1]}"
echo 'API and frontend checks passed.'
