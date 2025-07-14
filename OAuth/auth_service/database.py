from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite database path
DATABASE_URL = "sqlite:///./users.db"

# Create connection to SQLite
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Session maker (used to talk to DB)
SessionLocal = sessionmaker(bind=engine, autoflush=False)

# Base class for defining models
Base = declarative_base()
