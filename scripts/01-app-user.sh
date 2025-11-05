#!/bin/bash
set -e

echo "Creating application database and user…"
mongosh --username "$MONGO_INITDB_ROOT_USERNAME" --password "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin <<'EOF'
const dbName = process.env.APP_DB_NAME || "appdb";
const user   = process.env.APP_DB_USER || "appuser";
const pass   = process.env.APP_DB_PASS || "apppass";

db.getSiblingDB(dbName).createUser({
  user: user,
  pwd:  pass,
  roles: [{ role: "readWrite", db: dbName }]
});
print(`Created user ${user} on db ${dbName}`);
EOF