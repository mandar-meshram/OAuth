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


from starlette.middleware.sessions import SessionMiddleware
from oauth import router as oauth_router
from dotenv import load_dotenv
import os


load_dotenv()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


Base.metadata.create_all(bind=engine)
templates = Jinja2Templates(directory="templates")

app = FastAPI()


SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key-change-this")
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    max_age=86400,
    same_site="lax",
    https_only=False,   
)


from middlewares import combined_logger_and_limiter
app.middleware("http")(combined_logger_and_limiter)


app.include_router(oauth_router)


class UserIn(BaseModel):
    username: str
    password: str
    role: str = "user"   


def get_db():
    db = SessionLocal()  
    try:
        yield db          
    finally:
        db.close()        


@app.post("/signup/")
def signup(user: UserIn, db: Session = Depends(get_db)):
    
    existing = db.query(User).filter(User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

   
    new_user = User(username=user.username, hashed_password=hash_password(user.password), role=user.role)
    db.add(new_user)     
    db.commit()         
    return {"message": "User created"}


@app.post("/login")
def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
   
    existing = db.query(User).filter(User.username == username).first()

    
    if not existing or not verify_password(password, existing.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_jwt_token(existing.username, existing.role)

    response = JSONResponse(content={"access_token": token, "token_type": "bearer"})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,   
        max_age=1800,    
        path="/",        
        secure=True,  
    )
    return response


@app.get("/protected")
def protected(token: str = Depends(oauth2_scheme)):
    username = verify_jwt_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"message": f"Hello, {username}. You are authenticated."}



@app.get("/users", response_model=List[UserIn])
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

@app.get("/health")
def health_check():
    return {"status": "ok"}


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