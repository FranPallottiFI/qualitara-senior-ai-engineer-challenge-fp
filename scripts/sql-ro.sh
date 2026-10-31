#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ne 1 ]; then
  echo "usage: $0 \"<SQL>\"" >&2
  exit 2
fi
# psql -c runs a single backslash meta-command, e.g. \! (shell inside the container, where local
# connections are trusted, i.e. superuser) or \c (reconnect as another role). Block them all.
case "$1" in
  *\\*)
    echo "error: backslash not allowed; psql meta-commands (\\!, \\c, ...) are blocked" >&2
    exit 2
    ;;
esac
exec docker compose exec -T db \
  psql -v ON_ERROR_STOP=1 -X -U app_readonly -d "${POSTGRES_DB:-app}" -c "$1"