from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi import Cookie

# Secret key for signing tokens
SECRET_KEY = "boffins-secret-key"  
ALGORITHM = "HS256"
EXPIRE_MINUTES = 30

# Tells FastAPI where to look for token (used in Swagger docs)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

# Create a JWT token for a given username
def create_jwt_token(username: str, role:str):
    expire = datetime.utcnow() + timedelta(minutes=EXPIRE_MINUTES)
    payload = {"sub": username,"role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# Verify token and return the username
def verify_jwt_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# Reusable FastAPI dependency to extract user from token
def get_current_user(token : str = Depends(oauth2_scheme),access_token: str = Cookie(default=None)) -> str:
    # Decode and validate the token
    token_to_use = token or access_token
    if not token_to_use:
        raise HTTPException(status_code=401, detail="Token missing")

    payload = verify_jwt_token(token_to_use)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return {
        "username": payload.get("sub"),
        "role": payload.get("role")
    }