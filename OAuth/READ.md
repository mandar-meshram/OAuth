
# Auth Service (Boffins Botvana Project)

This microservice handles **user signup and login** operations with a database 
and password hashing. It is built using **FastAPI + SQLite + Docker**.



## Features Implemented

-  `POST /signup` - Register new users
-  `POST /login` - Authenticate existing users
-  Password hashing (secure, irreversible)
-  SQLite database integration
-  Docker container setup with `Dockerfile`
-  Health check route for Docker: `GET /health`
-  Custom info route: `GET /info`
-  Middleware to log every request and response
-  Docker Compose integration



##  Concepts We Learned

### 1. **FastAPI Basics**
- How to define routes using `@app.post()` and `@app.get()`
- Use of Pydantic models for request validation

### 2. **Database Integration**
- Using `SQLAlchemy` for models
- Creating tables with `Base.metadata.create_all(bind=engine)`
- Dependency injection with `Depends(get_db)`

### 3. **Password Security**
- Hashing passwords using `passlib`
- Storing only hashes, not plain text

### 4. **Dockerization**
- Writing a Dockerfile for FastAPI
- Exposing ports and using volumes
- Running with `docker-compose`

### 5. **Logging & Monitoring**
- Built a logging middleware to show request/response info in terminal
- Added `/info` route to return service name, version, and uptime

### 6. JWT Authentication
- Implemented JWT-based token generation using jose.jwt.encode
- Added /login route to issue JWT tokens upon successful authentication
- Secured /protected route using Depends(oauth2_scheme) and token verification
- Configured OAuth2PasswordBearer with tokenUrl="/login" for Swagger integration
- Used OAuth2PasswordRequestForm for login to support Swagger UI authentication
- Tested token flow via Swagger UI and curl with Authorization: Bearer <token>
- Understood and handled 401 Unauthorized errors when token is missing or invalid

### 7. Role-Based Access Control (RBAC) – Admin/User
What We Implemented
Today, we extended our authentication system by adding roles (admin, user) to users and 
controlling access to routes based on those roles.
    Skill	                            Description
 
- Role-Aware Tokens	            JWT token now includes both username and role. 
- Protect Routes	    Students can restrict sensitive routes to certain roles (e.g., /admin only admins).
- Role Validation	Students can write logic to check if user["role"] == "admin" and raise 403 otherwise.
- Reusable Auth	Use get_current_user() dependency to get username and role from token in any route.

### 8. Redis-Based Rate Limiting + Middleware Logging
What We Implemented
Introduced a Redis-based rate limiter for /login and /signup routes.

Added a combined middleware that handles both:

Request logging (method, URL, status).

Rate limiting with IP tracking using Redis.

| Tool/Library         | Purpose                         |
| -------------------- | ------------------------------- |
| `redis-py`           | Redis client in Python          |
| `FastAPI middleware` | Custom request/response control |
| `logging`            | Info + error logs to console    |
| `HTTPException`      | Return structured errors        |





##  Key Endpoints(Routes)

 Method     URL              Description          
------------------------------------------------
 POST    `/signup`         Register a new user  
 POST    `/login`          Login and receive JWT token
 GET     `/health`         Docker healthcheck   
 GET     `/info`           Returns uptime + version 
 GET     `/protected`   Access with valid Bearer token|
 GET     `/cart`   Access with valid token for user and admin


##  Docker Compose Configuration

Service is included in `docker-compose.yml` with:
- Health check setup
- Port mapping (`8000:8000`)
- Live code reload using volume



##  Folder Structure

auth_service/
│
├── main.py                  # FastAPI app with routes
├── models.py                # SQLAlchemy user model
├── database.py              # DB connection and Base config
├── auth_utils.py            # Password hashing and verification
├── jwt_utils.py             # JWT token creation and verification
├── Dockerfile               # Container instructions
├── requirements.txt         # Python dependencies
├── docker-compose.yml       # Docker Compose setup
└── README.md                # Project documentation

