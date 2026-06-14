import io
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from sqlalchemy.orm import Session

from model import process_csv_and_predict
from database import engine, Base, get_db
import db_models

# Bootstrap database tables directly on container instantiation in EKS
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Apnea Detection & Monitoring API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/predict_csv")
async def predict_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")

    contents = await file.read()
    df = pd.read_csv(io.BytesIO(contents), header=None)
    df.columns = ["PFlow", "Thorax", "Abdomen", "SaO2", "Vitalog1", "Vitalog2", "time_sec"]

    try:
        # Run your core DPO PyTorch pipeline inference
        results = process_csv_and_predict(df)
        
        # 1. Ensure a default clinical testing patient profile exists
        patient = db.query(db_models.Patient).first()
        if not patient:
            patient = db_models.Patient(name="Default Testing Subject")
            db.add(patient)
            db.commit()
            db.refresh(patient)

        # 2. Extract metrics to commit to state management
        total_w = len(results)
        apnea_w = sum(1 for x in results if x.get("is_apnea", False))
        osa_w = sum(1 for x in results if x.get("predicted_class") == "OSA")
        ca_w = sum(1 for x in results if x.get("predicted_class") == "Central Apnea")
        normal_w = sum(1 for x in results if x.get("predicted_class") == "Normal")

        # 3. Store result to SQL database
        session_record = db_models.DiagnosticSession(
            patient_id=patient.id,
            filename=file.filename,
            total_windows=total_w,
            apnea_windows=apnea_w,
            osa_windows=osa_w,
            ca_windows=ca_w,
            normal_windows=normal_w
        )
        db.add(session_record)
        db.commit()

        return {"filename": file.filename, "predictions": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
def get_diagnostic_history(db: Session = Depends(get_db)):
    # Returns history records to display in Streamlit
    records = db.query(db_models.DiagnosticSession).order_by(db_models.DiagnosticSession.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "filename": r.filename,
            "total_windows": r.total_windows,
            "apnea_windows": r.apnea_windows,
            "osa_windows": r.osa_windows,
            "ca_windows": r.ca_windows,
            "normal_windows": r.normal_windows,
            "date": r.created_at.strftime("%Y-%m-%d %H:%M:%S")
        } for r in records
    ]