#!/bin/sh
set -euo pipefail

admin_pw=$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(16))
PY
)

user_pw=$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(16))
PY
)

# create admin
if python3 scripts/create_user.py admin "$admin_pw" admin; then
  echo "ADMIN_PASSWORD:$admin_pw"
else
  echo "ADMIN_EXISTS_OR_ERROR"
fi

# create normal user
if python3 scripts/create_user.py user "$user_pw" user; then
  echo "USER_PASSWORD:$user_pw"
else
  echo "USER_EXISTS_OR_ERROR"
fi
