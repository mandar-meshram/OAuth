from fastapi import FastAPI, HTTPException, Depends, Request, Form
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
import time
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from typing import List


from database import SessionLocal, engine, Base
from models import User
from auth_utils import hash_password, verify_password
from jwt_utils import create_jwt_token, verify_jwt_token, get_current_user

from fastapi.security import OAuth2PasswordBearer

# For google login
from starlette.middleware.sessions import SessionMiddleware
from oauth import router as oauth_router
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# This line creates the tables in the DB if they don’t exist yet
Base.metadata.create_all(bind=engine)
templates = Jinja2Templates(directory="templates")
# Create a FastAPI application
app = FastAPI()

# IMPORTANT: Add SessionMiddleware BEFORE other middleware and routes
# Use as strong, consistent secret key
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key-change-this")
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    max_age=86400,
    same_site="lax",
    https_only=False,   # set to True in production with HTTPS
)

# Redis middleware
from middlewares import combined_logger_and_limiter
app.middleware("http")(combined_logger_and_limiter)

# Include OAuth routes
app.include_router(oauth_router)

# Define what data we expect when someone signs up or logs in
class UserIn(BaseModel):
    username: str
    password: str
    role: str = "user"    # default to user

# Dependency function that creates a new DB session for each request
def get_db():
    db = SessionLocal()  # Open a new DB session
    try:
        yield db          # Provide the session to the route
    finally:
        db.close()        # Close the session after the request is done

# Route to sign up a new user
@app.post("/signup/")
def signup(user: UserIn, db: Session = Depends(get_db)):
    # Check if username is already taken
    existing = db.query(User).filter(User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    # If username is new, create a new user and hash the password
    new_user = User(username=user.username, hashed_password=hash_password(user.password), role=user.role)
    db.add(new_user)     # Add new user to session
    db.commit()          # Save to database
    return {"message": "User created"}

# Route to login an existing user
@app.post("/login")
def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    # Find the user in the DB
    existing = db.query(User).filter(User.username == username).first()

    # Check if user exists and password is correct
    if not existing or not verify_password(password, existing.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_jwt_token(existing.username, existing.role)

    response = JSONResponse(content={"access_token": token, "token_type": "bearer"})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,   # Prevent JavaScript access (more secure)
        max_age=1800,    # 30 minutes
        path="/",        # Valid for all routes
        secure=True,  # Set to True in production with HTTPSTrue
    )
    return response

# Protected route: requires token to access
@app.get("/protected")
def protected(token: str = Depends(oauth2_scheme)):
    username = verify_jwt_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"message": f"Hello, {username}. You are authenticated."}
##Test Protected path
#curl.exe -X GET 'http://127.0.0.1:8000/protected' \  -H "accept: application/json" \  -H "Authorization: Bearer <enter token>"


@app.get("/users", response_model=List[UserIn])
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

@app.get("/health")
def health_check():
    return {"status": "ok"}

# Track service uptime
start_time = time.time()

@app.get("/info")
def info():
    uptime = round(time.time() - start_time, 2)
    return {
        "service": "auth_service",
        "version": "1.0.0",
        "uptime_in_seconds": uptime
    }


from jwt_utils import get_current_user
@app.get("/cart")
def cart(username : str = Depends(get_current_user)):
    return {"cart_items" : ["pen", "Notebook"], "user" : username}

@app.get("/admin", response_class=HTMLResponse)
def admin_panel(request: Request, user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        return {"error" : "Access Denied"}
    return templates.TemplateResponse('admin.html', {"request": request, "user": user})


@app.post("/logout")
def logout():
    response = JSONResponse(content={"message": "Logged out"})
    response.delete_cookie("access_token")
    return response

# HTML routes for OAuth
@app.get("/", response_class=HTMLResponse)
def show_login_page(request : Request):
    return templates.TemplateResponse("login.html",{'request':request})

@app.get("/welcome", response_class=HTMLResponse)
def welcome(request: Request, username: str ):
    token = request.cookies.get("access_token")

    if not token:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Please login first."})
    
    return templates.TemplateResponse("welcome.html", {"request": request, "username": username})