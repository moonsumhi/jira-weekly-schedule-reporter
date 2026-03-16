#!/bin/bash
set -euo pipefail

DB_NAME="${APP_DB_NAME}"
DB_USER="${APP_DB_USER}"
DB_PASS="${APP_DB_PASS}"

# bcrypt hash of "12345"
ADMIN_EMAIL="admin@ncc.re.kr"
ADMIN_HASH='$2b$12$EnLZOoqr0.lT0ZPqpJMQqOktSLxBrGL2lyJ81GmWHKBX58k2mtXQq'

mongosh \
  -u "$MONGO_INITDB_ROOT_USERNAME" \
  -p "$MONGO_INITDB_ROOT_PASSWORD" \
  --authenticationDatabase admin <<EOF
const db = db.getSiblingDB("${DB_NAME}");
const email = "${ADMIN_EMAIL}";
const existing = db.users.findOne({ email });
if (existing) {
  print("Admin user already exists, skipping.");
} else {
  db.users.insertOne({
    email: email,
    full_name: "관리자",
    hashed_password: "${ADMIN_HASH}",
    is_admin: true,
  });
  print("Admin user created: " + email);
}
EOF
