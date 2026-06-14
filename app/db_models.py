import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="Anonymous Patient")
    age = Column(Integer, default=52)
    bmi = Column(Float, default=29.4)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    sessions = relationship("DiagnosticSession", back_populates="patient")

class DiagnosticSession(Base):
    __tablename__ = "diagnostic_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    filename = Column(String)
    total_windows = Column(Integer)
    apnea_windows = Column(Integer)
    osa_windows = Column(Integer)
    ca_windows = Column(Integer)
    normal_windows = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    patient = relationship("Patient", back_populates="sessions")