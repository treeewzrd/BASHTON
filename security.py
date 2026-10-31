# Import PasswordHash to configure password hashing.
from pwdlib import PasswordHash

# Create a reusable password hasher using recommended settings (Argon2id).
password_hash = PasswordHash.recommended()


# Accept a plaintext password and return its securely salted hash.
def hash_password(password: str):
    return password_hash.hash(password)


# Compare a plaintext password against a stored hash.
# Returns True if they match, False otherwise.
def verify_password(plain_password: str, hashed_password: str):
    return password_hash.verify(plain_password, hashed_password)