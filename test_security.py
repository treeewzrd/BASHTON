# Import the password functions we want to test.
from security import hash_password, verify_password


def test_hash_password():
    # Simulate a user providing a plaintext password.
    password = "test_password_123"

    # Generate a salted password hash.
    hashed = hash_password(password)

    # Confirm the hash is different from the plaintext password.
    assert hashed != password


def test_verify_password():
    # Simulate a user providing a password.
    password = "test_password_123"

    # Generate a hash to simulate what is stored in the database.
    hashed = hash_password(password)

    # Correct password is accepted.
    assert verify_password(password, hashed) is True

    # Incorrect password is rejected.
    assert verify_password("wrong_password", hashed) is False

# test to see if identicle passwords prove hashes are different
def test_password_hashes_are_unique():
    password = "test_password_123"
    hash_one = hash_password(password)
    hash_two = hash_password(password)
    assert hash_one != hash_two