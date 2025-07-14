# Import Passlib's password hashing tool
from passlib.context import CryptContext

# Define the hashing algorithm to use ('bcrypt' is secure)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash the password using bcrypt (for storing in DB)
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Verify a password by comparing user input with hashed version in DBWH
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
