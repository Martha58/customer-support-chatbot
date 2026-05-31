from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from loguru import logger
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL=os.getenv("DB_URI")
try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    logger.info("Database connection successful")
except Exception as e:
    logger.error(f"Error connecting to the Database: {e}")