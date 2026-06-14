import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Uses EKS cluster internal DNS naming scheme to reach the postgres pod securely
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://apnea_admin:apnea_secure_pass@postgres-service:5432/apnea_db"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency injector pattern to handle safe connection cleanup
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()