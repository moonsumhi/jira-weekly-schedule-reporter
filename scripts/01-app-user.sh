#!/bin/bash
set -euo pipefail

DB_NAME="${APP_DB_NAME:-appdb}"
DB_USER="${APP_DB_USER:-appuser}"
DB_PASS="${APP_DB_PASS:-apppass}"

mongosh \
  -u "$MONGO_INITDB_ROOT_USERNAME" \
  -p "$MONGO_INITDB_ROOT_PASSWORD" \
  --authenticationDatabase admin <<EOF
const dbName = "$DB_NAME";
const user   = "$DB_USER";
const pass   = "$DB_PASS";

const target = db.getSiblingDB(dbName);
const existing = target.getUser(user);
if (existing) {
  print(\`User "\${user}" exists → updating\`);
  target.updateUser(user, { pwd: pass, roles: [{ role: "readWrite", db: dbName }] });
} else {
  print(\`Creating user "\${user}" in "\${dbName}"\`);
  target.createUser({ user, pwd: pass, roles: [{ role: "readWrite", db: dbName }] });
}
EOF
