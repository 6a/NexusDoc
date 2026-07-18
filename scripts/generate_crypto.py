"""
Generate cryptographically secure random values for the specified environment variables.
"""

import secrets

print("NEXTAUTH_SECRET=" + secrets.token_hex(32))
print("SALT=" + secrets.token_hex(16))
print("ENCRYPTION_KEY=" + secrets.token_hex(32))
print("POSTGRES_PASSWORD=" + secrets.token_hex(16))
print("CLICKHOUSE_PASSWORD=" + secrets.token_hex(16))
print("REDIS_AUTH=" + secrets.token_hex(16))
print("MINIO_ROOT_PASSWORD=" + secrets.token_hex(16))
