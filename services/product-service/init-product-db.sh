#!/bin/sh
set -eu

# Local bootstrap only. Leave auth_db and existing tables/data untouched.
case "$MYSQL_USER" in
  ""|*[!a-zA-Z0-9_]*)
    printf 'MYSQL_USER may only contain letters, numbers and underscores\n' >&2
    exit 1
    ;;
esac
MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql --protocol=TCP -h mysql -u root <<SQL
CREATE DATABASE IF NOT EXISTS product_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX ON product_db.* TO '$MYSQL_USER'@'%';
SQL
