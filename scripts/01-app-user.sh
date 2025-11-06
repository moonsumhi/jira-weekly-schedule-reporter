#!/bin/bash
set -e

echo "Creating application database and user…"

# Read env with sane defaults
DB_NAME="${APP_DB_NAME}"
DB_USER="${APP_DB_USER}"
DB_PASS="${APP_DB_PASS}"

mongosh --username "$MONGO_INITDB_ROOT_USERNAME" --password "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin <<'EOF'
const dbName = "$DB_NAME";
const user   = "$DB_USER";
const pass   = "$DB_PASS";

db.getSiblingDB(dbName).createUser({
  user: user,
  pwd:  pass,
  roles: [{ role: "readWrite", db: dbName }]
});
print(`Created user ${user} on db ${dbName}`);
EOF