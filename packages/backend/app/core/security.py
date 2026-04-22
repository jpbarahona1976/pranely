"""Password hashing using Argon2id (OWASP recommended)."""
from argon2 import PasswordHasher

ph = PasswordHasher(
    time_cost=3,      # Number of iterations
    memory_cost=65536, # 64 MB
    parallelism=4,    # Number of parallel threads
    hash_len=32,      # Length of the hash in bytes
    salt_len=16,      # Length of the random salt
)


def hash_password(password: str) -> str:
    """Hash a password using Argon2id."""
    return ph.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    try:
        return ph.verify(hashed, password)
    except Exception:
        return False